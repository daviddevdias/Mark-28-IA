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
from vision.capture import iniciar_monitor as ligar_monitor          # noqa: F401
from vision.capture import parar_monitor  as desligar_monitor        # noqa: F401
from vision.capture import status_monitor as info_monitor            # noqa: F401

log = logging.getLogger("engine.ia_router")

_URL         = "http://127.0.0.1:11434/api/chat"
_MODELO      = ""               # detectado automaticamente no primeiro ping
_TIMEOUT     = 30.0
_MAX_RETRIES = 1
_MAX_HIST    = 20
_MAX_TOOLS   = 5
_CHECK_COOL  = 10.0

_OPTIONS = {
    "num_predict": 256,
    "temperature": 0.7,
}

_MODELOS_PREFERIDOS = [
    "qwen2.5", "qwen2", "llama3.1", "llama3", "llama2",
    "mistral", "gemma2", "gemma", "phi3", "phi",
]

_SYSTEM = (
    "Você é Jarvis, assistente pessoal. "
    "Responda SEMPRE em português, de forma técnica e concisa. "
    "Contexto: {ctx}. "
    "REGRAS:\n"
    "1. Para ações reais (app, busca, clima, spotify) use tool_call.\n"
    "2. NUNCA simule execução sem chamar a ferramenta.\n"
    "3. NUNCA retorne JSON cru ao usuário.\n"
    "4. Após resultado da ferramenta, responda curto e direto.\n"
    "5. Sem ferramenta disponível? Responda em texto normalmente."
)


def _system_msg(ctx: str) -> str:
    return _SYSTEM.format(ctx=ctx[:300] if ctx else "Nenhum")


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
        self._disponivel: Optional[bool] = None
        self._ultimo_check: float = 0.0
        self.historico = Historico()

    @property
    def modo_atual(self) -> str:
        return "ollama"

    @property
    def status(self) -> dict:
        return {"modo": "ollama", "modelo": _MODELO, "ollama": self._disponivel}

    def definir_modo(self, modo: str) -> str:
        if modo.lower() == "ollama":
            return f"Modo Ollama ativo. Modelo: {_MODELO}."
        return f"Modo '{modo}' indisponível. Usando Ollama ({_MODELO})."

    def carregar_modo_salvo(self) -> None:
        pass

    def resetar_conversa(self) -> str:
        self.historico.clear()
        return "Conversa resetada."

    async def _ping(self) -> bool:
        global _MODELO
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    "http://127.0.0.1:11434/api/tags",
                    timeout=aiohttp.ClientTimeout(total=4),
                ) as r:
                    if r.status != 200:
                        return False
                    data = await r.json()
                    modelos = [m["name"] for m in data.get("models", [])]
                    if not modelos:
                        log.warning("Ollama online mas sem modelos instalados.")
                        return False

                    if _MODELO and any(m.startswith(_MODELO.split(":")[0]) for m in modelos):
                        log.info("Ollama online. Modelo atual: %s", _MODELO)
                        return True

                    for preferido in _MODELOS_PREFERIDOS:
                        match = next((m for m in modelos if m.startswith(preferido)), None)
                        if match:
                            _MODELO = match
                            log.info("Modelo selecionado: %s | Disponíveis: %s", _MODELO, modelos)
                            return True

                    _MODELO = modelos[0]
                    log.info("Usando primeiro modelo disponível: %s", _MODELO)
                    return True

        except Exception as e:
            log.warning("Ping falhou: %s", e)
            return False

    async def _check(self, force: bool = False) -> None:
        now = time.time()
        if not force and (now - self._ultimo_check) < _CHECK_COOL:
            return
        self._ultimo_check = now
        self._disponivel = await self._ping()
        if not self._disponivel:
            log.warning("Ollama offline (health-check).")

    async def _chat(self, messages: list[dict], usar_tools: bool = True) -> dict | None:
        payload = {
            "model": _MODELO,
            "messages": messages,
            "stream": False,
            "options": _OPTIONS,
        }
        if usar_tools:
            payload["tools"] = TOOL_DECLARATIONS

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    _URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=_TIMEOUT),
                ) as r:
                    if r.status != 200:
                        body = await r.text()
                        log.error("Ollama HTTP %d: %s", r.status, body[:200])
                        return None
                    data = await r.json()
                    return data.get("message")

        except asyncio.TimeoutError:
            log.warning("Ollama timeout %ds.", int(_TIMEOUT))
            self._disponivel = False
            self._ultimo_check = 0.0
            return None

        except aiohttp.ClientConnectorError as e:
            log.error("Ollama inacessível: %s", e)
            self._disponivel = False
            self._ultimo_check = 0.0
            return None

        except aiohttp.ServerDisconnectedError:
            log.error("Ollama desconectou.")
            self._disponivel = False
            self._ultimo_check = 0.0
            return None

        except Exception as e:
            log.error("Erro inesperado Ollama — %s: %s", type(e).__name__, e)
            self._disponivel = False
            self._ultimo_check = 0.0
            return None

    async def _dispatch_tool(self, name: str, args: dict) -> str:
        try:
            from engine.tools_mapper import despachar
            return str(await despachar(name, args))
        except Exception as e:
            log.error("Tool '%s' falhou: %s", name, e)
            return f"Erro na ferramenta '{name}': {e}"

    async def responder(
        self,
        pergunta: str,
        nome: str = "David",
        memoria: str = "",
        imagem: Any = None,
    ) -> str:
        await self._check()

        if not self._disponivel:
            await self._check(force=True)

        if not self._disponivel:
            return (
                f"Ollama offline. Execute 'ollama serve' e confirme com "
                f"'ollama list' que '{_MODELO}' está disponível."
            )

        content = self._build_content(pergunta, imagem)
        self.historico.add("user", content)
        msgs = [{"role": "system", "content": _system_msg(memoria)}] + self.historico.messages()

        for i in range(_MAX_TOOLS):
            msg = await self._chat(msgs, usar_tools=(i == 0))

            if msg is None:
                if i == 0:
                    log.warning("Falha com tools, tentando sem tools...")
                    msg = await self._chat(msgs, usar_tools=False)

                if msg is None:
                    self.historico.pop_last()
                    return "Ollama não respondeu. Verifique se o serviço está ativo."

            tool_calls: list = msg.get("tool_calls") or []

            if not tool_calls:
                reply = (msg.get("content") or "").strip() or "Concluído."
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

                args = json.loads(raw) if isinstance(raw, str) else (raw or {})

                log.info("Tool [%d]: %s(%s)", i, fn_name, args)
                result = await self._dispatch_tool(fn_name, args)
                log.info("Tool result: %.120s", result)

                tool_msg = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": fn_name,
                    "content": result,
                }
                msgs.append(tool_msg)
                self.historico.add_tool(call_id, fn_name, result)

        log.warning("Limite de tool iterations atingido.")
        return "Operação concluída."

    def _build_content(self, text: str, imagem: Any) -> Any:
        if imagem is None:
            return text

        img_url = None

        if isinstance(imagem, str) and os.path.isfile(imagem):
            try:
                with open(imagem, "rb") as f:
                    img_url = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
            except Exception as e:
                log.warning("Falha ao ler imagem '%s': %s", imagem, e)

        elif isinstance(imagem, bytes):
            img_url = f"data:image/png;base64,{base64.b64encode(imagem).decode()}"

        elif isinstance(imagem, str) and imagem.startswith("data:"):
            img_url = imagem

        if img_url:
            return [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": img_url}},
            ]

        log.warning("Formato de imagem não reconhecido: %s", type(imagem))
        return text


router = IARRouter()
router.carregar_modo_salvo()