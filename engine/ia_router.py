from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from collections import deque
from typing import Any, Optional

import aiohttp

from engine.tools import TOOL_DECLARATIONS
import config
from vision.capture import iniciar_monitor as _iniciar_monitor_raw
from vision.capture import parar_monitor   as desligar_monitor
from vision.capture import status_monitor  as info_monitor
from vision.capture import MonitorConfig

log = logging.getLogger("engine.ia_router")

_URL        = "http://127.0.0.1:11434/api/chat"
_TIMEOUT    = 25.0
_MAX_HIST   = 20
_MAX_TOOLS  = 5
_CHECK_COOL = 30.0

_OPTIONS = {"num_predict": 300, "temperature": 0.7}

_MODELO_DETECTADO: str = ""
_DISPONIVEL: bool = False
_ULTIMO_CHECK: float = 0.0

_PREFERIDOS = [
    "llama3.2", "llama3.1", "llama3", "qwen2.5", "qwen2",
    "mistral", "gemma2", "gemma", "phi3", "phi", "tinyllama",
]

_SYSTEM = (
    "Voce e Jarvis, assistente pessoal inteligente. "
    "Responda SEMPRE em portugues brasileiro, de forma direta e concisa. "
    "Contexto do usuario: {ctx}. "
    "REGRAS:\n"
    "1. Para acoes reais (abrir app, buscar, clima, spotify, youtube) use tool_call.\n"
    "2. NUNCA escreva JSON cru ou nome de ferramenta como texto de resposta.\n"
    "3. NUNCA simule execucao sem chamar a ferramenta.\n"
    "4. Apos resultado de ferramenta, responda em linguagem natural, curto.\n"
    "5. Sem ferramenta disponivel? Responda normalmente em texto."
)


def _system_msg(ctx: str) -> str:
    return _SYSTEM.format(ctx=ctx[:300] if ctx else "Sem contexto")


# =========================
# 🔥 NOVO: DETECTOR DE TOOLS
# =========================
def _modelo_suporta_tools(modelo: str) -> bool:




    if not modelo:
        return False




    modelo = modelo.lower()




    suportados = [
        "qwen",
        "phi3",
        "mixtral",
        "mistral",
    ]




    return any(m in modelo for m in suportados)


def ligar_monitor(intervalo_s: float = 10.0, callback=None) -> None:
    cfg = MonitorConfig(intervalo_s=intervalo_s, callback=callback)
    try:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(_iniciar_monitor_raw(cfg), loop)
    except Exception as e:
        log.error("Erro ao ligar monitor: %s", e)


async def _detectar_modelo() -> bool:
    global _MODELO_DETECTADO, _DISPONIVEL, _ULTIMO_CHECK
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "http://127.0.0.1:11434/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                if r.status != 200:
                    _DISPONIVEL = False
                    return False
                data = await r.json()
                modelos = [m["name"] for m in data.get("models", [])]
                if not modelos:
                    log.warning("Ollama online mas sem modelos. Rode: ollama pull llama3.2")
                    _DISPONIVEL = False
                    return False
                for p in _PREFERIDOS:
                    match = next((m for m in modelos if m.startswith(p)), None)
                    if match:
                        _MODELO_DETECTADO = match
                        break
                if not _MODELO_DETECTADO:
                    _MODELO_DETECTADO = modelos[0]
                _DISPONIVEL = True
                _ULTIMO_CHECK = time.time()
                log.info("[OLLAMA] Modelo: %s | Todos: %s", _MODELO_DETECTADO, modelos)
                print(f"[OLLAMA] Modelo detectado: {_MODELO_DETECTADO}")
                return True
    except Exception as e:
        log.warning("Ping Ollama falhou: %s", e)
        _DISPONIVEL = False
        return False


async def _check_if_needed(force: bool = False) -> None:
    global _ULTIMO_CHECK, _DISPONIVEL
    agora = time.time()
    if not force and _DISPONIVEL and (agora - _ULTIMO_CHECK) < _CHECK_COOL:
        return
    await _detectar_modelo()


class Historico:
    def __init__(self) -> None:
        self._turns: deque[dict] = deque(maxlen=_MAX_HIST)

    def add(self, role: str, content: Any) -> None:
        self._turns.append({"role": role, "content": content})

    def add_tool(self, call_id: str, name: str, result: str) -> None:
        self._turns.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": result,
        })

    def messages(self) -> list[dict]:
        return list(self._turns)

    def pop_last(self) -> None:
        if self._turns:
            self._turns.pop()

    def clear(self) -> None:
        self._turns.clear()


