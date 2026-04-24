from __future__ import annotations
import asyncio
import re
from typing import Awaitable, Callable, Dict, Optional
from audio.audio import falar, interromper_voz
from tasks.spotify_manager import spotify_stark
from tasks.smart_home import enviar_comando_tv, ligar_tv
from tasks.open_app import open_app
from tasks.computer_control import fechar_janela, minimizar_tudo, print_tela, bloquear_tela, limpar_lixeira
from tasks.alarm import adicionar_alarme, parar_alarme_total

SHUTDOWN_EVENT = asyncio.Event()
Handler = Callable[[str], Awaitable[Optional[str]]]







def get_shutdown_event() -> asyncio.Event:
    return SHUTDOWN_EVENT







def normalizar(texto: str) -> str:
    t = texto.lower().strip()
    t = re.sub(r"\s+", " ", t)
    for src, dst in [("ã","a"),("â","a"),("á","a"),("à","a"),
                     ("ê","e"),("é","e"),("è","e"),
                     ("í","i"),("î","i"),
                     ("ó","o"),("ô","o"),("õ","o"),
                     ("ú","u"),("û","u"),("ç","c")]:
        t = t.replace(src, dst)
    return t







def extrair_numero(texto: str) -> Optional[int]:
    m = re.search(r"\d+", texto)
    return int(m.group()) if m else None







_PREFIXOS_SPOTIFY = [
    "buscar no spotify", "busca no spotify", "tocar no spotify", "toca no spotify",
    "procurar no spotify", "pesquisar no spotify",
    "buscar spotify", "busca spotify", "tocar spotify", "toca spotify",
    "procurar spotify", "pesquisar spotify",
    "spotify buscar", "spotify tocar", "spotify busca", "spotify",
    "tocar musica", "toca musica", "buscar musica", "busca musica",
    "colocar", "coloca", "tocar", "toca", "buscar", "busca",
    "procurar", "procura", "pesquisar", "pesquisa",
    "musica", "musicas",
]

_PREFIXOS_YOUTUBE = [
    "buscar no youtube", "tocar no youtube", "toca no youtube",
    "youtube buscar", "youtube tocar", "youtube busca", "youtube",
]

_PREFIXOS_WEB = [
    "pesquisar na web", "pesquisa na web", "buscar na web",
    "pesquisar no google", "pesquisa no google", "buscar no google",
    "pesquisar", "pesquisa", "buscar", "busca", "procurar", "procura",
]







def extrair_termo(cmd: str, prefixos: list) -> str:
    texto = cmd.strip()
    for p in sorted(prefixos, key=len, reverse=True):
        if texto.startswith(p):
            texto = texto[len(p):].strip()
            break
    return re.sub(r"^(a musica|o|a|as|os|um|uma)\s+", "", texto).strip()







async def encerrar(cmd: str) -> str:
    await falar("Desligando sistema.")
    SHUTDOWN_EVENT.set()
    return ""







async def desligar_inteligente(cmd: str) -> str:
    if any(p in cmd for p in ("tv", "televisao")):
        return await tv_desligar(cmd)
    return await encerrar(cmd)







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







async def comando_print(cmd: str) -> str:
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
    return "TV ligada." if ligar_tv() else "Falha ao ligar TV."







async def tv_desligar(cmd: str) -> str:
    return "TV desligada." if enviar_comando_tv("off", "switch") else "Erro ao desligar TV."







async def tv_volume(cmd: str) -> str:
    nivel = extrair_numero(cmd)
    if nivel is None:
        return "Informe o nível de volume."
    nivel = max(0, min(100, nivel))
    ok = enviar_comando_tv("setVolume", "audioVolume", [nivel])
    return f"Volume ajustado para {nivel}." if ok else "Erro no volume."







async def musica_spotify(cmd: str) -> str:
    cmd_limpo = re.sub(r"\bspotify\b", "", cmd)
    cmd_limpo = re.sub(r"\s+", " ", cmd_limpo).strip()
    termo = extrair_termo(cmd_limpo, _PREFIXOS_SPOTIFY)
    if not termo:
        return "Informe o nome da música ou artista."
    return spotify_stark.abrir_e_buscar(termo)







async def musica(cmd: str) -> str:
    termo = extrair_termo(cmd, _PREFIXOS_SPOTIFY)
    if not termo:
        return "Informe o nome da música ou artista."
    return spotify_stark.abrir_e_buscar(termo)







async def playlist(cmd: str) -> str:
    termo = re.sub(r"\bplaylist\b", "", cmd).strip()
    return spotify_stark.listar_e_tocar_playlist(termo)







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







async def youtube(cmd: str) -> str:
    from tasks.browser import _jarvis_web
    termo = extrair_termo(cmd, _PREFIXOS_YOUTUBE)
    if not termo:
        return "Informe o que deseja ver no YouTube."
    return _jarvis_web.run(_jarvis_web.tocar_youtube(termo))







