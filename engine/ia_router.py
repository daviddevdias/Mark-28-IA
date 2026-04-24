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

import config
from engine.tools import TOOL_DECLARATIONS
from vision.capture import iniciar_monitor as iniciar_monitor_raw, parar_monitor, status_monitor, MonitorConfig

log = logging.getLogger("engine.ia_router")

URL        = "http://127.0.0.1:11434/api/chat"
TIMEOUT    = 25.0
MAX_HIST   = 20
MAX_TOOLS  = 5
COOL       = 30.0
OPTIONS    = {"num_predict": 300, "temperature": 0.7}





PREFERIDOS = ["llama3.2", "llama3.1", "llama3", "qwen2.5", "qwen2",
               "mistral", "gemma2", "gemma", "phi3", "phi", "tinyllama"]



TOOLS_SUPORTADOS = ["qwen", "phi3", "mixtral", "mistral", "llama3.1", "llama3.2"]





SYSTEM = (
    "Você é Jarvis, assistente pessoal inteligente e didático. "
    "Responda SEMPRE em português brasileiro, direto e conciso. "
    "Contexto: {ctx}. "
    "REGRAS: "
    "1. Tarefas/compromissos/horários → use tool_call 'set_reminder'. "
    "2. Ações reais (app, busca, clima, spotify) → use tool_call. "
    "3. NUNCA escreva JSON cru ou nome de ferramenta como resposta. "
    "4. Após resultado de ferramenta, confirme em linguagem natural. "
    "5. Seja conversacional."
)

modelo:      str   = ""
disponivel:  bool  = False
ultimo_check: float = 0.0







def system_msg(ctx: str) -> str:
    return SYSTEM.format(ctx=ctx[:300] or "Sem contexto")







def suporta_tools(modelo_param: str) -> bool:
    m = modelo_param.lower()
    return any(s in m for s in TOOLS_SUPORTADOS)







def ligar_monitor(intervalo_s: float = 10.0, callback=None) -> None:
    cfg = MonitorConfig(intervalo_s=intervalo_s, callback=callback)
    try:
        asyncio.run_coroutine_threadsafe(iniciar_monitor_raw(cfg), asyncio.get_event_loop())
    except Exception as e:
        log.error("Erro ao ligar monitor: %s", e)







async def detectar_modelo() -> bool:
    global modelo, disponivel, ultimo_check
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("http://127.0.0.1:11434/api/tags",
                             timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status != 200:
                    disponivel = False
                    return False
                data    = await r.json()
                modelos = [m["name"] for m in data.get("models", [])]
                if not modelos:
                    disponivel = False
                    return False
                modelo = next(
                    (m for p in PREFERIDOS for m in modelos if m.startswith(p)),
                    modelos[0],
                )
                disponivel    = True
                ultimo_check = time.time()
                print(f"[OLLAMA] Modelo: {modelo}")
                return True
    except Exception:
        disponivel = False
        return False







async def check(force: bool = False) -> None:
    if not force and disponivel and (time.time() - ultimo_check) < COOL:
        return
    await detectar_modelo()







class Historico:







    def __init__(self):
        self.turns: deque[dict] = deque(maxlen=MAX_HIST)







    def add(self, role: str, content: Any) -> None:
        self.turns.append({"role": role, "content": content})







    def add_tool(self, call_id: str, name: str, result: str) -> None:
        self.turns.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": result})







    def msgs(self) -> list[dict]:
        return list(self.turns)







    def pop(self) -> None:
        if self.turns:
            self.turns.pop()







    def clear(self) -> None:
        self.turns.clear()







class IARRouter:







    def __init__(self):
        self.historico = Historico()







    @property







    def status(self) -> dict:
        return {"modelo": modelo, "ollama": disponivel}







    def definir_modo(self, modo: str) -> str:
        return f"Modo Ollama ativo. Modelo: {modelo or 'nenhum detectado'}."







    def carregar_modo_salvo(self) -> None:
        pass







    def resetar_conversa(self) -> str:
        self.historico.clear()
        return "Conversa resetada."







    async def chat(self, messages: list[dict], tools: bool = True) -> dict | None:
        if not modelo:
            return None
        payload: dict = {"model": modelo, "messages": messages, "stream": False, "options": OPTIONS}
        if tools and suporta_tools(modelo):
            payload["tools"] = TOOL_DECLARATIONS
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(URL, json=payload,
                                  timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                    if r.status != 200:
                        return None
                    return (await r.json()).get("message")
        except Exception:
            return None







    async def dispatch(self, name: str, args: dict) -> str:
        try:
            from engine.tools_mapper import despachar
            return str(await despachar(name, args))
        except Exception as e:
            return f"Erro na ferramenta '{name}': {e}"







    def e_json_cru(self, texto: str) -> bool:
        t = texto.strip()
        if t.startswith("{") and t.endswith("}"):
            return True
        return len(t) < 150 and any(k in t for k in ('"query"', '"action"', '"app_name"'))







    def montar_content(self, text: str, imagem: Any) -> Any:
        if imagem is None:
            return text
        img_url = None
        if isinstance(imagem, str) and os.path.isfile(imagem):
            try:
                img_url = f"data:image/png;base64,{base64.b64encode(open(imagem, 'rb').read()).decode()}"
            except Exception:
                pass
        elif isinstance(imagem, bytes):
            img_url = f"data:image/png;base64,{base64.b64encode(imagem).decode()}"
        elif isinstance(imagem, str) and imagem.startswith("data:"):
            img_url = imagem
        if img_url:
            return [{"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": img_url}}]
        return text







    async def responder(self, pergunta: str, nome: str = "Chefe", memoria: str = "", imagem: Any = None) -> str:
        await check()
        if not disponivel:
            await check(force=True)
        if not disponivel:
            return "Ollama offline. Rode 'ollama serve' no terminal."
        if not modelo:
            return "Nenhum modelo instalado. Rode: ollama pull llama3.2"



        self.historico.add("user", self.montar_content(pergunta, imagem))
        msgs = [{"role": "system", "content": system_msg(memoria)}] + self.historico.msgs()



        for i in range(MAX_TOOLS):
            msg = await self.chat(msgs) or await self.chat(msgs, tools=False)
            if msg is None:
                self.historico.pop()
                return "Sem resposta do Ollama. Tente novamente."



            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                reply = (msg.get("content") or "").strip()
                if self.e_json_cru(reply):
                    reply = "Feito."
                if not reply:
                    reply = "Concluído."
                self.historico.add("assistant", reply)
                return reply



            msgs.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
            self.historico.add("assistant", msg.get("content") or "")



            for tc in tool_calls:
                call_id = tc.get("id", f"call_{i}")
                fn      = tc.get("function", {})
                raw     = fn.get("arguments", {})
                args    = json.loads(raw) if isinstance(raw, str) else (raw or {})
                result  = await self.dispatch(fn.get("name", ""), args)
                msgs.append({"role": "tool", "tool_call_id": call_id, "name": fn.get("name"), "content": result})
                self.historico.add_tool(call_id, fn.get("name", ""), result)

        return "Operação concluída."

router = IARRouter()
router.carregar_modo_salvo()

info_monitor    = status_monitor
desligar_monitor = parar_monitor