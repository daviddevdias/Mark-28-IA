import asyncio
import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import Callable, Optional

import config
from mss import mss
from openai import OpenAI
from PIL import Image

log = logging.getLogger("vision")

MAX_WIDTH = 1280
JPEG_QUALITY = 42
MONITOR_INDEX = 1

_client: Optional[OpenAI] = None


def get_client() -> Optional[OpenAI]:
    global _client

    if _client:
        return _client

    if not getattr(config, "QWEN_API_KEY", None):
        log.error("QWEN_API_KEY ausente em config.")
        return None

    _client = OpenAI(api_key=config.QWEN_API_KEY, base_url=config.BASE_URL)
    return _client


def capturar_frame_base64() -> Optional[str]:
    try:
        with mss() as sct:
            idx = MONITOR_INDEX if len(sct.monitors) > MONITOR_INDEX else 0
            monitor = sct.monitors[idx]
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            if img.width > MAX_WIDTH:
                img.thumbnail((MAX_WIDTH, 720), Image.LANCZOS)

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
            return base64.b64encode(buffer.getvalue()).decode()

    except Exception as e:
        log.error("Erro ao capturar tela: %s", e)
        return None


def _hash_frame(b64: str) -> str:
    return hashlib.md5(b64[:4096].encode()).hexdigest()


_SYSTEM_VISAO_RAPIDA = (
    "Você é o sensor visual do J.A.R.V.I.S. "
    "Observe a tela e responda SOMENTE em JSON, sem markdown, sem explicações. "
    "Formato obrigatório: "
    '{"ok": true/false, "tipo": "normal|erro|aviso|crash|travado|instalacao|compilacao|terminal|codigo|navegador|outro", '
    '"resumo": "frase curta do que vê", '
    '"problema": "descrição do problema se ok=false, senão vazio", '
    '"sugestao_rapida": "ação imediata se ok=false, senão vazia"} '
    "Seja preciso. Máximo 20 palavras por campo."
)

_SYSTEM_DICA_PROFUNDA = (
    "Você é J.A.R.V.I.S, assistente técnico especialista. "
    "O usuário é desenvolvedor ADS. "
    "Analise o problema detectado na tela e forneça: "
    "1) diagnóstico direto do problema "
    "2) causa provável "
    "3) solução passo a passo (máximo 3 passos) "
    "Seja técnico, direto, sem rodeios. "
    "Responda em português. Máximo 80 palavras total."
)


async def _chamar_qwen(system: str, pergunta: str, img_b64: str, max_tokens: int = 120) -> str:
    client = get_client()
    if not client:
        return "[ERRO] Cliente Qwen não configurado."

    loop = asyncio.get_event_loop()

    try:
        resp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=config.CURRENT_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": pergunta},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                            },
                        ],
                    },
                ],
            ),
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        log.error("Erro Qwen API: %s", e)
        return f"[ERRO] {e}"


async def analisar_tela(pergunta: str = "O que vê na tela?") -> str:
    client = get_client()
    if not client:
        return "[ERRO] Cliente não configurado."

    loop = asyncio.get_event_loop()
    img_b64 = await loop.run_in_executor(None, capturar_frame_base64)

    if not img_b64:
        return "[ERRO] Falha na captura de tela."

    return await _chamar_qwen(_SYSTEM_VISAO_RAPIDA, pergunta, img_b64, max_tokens=120)


async def gerar_dica_profunda(img_b64: str, problema: str, tipo: str) -> str:
    prompt = (
        f"Tipo de problema detectado: {tipo}.\n"
        f"Descrição: {problema}\n"
        f"Analise a tela e me diga o que fazer."
    )
    return await _chamar_qwen(_SYSTEM_DICA_PROFUNDA, prompt, img_b64, max_tokens=200)


@dataclass
class ResultadoAnalise:
    ok: bool = True
    tipo: str = "normal"
    resumo: str = ""
    problema: str = ""
    sugestao_rapida: str = ""
    dica_profunda: str = ""
    img_b64: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class MonitorConfig:
    intervalo_s: float = 8.0
    apenas_mudancas: bool = True
    gerar_dica_automatica: bool = True
    cooldown_alerta_s: float = 45.0
    pergunta: str = "Analise esta tela. Há erros, travamentos ou problemas visíveis?"
    callback: Optional[Callable] = None


@dataclass
class _MonitorState:
    rodando: bool = False
    ultimo_hash: str = ""
    ultima_analise: str = ""
    ultimo_resultado: Optional[ResultadoAnalise] = None
    total_capturas: int = 0
    total_chamadas_api: int = 0
    total_problemas: int = 0
    economizados: int = 0
    ultimo_alerta_ts: float = 0.0


_monitor_state = _MonitorState()
_monitor_cfg: Optional[MonitorConfig] = None
_monitor_task: Optional[asyncio.Task] = None


