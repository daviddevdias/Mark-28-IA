from __future__ import annotations
import logging
import time
from typing import Optional, Callable, Any
import aiohttp
import PIL.Image
from google import genai
from engine.tools import TOOL_DECLARATIONS, DISPATCHER
import config
from vision.capture import iniciar_monitor as ligar_monitor

log = logging.getLogger("engine.ia_router")




URL_OLLAMA = "http://127.0.0.1:11434/api/chat"
MODELO_OLLAMA = "llama3"
MODELO_GEMINI = "gemini-2.0-flash-lite"
MAX_TOKENS = 512
TIMEOUT_S = 30.0

MODO_GEMINI = "gemini"
MODO_OLLAMA = "ollama"
MODO_AUTO = "auto"





BASE_SISTEMA = (
    "Você é Jarvis, assistente pessoal de David (Dev ADS). "
    "Responda em português, de forma técnica e concisa. "
    "Memória disponível: {memoria}. "
    "Use ferramentas quando o usuário pedir ações reais. "
    "Para ações domésticas informe que executou o comando. "
    "Seja direto: máximo 2 frases por resposta."
)




PROMPT_ESTRATEGISTA = (
    "Você é o estrategista do Jarvis (Dev ADS - David). "
    "Quebre a tarefa em até 5 passos objetivos, numerados. "
    "Sem explicação longa.\n\nTarefa: "
)


gemini_client_global: Optional[genai.Client] = None
IA_AVISADA = False






def build_system(nome: str, memoria: str) -> str:
    return BASE_SISTEMA.format(nome=nome, memoria=memoria[:400])






def get_client() -> Optional[genai.Client]:
    global gemini_client_global
    if gemini_client_global:
        return gemini_client_global
    key = getattr(config, "GEMINI_API_KEY", None)
    if not key:
        return None
    gemini_client_global = genai.Client(api_key=key)
    return gemini_client_global






def criar_plano(comando: str) -> str:
    global IA_AVISADA
    if not comando:
        return ""
    client = get_client()
    if not client:
        if not IA_AVISADA:
            log.warning("API Key do Gemini não encontrada no planner.")
            IA_AVISADA = True
        return ""
    try:
        resp = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=PROMPT_ESTRATEGISTA + comando,
        )
        plano = (resp.text or "").strip()
        return plano if plano else ""
    except Exception as e:
        log.error("Erro ao gerar plano: %s", e)
        return ""






def executar_plano(comando: str, executor_fn: Optional[Callable[[str], Any]] = None) -> str:
    plano = criar_plano(comando)
    if not plano:
        return "Falha no núcleo estratégico."
    if not executor_fn:
        return plano
    try:
        return executor_fn(plano)
    except Exception as e:
        return f"Erro ao executar plano: {e}"






def obter_chat_core(client):
    return client.chats.create(
        model=MODELO_GEMINI,
        config={
            "tools": TOOL_DECLARATIONS
        }
    )

class IARRouter:






    def __init__(self):
        self.modo: str = MODO_AUTO
        self.gemini_disponivel: Optional[bool] = None
        self.ollama_disponivel: Optional[bool] = None
        self.ultimo_check: float = 0.0
        self.intervalo: float = 20.0
        self.gemini_client: Optional[genai.Client] = None






    @property
    def modo_atual(self) -> str:
        return self.modo






    @property
    def status(self) -> dict:
        return {
            "modo": self.modo,
            "gemini": self.gemini_disponivel,
            "ollama": self.ollama_disponivel,
        }






    def definir_modo(self, modo: str) -> str:
        modo = modo.lower().strip()
        if modo not in (MODO_GEMINI, MODO_OLLAMA, MODO_AUTO):
            return "Modo inválido"
        self.modo = modo
        log.info("Modo IA alterado para: %s", modo)
        try:
            config.update_memory("api/config_jarvis.json", {"ia_mode": modo})
        except Exception as e:
            log.error("Erro ao salvar no config_jarvis.json: %s", e)
        return modo






    def carregar_modo_salvo(self) -> None:
        try:
            mem = config.load_memory()
            self.modo = mem.get("ia_mode", MODO_AUTO)
        except Exception as e:
            log.error("Erro ao carregar memória do roteador: %s", e)






    async def check_ollama(self) -> bool:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("http://127.0.0.1:11434/api/tags", timeout=2.0) as r:
                    return r.status == 200
        except Exception:
            return False






    def check_gemini(self) -> bool:
        return bool(getattr(config, "GEMINI_API_KEY", None))






    async def update_status(self) -> None:
        now = time.time()
        if now - self.ultimo_check < self.intervalo:
            return
        self.ultimo_check = now
        self.ollama_disponivel = await self.check_ollama()
        self.gemini_disponivel = self.check_gemini()






    async def responder(self, pergunta: str, nome: str = "David", memoria: str = "", imagem: Any = None) -> str:
        await self.update_status()
        system = build_system(nome, memoria)
        if self.modo == MODO_OLLAMA:
            return await self.ollama(pergunta, system)
        if self.modo == MODO_GEMINI:
            return await self.gemini(pergunta, system, imagem)
        if self.ollama_disponivel:
            return await self.ollama(pergunta, system)
        if self.gemini_disponivel:
            return await self.gemini(pergunta, system, imagem)
        return "Nenhuma IA disponível."






    async def gemini(self, pergunta: str, system: str, imagem: Any = None) -> str:
        try:
            if not self.gemini_client:
                self.gemini_client = get_client()
            chat = self.gemini_client.chats.create(
                model=MODELO_GEMINI,
                config={
                    "tools": TOOL_DECLARATIONS,
                    "system_instruction": system
                }
            )
            conteudo = [pergunta]
            if imagem:
                conteudo.append(imagem)
            response = chat.send_message(conteudo)
            while response.candidates[0].content.parts[0].function_call:
                respostas = []
                for part in response.candidates[0].content.parts:
                    if fn := part.function_call:
                        resultado = await self.call_local(fn.name, fn.args)
                        respostas.append({
                            "function_response": {
                                "name": fn.name,
                                "response": {"result": resultado}
                            }
                        })
                response = chat.send_message(respostas)
            return response.text
        except Exception as e:
            log.error("Exceção Gemini: %s", e)
            return "Erro no processamento."






    async def call_local(self, nome: str, args: dict) -> Any:
        try:
            func = DISPATCHER.get(nome)
            return func(args) if func else "Ferramenta não encontrada."
        except Exception as e:
            log.error("Erro na execução local: %s", e)
            return str(e)






    async def ollama(self, pergunta: str, system: str) -> str:
        try:
            async with aiohttp.ClientSession() as s:
                payload = {
                    "model": MODELO_OLLAMA,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": pergunta}
                    ],
                    "stream": False
                }
                async with s.post(URL_OLLAMA, json=payload, timeout=TIMEOUT_S) as r:
                    if r.status != 200:
                        return f"Erro Ollama ({r.status})"
                    data = await r.json()
                    return data.get("message", {}).get("content", "")
        except Exception as e:
            log.error("Exceção Ollama: %s", e)
            return str(e)






from vision.capture import iniciar_monitor as ligar_monitor
from vision.capture import parar_monitor as desligar_monitor
from vision.capture import status_monitor as info_monitor

router = IARRouter()
router.carregar_modo_salvo()