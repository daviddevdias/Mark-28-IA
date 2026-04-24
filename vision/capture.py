from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import Callable, Optional

import config
from mss import mss
from openai import OpenAI
from PIL import Image


log = logging.getLogger("vision")

MAX_WIDTH     = 1280
JPEG_QUALITY  = 42
MONITOR_INDEX = 1

client: Optional[OpenAI] = None


SYSTEM_RAPIDO = (
    "Você é o sensor visual do J.A.R.V.I.S. "
    "Observe a tela e responda SOMENTE em JSON sem markdown. "
    'Formato: {"ok": true/false, "tipo": "normal|erro|aviso|crash|travado|instalacao|compilacao|terminal|codigo|outro", '
    '"resumo": "frase curta", "problema": "descrição se ok=false", "sugestao_rapida": "ação se ok=false"} '
    "Máximo 20 palavras por campo."
)

SYSTEM_DICA = (
    "Você é J.A.R.V.I.S, assistente técnico. Usuário é desenvolvedor ADS. "
    "Analise o problema e forneça: diagnóstico direto, causa provável, solução em até 3 passos. "
    "Seja técnico e direto. Português. Máximo 80 palavras."
)


@dataclass
class ResultadoAnalise:
    ok: bool             = True
    tipo: str            = "normal"
    resumo: str          = ""
    problema: str        = ""
    sugestao_rapida: str = ""
    dica_profunda: str   = ""
    img_b64: str         = ""
    timestamp: float     = field(default_factory=time.time)


@dataclass
class MonitorConfig:
    intervalo_s: float           = 8.0
    apenas_mudancas: bool        = True
    gerar_dica_auto: bool        = True
    cooldown_s: float            = 45.0
    pergunta: str                = "Analise esta tela. Há erros ou problemas visíveis?"
    callback: Optional[Callable] = None


@dataclass
class Estado:
    rodando: bool                                = False
    ultimo_hash: str                             = ""
    ultima_analise: str                          = ""
    ultimo_resultado: Optional[ResultadoAnalise] = None
    capturas: int                                = 0
    chamadas_api: int                            = 0
    problemas: int                               = 0
    economizados: int                            = 0
    ultimo_alerta: float                         = 0.0


estado  = Estado()
cfg_mon: Optional[MonitorConfig] = None
task:    Optional[asyncio.Task]  = None


def get_client() -> Optional[OpenAI]:
    global client
    if client:
        return client
    if not getattr(config, "QWEN_API_KEY", None):
        log.error("QWEN_API_KEY ausente.")
        return None
    client = OpenAI(api_key=config.QWEN_API_KEY, base_url=config.BASE_URL)
    return client


def capturar_frame_base64() -> Optional[str]:
    try:
        with mss() as sct:
            idx  = MONITOR_INDEX if len(sct.monitors) > MONITOR_INDEX else 0
            shot = sct.grab(sct.monitors[idx])
            img  = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            if img.width > MAX_WIDTH:
                img.thumbnail((MAX_WIDTH, 720), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_QUALITY)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log.error("Erro ao capturar tela: %s", e)
        return None


def hash_frame(b64: str) -> str:
    return hashlib.md5(b64[:4096].encode()).hexdigest()


def parse(raw: str, img_b64: str) -> ResultadoAnalise:
    try:
        dados = json.loads(re.sub(r"```(?:json)?|```", "", raw).strip())
        return ResultadoAnalise(
            ok=bool(dados.get("ok", True)),
            tipo=str(dados.get("tipo", "normal")),
            resumo=str(dados.get("resumo", "")),
            problema=str(dados.get("problema", "")),
            sugestao_rapida=str(dados.get("sugestao_rapida", "")),
            img_b64=img_b64,
        )
    except Exception:
        tem_prob = any(k in raw.lower() for k in ["erro", "error", "falha", "crash", "travad", "exception"])
        return ResultadoAnalise(
            ok=not tem_prob,
            tipo="erro" if tem_prob else "normal",
            resumo=raw[:120],
            problema=raw[:120] if tem_prob else "",
            img_b64=img_b64,
        )