class IARRouter:

    def __init__(self) -> None:
        self.historico = Historico()

    @property
    def modo_atual(self) -> str:
        return "ollama"

    @property
    def status(self) -> dict:
        return {"modo": "ollama", "modelo": _MODELO_DETECTADO, "ollama": _DISPONIVEL}

    def definir_modo(self, modo: str) -> str:
        return f"Modo Ollama ativo. Modelo: {_MODELO_DETECTADO or 'nenhum detectado'}."

    def carregar_modo_salvo(self) -> None:
        pass

    def resetar_conversa(self) -> str:
        self.historico.clear()
        return "Conversa resetada."

    async def _chat(self, messages: list[dict], usar_tools: bool = True) -> dict | None:
        if not _MODELO_DETECTADO:
            return None

        payload: dict = {
            "model": _MODELO_DETECTADO,
            "messages": messages,
            "stream": False,
            "options": _OPTIONS,
        }

        # 🔥 CORREÇÃO AQUI
        if usar_tools and _modelo_suporta_tools(_MODELO_DETECTADO):
            payload["tools"] = TOOL_DECLARATIONS

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    _URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=_TIMEOUT),
                ) as r:
                    if r.status != 200:
                        log.error("Ollama HTTP %d: %s", r.status, (await r.text())[:200])
                        return None
                    data = await r.json()
                    return data.get("message")

        except asyncio.TimeoutError:
            log.warning("Timeout %ds modelo '%s'.", int(_TIMEOUT), _MODELO_DETECTADO)
            return None
        except aiohttp.ClientConnectorError:
            log.error("Ollama inacessivel.")
            return None
        except aiohttp.ServerDisconnectedError:
            log.error("Ollama desconectou.")
            return None
        except Exception as e:
            log.error("Erro Ollama %s: %s", type(e).__name__, e)
            return None

    async def _dispatch_tool(self, name: str, args: dict) -> str:
        try:
            from engine.tools_mapper import despachar
            return str(await despachar(name, args))
        except Exception as e:
            log.error("Tool '%s' falhou: %s", name, e)
            return f"Erro na ferramenta '{name}': {e}"

    def _e_json_cru(self, texto: str) -> bool:
        t = texto.strip()
        if t.startswith("{") and t.endswith("}"):
            return True
        if len(t) < 150 and ('"query"' in t or '"action"' in t or '"app_name"' in t):
            return True
        return False

    async def responder(
        self,
        pergunta: str,
        nome: str = "David",
        memoria: str = "",
        imagem: Any = None,
    ) -> str:
        await _check_if_needed()

        if not _DISPONIVEL:
            await _check_if_needed(force=True)

        if not _DISPONIVEL:
            return "Ollama offline. Rode 'ollama serve' no terminal."

        if not _MODELO_DETECTADO:
            return "Nenhum modelo instalado. Rode: ollama pull llama3.2"

        content = self._build_content(pergunta, imagem)
        self.historico.add("user", content)
        msgs = [{"role": "system", "content": _system_msg(memoria)}] + self.historico.messages()

        for i in range(_MAX_TOOLS):

            # 🔥 CORREÇÃO AQUI TAMBÉM
            usar_tools = _modelo_suporta_tools(_MODELO_DETECTADO)

            msg = await self._chat(msgs, usar_tools=usar_tools)

            if msg is None:
                msg = await self._chat(msgs, usar_tools=False)

            if msg is None:
                self.historico.pop_last()
                return "Nao consegui resposta do Ollama. Tente novamente."

            tool_calls: list = msg.get("tool_calls") or []

            if not tool_calls:
                reply = (msg.get("content") or "").strip()
                if reply and self._e_json_cru(reply):
                    log.warning("JSON cru detectado, descartando: %s", reply[:80])
                    reply = "Feito."
                if not reply:
                    reply = "Concluido."
                self.historico.add("assistant", reply)
                return reply

            msgs.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            })
            self.historico.add("assistant", msg.get("content") or "")

            for tc in tool_calls:
                call_id = tc.get("id", f"call_{i}")
                fn      = tc.get("function", {})
                fn_name = fn.get("name", "")
                raw     = fn.get("arguments", {})
                args    = json.loads(raw) if isinstance(raw, str) else (raw or {})

                log.info("Tool [%d]: %s(%s)", i, fn_name, args)
                result = await self._dispatch_tool(fn_name, args)
                log.info("Tool result: %.120s", result)

                msgs.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": fn_name,
                    "content": result,
                })
                self.historico.add_tool(call_id, fn_name, result)

        return "Operacao concluida."

    def _build_content(self, text: str, imagem: Any) -> Any:
        if imagem is None:
            return text
        img_url = None
        if isinstance(imagem, str) and os.path.isfile(imagem):
            try:
                with open(imagem, "rb") as f:
                    img_url = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
            except Exception as e:
                log.warning("Falha ao ler imagem: %s", e)
        elif isinstance(imagem, bytes):
            img_url = f"data:image/png;base64,{base64.b64encode(imagem).decode()}"
        elif isinstance(imagem, str) and imagem.startswith("data:"):
            img_url = imagem
        if img_url:
            return [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": img_url}},
            ]
        return text


router = IARRouter()
router.carregar_modo_salvo()