def _parse_resultado(raw: str, img_b64: str) -> ResultadoAnalise:
    import json
    import re

    try:
        limpo = re.sub(r"```(?:json)?|```", "", raw).strip()
        dados = json.loads(limpo)
        return ResultadoAnalise(
            ok=bool(dados.get("ok", True)),
            tipo=str(dados.get("tipo", "normal")),
            resumo=str(dados.get("resumo", "")),
            problema=str(dados.get("problema", "")),
            sugestao_rapida=str(dados.get("sugestao_rapida", "")),
            img_b64=img_b64,
        )
    except Exception:
        tem_problema = any(
            k in raw.lower()
            for k in ["erro", "error", "falha", "crash", "travad", "exception", "warning"]
        )
        return ResultadoAnalise(
            ok=not tem_problema,
            tipo="erro" if tem_problema else "normal",
            resumo=raw[:120],
            problema=raw[:120] if tem_problema else "",
            img_b64=img_b64,
        )


async def _loop_monitor():
    global _monitor_state, _monitor_cfg

    cfg = _monitor_cfg
    state = _monitor_state

    loop = asyncio.get_event_loop()

    while state.rodando:
        t_inicio = time.monotonic()

        img_b64 = await loop.run_in_executor(None, capturar_frame_base64)
        state.total_capturas += 1

        if img_b64:
            h = _hash_frame(img_b64)
            mudou = h != state.ultimo_hash

            if mudou or not cfg.apenas_mudancas:
                state.ultimo_hash = h
                state.total_chamadas_api += 1

                raw = await _chamar_qwen(
                    _SYSTEM_VISAO_RAPIDA,
                    cfg.pergunta,
                    img_b64,
                    max_tokens=150,
                )

                resultado = _parse_resultado(raw, img_b64)
                state.ultima_analise = resultado.resumo
                state.ultimo_resultado = resultado

                agora = time.time()
                cooldown_ok = (agora - state.ultimo_alerta_ts) >= cfg.cooldown_alerta_s

                if not resultado.ok and cooldown_ok:
                    state.total_problemas += 1
                    state.ultimo_alerta_ts = agora

                    if cfg.gerar_dica_automatica:
                        resultado.dica_profunda = await gerar_dica_profunda(
                            img_b64,
                            resultado.problema,
                            resultado.tipo,
                        )

                    log.warning(
                        "[MONITOR] Problema '%s': %s",
                        resultado.tipo,
                        resultado.problema[:80],
                    )

                    if cfg.callback:
                        try:
                            import inspect
                            if inspect.iscoroutinefunction(cfg.callback):
                                asyncio.create_task(cfg.callback(resultado))
                            else:
                                cfg.callback(resultado)
                        except Exception as e:
                            log.warning("Callback erro: %s", e)

                else:

                    if cfg.callback and resultado.ok:
                        try:
                            import inspect
                            if inspect.iscoroutinefunction(cfg.callback):
                                asyncio.create_task(cfg.callback(resultado))
                            else:
                                cfg.callback(resultado)
                        except Exception as e:
                            log.warning("Callback erro: %s", e)

                    log.debug("[MONITOR] OK — %s", resultado.resumo[:60])

            else:
                state.economizados += 1

        elapsed = time.monotonic() - t_inicio
        await asyncio.sleep(max(0.5, cfg.intervalo_s - elapsed))


async def iniciar_monitor(cfg: Optional[MonitorConfig] = None) -> bool:
    global _monitor_state, _monitor_cfg, _monitor_task

    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_monitor_task), timeout=2.0)
        except Exception:
            pass

    _monitor_cfg   = cfg or MonitorConfig()

    _monitor_state = _MonitorState(rodando=True)

    loop = asyncio.get_event_loop()
    _monitor_task  = loop.create_task(_loop_monitor())

    log.info("[MONITOR] Iniciado — intervalo %.0fs", _monitor_cfg.intervalo_s)
    return True


def parar_monitor() -> dict:
    global _monitor_state, _monitor_task

    if not _monitor_state.rodando:
        return {"status": "inativo"}

    _monitor_state.rodando = False

    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()

    stats = {
        "total_capturas":   _monitor_state.total_capturas,
        "chamadas_api":     _monitor_state.total_chamadas_api,
        "total_problemas":  _monitor_state.total_problemas,
        "economizados":     _monitor_state.economizados,
        "ultima_analise":   _monitor_state.ultima_analise,
    }

    return stats


def status_monitor() -> dict:
    return {
        "rodando":          _monitor_state.rodando,
        "total_capturas":   _monitor_state.total_capturas,
        "chamadas_api":     _monitor_state.total_chamadas_api,
        "total_problemas":  _monitor_state.total_problemas,
        "economizados":     _monitor_state.economizados,
        "ultima_analise":   _monitor_state.ultima_analise,
    }