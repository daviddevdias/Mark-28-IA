import asyncio
import base64
import hashlib
import logging
import time
from dataclasses import dataclass
from io import BytesIO
from typing import Callable, Optional


import config
from mss import mss
from openai import OpenAI
from PIL import Image


log = logging.getLogger("CORE.vision")

MAX_WIDTH = 1280
JPEG_QUALITY = 40
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
            img = Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )

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


_SYSTEM_VISION = (
    "Você é o módulo de visão do C.O.R.E. "
    "Descreva o que vê de forma direta e técnica. "
    "Máximo 25 palavras."
)


async def analisar_tela(pergunta: str = "O que vê na tela?") -> str:

    client = get_client()
    if not client:
        return "[ERRO] Cliente não configurado."

    loop = asyncio.get_event_loop()
    img_b64 = await loop.run_in_executor(None, capturar_frame_base64)

    if not img_b64:
        return "[ERRO] Falha na captura de tela."

    try:
        resp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=config.CURRENT_MODEL,
                max_tokens=60,
                messages=[
                    {"role": "system", "content": _SYSTEM_VISION},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": pergunta},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}"
                                },
                            },
                        ],
                    },
                ],
            ),
        )

        return resp.choices[0].message.content.strip()

    except Exception as e:
        log.error("Erro na API de visão: %s", e)
        return f"[ERRO] {e}"


@dataclass
class MonitorConfig:
    intervalo_s: float = 5.0
    apenas_mudancas: bool = True
    pergunta: str = "Analise a tela e destaque erros ou mensagens importantes."
    callback: Optional[Callable[[str, str], None]] = None


@dataclass
class _MonitorState:
    rodando: bool = False
    ultimo_hash: str = ""
    ultima_analise: str = ""
    total_capturas: int = 0
    total_chamadas_api: int = 0
    economizados: int = 0


_monitor_state = _MonitorState()
_monitor_cfg: Optional[MonitorConfig] = None
_monitor_task: Optional[asyncio.Task] = None


async def _analisar_b64(img_b64: str, pergunta: str) -> str:

    client = get_client()
    if not client:
        return "[ERRO] Cliente ausente."

    loop = asyncio.get_event_loop()

    try:
        resp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=config.CURRENT_MODEL,
                max_tokens=60,
                messages=[
                    {"role": "system", "content": _SYSTEM_VISION},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": pergunta},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}"
                                },
                            },
                        ],
                    },
                ],
            ),
        )

        return resp.choices[0].message.content.strip()

    except Exception as e:
        log.error("Erro na análise contínua: %s", e)
        return f"[ERRO] {e}"


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

                analise = await _analisar_b64(img_b64, cfg.pergunta)
                state.ultima_analise = analise

                ts = time.strftime("%H:%M:%S")
                log.info("[%s] %s", ts, analise)

                if cfg.callback:
                    try:
                        import inspect
                        if inspect.iscoroutinefunction(cfg.callback):
                            asyncio.create_task(cfg.callback(analise))
                        else:
                            cfg.callback(analise)
                    except Exception as e:
                        log.warning("Callback erro: %s", e)

            else:
                state.economizados += 1

        elapsed = time.monotonic() - t_inicio
        await asyncio.sleep(max(0.0, cfg.intervalo_s - elapsed))


async def iniciar_monitor(cfg: Optional[MonitorConfig] = None) -> bool:

    global _monitor_state, _monitor_cfg, _monitor_task

    if _monitor_state.rodando:
        return False

    _monitor_cfg = cfg or MonitorConfig()
    _monitor_state = _MonitorState(rodando=True)

    loop = asyncio.get_event_loop()
    _monitor_task = loop.create_task(_loop_monitor())

    return True


def parar_monitor() -> dict:

    global _monitor_state, _monitor_task

    if not _monitor_state.rodando:
        return {"status": "inativo"}

    _monitor_state.rodando = False

    if _monitor_task:
        _monitor_task.cancel()

    return {
        "total_capturas": _monitor_state.total_capturas,
        "chamadas_api": _monitor_state.total_chamadas_api,
        "economizados": _monitor_state.economizados,
        "ultima_analise": _monitor_state.ultima_analise,
    }


def status_monitor() -> dict:
    return {
        "rodando": _monitor_state.rodando,
        "total_capturas": _monitor_state.total_capturas,
        "chamadas_api": _monitor_state.total_chamadas_api,
        "economizados": _monitor_state.economizados,
        "ultima_analise": _monitor_state.ultima_analise,
    }