async def pesquisa(cmd: str) -> str:
    from tasks.browser import _jarvis_web
    termo = extrair_termo(cmd, _PREFIXOS_WEB)
    if not termo:
        return "Informe o termo de pesquisa."
    return _jarvis_web.run(_jarvis_web.smart_search(termo))







async def monitorar_tela(cmd: str) -> str:
    from engine.core import ligar_monitoramento
    await ligar_monitoramento(cmd)
    return ""







async def desligar_monitor(cmd: str) -> str:
    from engine.core import desligar_monitoramento
    await desligar_monitoramento()
    return ""







async def status_monitor(cmd: str) -> str:
    from engine.core import status_do_sistema
    await status_do_sistema()
    return ""







async def olha_tela(cmd: str) -> str:
    from engine.core import analisar_tela_agora
    await analisar_tela_agora()
    return ""







async def comando_alarme(cmd: str) -> str:
    match = re.search(r"(\d{1,2})[:h](\d{2})", cmd.replace(" e ", ":"))
    if not match:
        match = re.search(r"(\d{1,2})", cmd)
        if match:
            hora = f"{int(match.group(1)):02d}:00"
        else:
            return "Por favor, me informe a hora do alarme."
    else:
        hora = f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
    return adicionar_alarme(hora, "Alarme programado por voz")







async def comando_parar_alarme(cmd: str) -> str:
    return parar_alarme_total()







_ROUTES: list[tuple[tuple[str, ...], Handler]] = [
    (("encerrar",),              encerrar),
    (("desligar", "sistema"),    encerrar),
    (("desligar",),              desligar_inteligente),
    (("silencio",),              silencio),
    (("mutar",),                 silencio),

    (("bloquear",),              bloquear),
    (("lock",),                  bloquear),
    (("minimizar",),             minimizar),
    (("fechar",),                fechar),
    (("screenshot",),            comando_print),
    (("print", "tela"),          comando_print),
    (("limpar", "lixeira"),      limpar_lixo),
    (("limpar",),                limpar_lixo),
    (("trabalho",),              modo_trabalho),
    (("ligar", "tv"),            tv_ligar),
    (("liga", "tv"),             tv_ligar),
    (("tv", "ligar"),            tv_ligar),
    (("desligar", "tv"),         tv_desligar),
    (("desliga", "tv"),          tv_desligar),
    (("tv", "desligar"),         tv_desligar),
    (("volume",),                tv_volume),
    (("spotify",),               musica_spotify),
    (("tocar", "musica"),        musica),
    (("toca", "musica"),         musica),
    (("colocar", "musica"),      musica),
    (("musica",),                musica),
    (("playlist",),              playlist),
    (("favoritas",),             favoritas),
    (("pausar",),                pausar),
    (("continuar",),             continuar),
    (("proxima",),               proxima),
    (("anterior",),              anterior),
    (("youtube",),               youtube),
    (("pesquisar", "google"),    pesquisa),
    (("pesquisar", "web"),       pesquisa),
    (("pesquisar",),             pesquisa),
    (("pesquisa",),              pesquisa),
    (("monitorar", "tela"),      monitorar_tela),
    (("monitorar",),             monitorar_tela),
    (("desligar", "monitor"),    desligar_monitor),
    (("desativar", "monitor"),   desligar_monitor),
    (("monitor", "status"),      status_monitor),
    (("olha", "tela"),           olha_tela),
    (("analisa", "tela"),        olha_tela),
    (("agendar", "alarme"),      comando_alarme),
    (("agendar", "horario"),     comando_alarme),
    (("criar", "alarme"),        comando_alarme),
    (("despertar",),             comando_alarme),
    (("parar", "alarme"),        comando_parar_alarme),
    (("parar", "musica"),        comando_parar_alarme),
    (("desligar", "alarme"),     comando_parar_alarme),
    (("acordei",),               comando_parar_alarme),
    (("ja", "acordei"),          comando_parar_alarme),
]

_PREFIXO_PARA_CHAVE: dict[str, str] = {}

for _route in _ROUTES:
    for _kw in _route[0]:
        for _n in range(4, len(_kw) + 1):
            _PREFIXO_PARA_CHAVE.setdefault(_kw[:_n], _kw)







def expandir(cmd: str) -> str:
    tokens = cmd.split()
    expandido = []
    for tok in tokens:
        expandido.append(_PREFIXO_PARA_CHAVE.get(tok, tok))
    return " ".join(expandido)







def buscar_comando(cmd: str) -> Optional[Handler]:
    cmd_exp = expandir(cmd)
    for keywords, handler in _ROUTES:
        if all(kw in cmd_exp for kw in keywords):
            return handler
    return None







async def processar_diretriz(texto: str) -> Optional[str]:
    cmd = normalizar(texto)
    handler = buscar_comando(cmd)
    if handler is None:
        return None
    try:
        return await handler(cmd)
    except Exception as e:
        return f"Erro ao executar comando: {e}"