async def chamar_qwen(system: str, pergunta: str, img_b64: str, max_tokens: int = 120) -> str:
    c = get_client()
    if not c:
        return "[ERRO] Cliente Qwen não configurado."
    try:
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: c.chat.completions.create(
                model=config.CURRENT_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": [
                        {"type": "text", "text": pergunta},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    ]},
                ],
            ),
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error("Qwen API erro: %s", e)
        return f"[ERRO] {e}"


async def analisar_tela(pergunta: str = "O que vê na tela?") -> str:
    if not get_client():
        return "[ERRO] Cliente não configurado."
    img = await asyncio.get_event_loop().run_in_executor(None, capturar_frame_base64)
    if not img:
        return "[ERRO] Falha na captura."
    return await chamar_qwen(SYSTEM_RAPIDO, pergunta, img)


async def gerar_dica_profunda(img_b64: str, problema: str, tipo: str) -> str:
    prompt = f"Tipo: {tipo}.\nProblema: {problema}\nAnalise e diga o que fazer."
    return await chamar_qwen(SYSTEM_DICA, prompt, img_b64, max_tokens=200)


async def loop_monitor():
    loop = asyncio.get_event_loop()

    while estado.rodando:
        t0  = time.monotonic()
        img = await loop.run_in_executor(None, capturar_frame_base64)
        estado.capturas += 1

        if img:
            h     = hash_frame(img)
            mudou = h != estado.ultimo_hash

            if mudou or not cfg_mon.apenas_mudancas:
                estado.ultimo_hash   = h
                estado.chamadas_api += 1

                raw       = await chamar_qwen(SYSTEM_RAPIDO, cfg_mon.pergunta, img, max_tokens=150)
                resultado = parse(raw, img)
                estado.ultima_analise   = resultado.resumo
                estado.ultimo_resultado = resultado

                agora       = time.time()
                em_cooldown = (agora - estado.ultimo_alerta) < cfg_mon.cooldown_s

                if not resultado.ok and not em_cooldown:
                    estado.problemas     += 1
                    estado.ultimo_alerta  = agora
                    if cfg_mon.gerar_dica_auto:
                        resultado.dica_profunda = await gerar_dica_profunda(
                            img, resultado.problema, resultado.tipo
                        )

                if cfg_mon.callback:
                    try:
                        import inspect
                        if inspect.iscoroutinefunction(cfg_mon.callback):
                            asyncio.create_task(cfg_mon.callback(resultado))
                        else:
                            cfg_mon.callback(resultado)
                    except Exception as e:
                        log.warning("Callback erro: %s", e)
            else:
                estado.economizados += 1

        await asyncio.sleep(max(0.5, cfg_mon.intervalo_s - (time.monotonic() - t0)))


async def iniciar_monitor(cfg: Optional[MonitorConfig] = None) -> bool:
    global estado, cfg_mon, task

    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
        except Exception:
            pass

    cfg_mon = cfg or MonitorConfig()
    estado  = Estado(rodando=True)
    task    = asyncio.get_event_loop().create_task(loop_monitor())
    return True


def parar_monitor() -> dict:
    global estado, task
    if not estado.rodando:
        return {"status": "inativo"}
    estado.rodando = False
    if task and not task.done():
        task.cancel()
    return {
        "capturas":        estado.capturas,
        "chamadas_api":    estado.chamadas_api,
        "total_problemas": estado.problemas,
        "economizados":    estado.economizados,
        "ultima_analise":  estado.ultima_analise,
    }


def status_monitor() -> dict:
    return {
        "rodando":         estado.rodando,
        "chamadas_api":    estado.chamadas_api,
        "total_problemas": estado.problemas,
        "economizados":    estado.economizados,
        "ultima_analise":  estado.ultima_analise,
    }