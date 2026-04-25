from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import re
from collections import deque
from typing import Any, Optional, Awaitable, Callable

import aiohttp

import config
from engine.tools import TOOL_DECLARATIONS
from vision.capture import iniciar_monitor as iniciar_monitor_raw, parar_monitor, status_monitor, MonitorConfig
from audio.audio import falar, interromper_voz
from tasks.spotify_manager import spotify_stark
from tasks.smart_home import abrir_youtube_tv, desligar_tv, energia_tv, enviar_comando_tv, diagnosticar_falha_tv
from tasks.open_app import open_app
from tasks.computer_control import fechar_janela, minimizar_tudo, print_tela, bloquear_tela, limpar_lixeira
from tasks.alarm import adicionar_alarme, parar_alarme_total

log = logging.getLogger("engine.controller")

URL       = "http://127.0.0.1:11434/api/chat"
TIMEOUT   = 25.0
MAX_HIST  = 20
MAX_TOOLS = 5
COOL      = 30.0
OPTIONS   = {"num_predict": 300, "temperature": 0.7}

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

modelo:     str   = ""
disponivel: bool  = False
ultimo_check: float = 0.0

SHUTDOWN_EVENT = asyncio.Event()
Handler = Callable[[str], Awaitable[Optional[str]]]

PREFIXOS_SPOTIFY = [
    "buscar no spotify", "tocar no spotify", "procurar no spotify",
    "buscar spotify", "tocar spotify", "spotify",
    "tocar musica", "toca musica", "buscar musica",
    "colocar", "coloca", "tocar", "toca", "buscar", "busca",
    "musica", "musicas",
]

PREFIXOS_YOUTUBE = ["buscar no youtube", "tocar no youtube", "youtube"]

PREFIXOS_WEB = [
    "pesquisar na web", "pesquisar no google", "buscar na web",
    "pesquisar", "pesquisa", "buscar", "busca",
]







def system_msg(ctx: str) -> str:
    return SYSTEM.format(ctx=ctx[:300] or "Sem contexto")







def suporta_tools(modelo_alvo: str) -> bool:
    m = modelo_alvo.lower()
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
                print(f"OLLAMA Modelo: {modelo}")
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
        self.provedor = "ollama"







    @property
    def status(self) -> dict:
        return {"modelo": modelo, "ollama": disponivel, "provedor": self.provedor}







    @property
    def modo_atual(self) -> str:
        return self.provedor







    def definir_modo(self, modo: str) -> str:
        if modo == "gemini":
            if not config.GEMINI_API_KEY:
                return "Chave da API do Gemini ausente no sistema."
            self.provedor = "gemini"
            return "Conexão estabelecida com os servidores do Google Gemini."
        if modo == "openrouter" or modo == "auto":
            if not config.QWEN_API_KEY:
                return "Chave da API externa ausente no sistema."
            self.provedor = "openrouter"
            return "Modelos externos do OpenRouter ativados com sucesso."
        self.provedor = "ollama"
        return f"Processamento neural local ativado. Modelo: {modelo or 'nenhum detectado'}."







    def carregar_modo_salvo(self) -> None:
        pass







    def resetar_conversa(self) -> str:
        self.historico.clear()
        return "Conversa resetada."







    async def chat(self, messages: list[dict], tools: bool = True) -> dict | None:
        if self.provedor == "gemini":
            url_api = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            headers = {"Authorization": f"Bearer {config.GEMINI_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": "gemini-1.5-flash", "messages": messages, "temperature": 0.7}
            if tools:
                payload["tools"] = TOOL_DECLARATIONS
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(url_api, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                        if r.status != 200:
                            return None
                        data = await r.json()
                        return data.get("choices", [{}])[0].get("message")
            except Exception:
                return None

        if self.provedor == "openrouter":
            url_api = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {config.QWEN_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": config.CURRENT_MODEL, "messages": messages, "temperature": 0.7}
            if tools:
                payload["tools"] = TOOL_DECLARATIONS
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(url_api, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                        if r.status != 200:
                            return None
                        data = await r.json()
                        return data.get("choices", [{}])[0].get("message")
            except Exception:
                return None

        if not modelo:
            return None

        payload_ollama: dict = {"model": modelo, "messages": messages, "stream": False, "options": OPTIONS}
        if tools and suporta_tools(modelo):
            payload_ollama["tools"] = TOOL_DECLARATIONS
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(URL, json=payload_ollama,
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







    async def responder(self, pergunta: str, nome: str = "Chefe",
                        memoria: str = "", imagem: Any = None) -> str:
        if self.provedor == "ollama":
            await check()
            if not disponivel:
                await check(force=True)
            if not disponivel:
                return "Ollama offline. Rode 'ollama serve' no terminal ou mude para a nuvem."
            if not modelo:
                return "Nenhum modelo instalado. Rode: ollama pull llama3.2"

        self.historico.add("user", self.montar_content(pergunta, imagem))
        msgs = [{"role": "system", "content": system_msg(memoria)}] + self.historico.msgs()

        for i in range(MAX_TOOLS):
            msg = await self.chat(msgs) or await self.chat(msgs, tools=False)
            if msg is None:
                self.historico.pop()
                return "Perdemos o sinal de conexão com o servidor de IA. Tente novamente."

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

        return "Operação concluída nas linhas do servidor principal."







def get_shutdown_event() -> asyncio.Event:
    return SHUTDOWN_EVENT







def normalizar(texto: str) -> str:
    t = texto.lower().strip()
    t = re.sub(r"\s+", " ", t)
    for src, dst in [("ã","a"),("â","a"),("á","a"),("à","a"),("ê","e"),("é","e"),
                     ("í","i"),("ó","o"),("ô","o"),("õ","o"),("ú","u"),("ç","c")]:
        t = t.replace(src, dst)
    return t







def extrair_numero(texto: str) -> Optional[int]:
    m = re.search(r"\d+", texto)
    return int(m.group()) if m else None







def extrair_termo(cmd: str, prefixos: list) -> str:
    texto = cmd.strip()
    for p in sorted(prefixos, key=len, reverse=True):
        if texto.startswith(p):
            texto = texto[len(p):].strip()
            break
    return re.sub(r"^(a musica|o|a|as|os|um|uma)\s+", "", texto).strip()







async def silencio(cmd: str) -> str:
    interromper_voz()
    return ""







async def bloquear(cmd: str) -> str:
    bloquear_tela()
    return "Tela bloqueada."







async def minimizar(cmd: str) -> str:
    minimizar_tudo()
    return "Janelas minimizadas."







async def fechar(cmd: str) -> str:
    fechar_janela()
    return "Janela fechada."







async def screenshot(cmd: str) -> str:
    print_tela()
    return "Screenshot capturado."







async def limpar_lixo(cmd: str) -> str:
    limpar_lixeira()
    return "Lixeira limpa."







async def modo_trabalho(cmd: str) -> str:
    open_app({"app_name": "vscode"})
    open_app({"app_name": "chrome"})
    return "Modo trabalho ativado."







async def tv_ligar(cmd: str) -> str:
    if energia_tv(True):
        return "TV ligada."
    from tasks.smart_home import buscar_id_tv

    if not buscar_id_tv():
        return diagnosticar_falha_tv()
    return "Falha ao ligar a TV. Verifique o dispositivo no SmartThings."







async def tv_desligar(cmd: str) -> str:
    if desligar_tv():
        return "TV desligada."
    from tasks.smart_home import buscar_id_tv

    if not buscar_id_tv():
        return diagnosticar_falha_tv()
    return "Erro ao desligar a TV. Verifique o dispositivo no SmartThings."







async def tv_volume(cmd: str) -> str:
    nivel = extrair_numero(cmd)
    if nivel is None:
        return "Informe o nível de volume."
    nivel = max(0, min(100, nivel))
    return f"Volume {nivel}." if enviar_comando_tv("setVolume", "audioVolume", [nivel]) else "Erro no volume."







async def musica_spotify(cmd: str) -> str:
    cmd = re.sub(r"\s+", " ", re.sub(r"\bspotify\b", "", cmd)).strip()
    termo = extrair_termo(cmd, PREFIXOS_SPOTIFY)
    return spotify_stark.abrir_e_buscar(termo) if termo else "Informe a música ou artista."







async def musica(cmd: str) -> str:
    termo = extrair_termo(cmd, PREFIXOS_SPOTIFY)
    return spotify_stark.abrir_e_buscar(termo) if termo else "Informe a música ou artista."







async def playlist(cmd: str) -> str:
    return spotify_stark.listar_e_tocar_playlist(re.sub(r"\bplaylist\b", "", cmd).strip())







async def favoritas(cmd: str) -> str:
    return spotify_stark.tocar_minhas_favoritas()







async def pausar(cmd: str) -> str:
    spotify_stark.controlar_reproducao("pause")
    return ""







async def continuar(cmd: str) -> str:
    spotify_stark.controlar_reproducao("play")
    return ""







async def proxima(cmd: str) -> str:
    spotify_stark.controlar_reproducao("proxima")
    return ""







async def anterior(cmd: str) -> str:
    spotify_stark.controlar_reproducao("anterior")
    return ""







async def tv_youtube_app(cmd: str) -> str:
    return abrir_youtube_tv()







async def youtube(cmd: str) -> str:
    from tasks.browser import jarvis_web
    termo = extrair_termo(cmd, PREFIXOS_YOUTUBE)
    return jarvis_web.run(jarvis_web.tocar_youtube(termo)) if termo else "Informe o vídeo."







async def pesquisa(cmd: str) -> str:
    from tasks.browser import jarvis_web
    termo = extrair_termo(cmd, PREFIXOS_WEB)
    return jarvis_web.run(jarvis_web.smart_search(termo)) if termo else "Informe o termo."







async def monitorar_tela(cmd: str) -> str:
    from engine.core import ligar_monitoramento
    await ligar_monitoramento(cmd)
    return ""







async def desligar_monitor_cmd(cmd: str) -> str:
    from engine.core import desligar_monitoramento
    await desligar_monitoramento()
    return ""







async def status_monitor_cmd(cmd: str) -> str:
    from engine.core import status_do_sistema
    await status_do_sistema()
    return ""







async def olha_tela(cmd: str) -> str:
    from engine.core import analisar_tela_agora
    await analisar_tela_agora()
    return ""







async def olha_camera(cmd: str) -> str:
    from engine.core import analisar_camera_agora
    await analisar_camera_agora()
    return ""







async def agendar_alarme(cmd: str) -> str:
    from tasks.alarm import parse_alarme_voz

    data_iso, hora, missao = parse_alarme_voz(cmd)
    if not hora:
        match = re.search(r"(\d{1,2})[:h](\d{2})", cmd.replace(" e ", ":"))
        if match:
            hora = f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
        else:
            m2 = re.search(r"(\d{1,2})", cmd)
            hora = f"{int(m2.group(1)):02d}:00" if m2 else None
        if not hora:
            return "Diga a data e hora, por exemplo dia oito de maio as sete."
        missao = "Alarme por voz"
    return adicionar_alarme(hora, missao or "Alarme por voz", data=data_iso)







async def parar_alarme(cmd: str) -> str:
    return parar_alarme_total()

ROUTES: list[tuple[tuple[str, ...], Handler]] = [
    (("silencio",),            silencio),
    (("mutar",),               silencio),
    (("bloquear",),            bloquear),
    (("lock",),                bloquear),
    (("minimizar",),           minimizar),
    (("fechar",),              fechar),
    (("screenshot",),          screenshot),
    (("print", "tela"),        screenshot),
    (("limpar", "lixeira"),    limpar_lixo),
    (("limpar",),              limpar_lixo),
    (("trabalho",),            modo_trabalho),
    (("ligar", "tv"),          tv_ligar),
    (("liga", "tv"),           tv_ligar),
    (("desligar", "tv"),       tv_desligar),
    (("desliga", "tv"),        tv_desligar),
    (("abrir", "youtube", "tv"), tv_youtube_app),
    (("youtube", "na", "tv"),    tv_youtube_app),
    (("abrir", "youtube", "na", "tv"), tv_youtube_app),
    (("youtube", "na", "televisao"), tv_youtube_app),
    (("abrir", "youtube", "televisao"), tv_youtube_app),
    (("volume",),              tv_volume),
    (("spotify",),             musica_spotify),
    (("tocar", "musica"),      musica),
    (("musica",),              musica),
    (("playlist",),            playlist),
    (("favoritas",),           favoritas),
    (("pausar",),              pausar),
    (("continuar",),           continuar),
    (("proxima",),             proxima),
    (("anterior",),            anterior),
    (("youtube",),             youtube),
    (("pesquisar", "google"),  pesquisa),
    (("pesquisar", "web"),     pesquisa),
    (("pesquisar",),           pesquisa),
    (("pesquisa",),            pesquisa),
    (("monitorar", "tela"),    monitorar_tela),
    (("monitorar",),           monitorar_tela),
    (("desligar", "monitor"),  desligar_monitor_cmd),
    (("desativar", "monitor"), desligar_monitor_cmd),
    (("monitor", "status"),    status_monitor_cmd),
    (("olha", "tela"),         olha_tela),
    (("analisa", "tela"),      olha_tela),
    (("olha", "camera"),       olha_camera),
    (("camera",),              olha_camera),
    (("ver", "camera"),        olha_camera),
    (("agendar", "alarme"),    agendar_alarme),
    (("criar", "alarme"),      agendar_alarme),
    (("despertar",),           agendar_alarme),
    (("parar", "alarme"),      parar_alarme),
    (("parar", "musica"),      parar_alarme),
    (("desligar", "alarme"),   parar_alarme),
    (("acordei",),             parar_alarme),
]

PREFIXO_MAP: dict[str, str] = {}
for route in ROUTES:
    for kw in route[0]:
        for n in range(4, len(kw) + 1):
            PREFIXO_MAP.setdefault(kw[:n], kw)







def expandir(cmd: str) -> str:
    return " ".join(PREFIXO_MAP.get(tok, tok) for tok in cmd.split())







def route_matches(exp: str, keywords: tuple[str, ...]) -> bool:
    tokens = exp.split()
    return all(kw in tokens for kw in keywords)







def buscar_handler(cmd: str) -> Optional[Handler]:
    exp = expandir(cmd)
    for keywords, handler in ROUTES:
        if route_matches(exp, keywords):
            return handler
    return None







async def diretriz_clima(cmd_bruto: str, cmd: str) -> Optional[str]:
    from tasks import weather as wx

    if not wx.menciona_clima(cmd):
        return None
    cidade = wx.extrair_cidade_do_utterance(cmd_bruto)
    if "amanh" in cmd:
        msg = wx.verificar_chuva_amanha(cidade)
    else:
        msg = wx.obter_previsao_hoje(cidade)
    await falar(msg)
    return ""







async def processar_diretriz(texto: str) -> Optional[str]:
    cmd = normalizar(texto)
    clima = await diretriz_clima(texto, cmd)
    if clima is not None:
        return clima
    handler = buscar_handler(cmd)
    if handler is None:
        return None
    try:
        return await handler(cmd)
    except Exception as e:
        return f"Erro: {e}"

router = IARRouter()
router.carregar_modo_salvo()

info_monitor     = status_monitor
desligar_monitor = parar_monitor