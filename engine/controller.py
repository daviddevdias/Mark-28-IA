import asyncio
import re
from typing import Callable, Awaitable, Optional, Dict, Any

from audio.audio import falar, interromper_voz

from tasks.spotify_manager import spotify_stark
from tasks.smart_home import enviar_comando_tv, ligar_tv
from tasks.open_app import open_app
from tasks.computer_control import fechar_janela, minimizar_tudo, print_tela, bloquear_tela, limpar_lixeira

SHUTDOWN_EVENT = asyncio.Event()

Handler = Callable[[str], Awaitable[Optional[str]]]


def get_shutdown_event() -> asyncio.Event:
    return SHUTDOWN_EVENT


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.lower()).strip()


def extrair_numero(texto: str) -> Optional[int]:
    match_obj = re.search(r"\d+", texto)
    if match_obj:
        return int(match_obj.group())
    return None


async def encerrar(cmd: str) -> str:
    await falar("Desligando sistema.")
    SHUTDOWN_EVENT.set()
    return ""


async def silencio(cmd: str) -> str:
    interromper_voz()
    return ""


async def bloquear(cmd: str) -> str:
    bloquear_tela()
    return "Bloqueado"


async def minimizar(cmd: str) -> str:
    minimizar_tudo()
    return "Minimizado"


async def fechar(cmd: str) -> str:
    fechar_janela()
    return "Fechado"


async def comando_print(cmd: str) -> str:
    print_tela()
    return "Screenshot"


async def limpar_lixo(cmd: str) -> str:
    limpar_lixeira()
    return "Lixeira limpa"


async def modo_trabalho(cmd: str) -> str:
    open_app({"app_name": "vscode"})
    open_app({"app_name": "chrome"})
    return "Modo trabalho ativado"


async def tv_ligar(cmd: str) -> str:
    return "TV ligada" if ligar_tv() else "Falha TV"


async def tv_desligar(cmd: str) -> str:
    return "TV desligada" if enviar_comando_tv("off", "switch") else "Erro TV"


async def tv_volume(cmd: str) -> str:
    nivel = extrair_numero(cmd)
    if nivel is None:
        return "Informe volume"
    nivel = max(0, min(100, nivel))
    ok = enviar_comando_tv("setVolume", "audioVolume", [nivel])
    return f"Volume {nivel}" if ok else "Erro volume"


async def musica(cmd: str) -> str:
    termo = normalizar(cmd).replace("musica", "").replace("tocar", "").strip()
    if not termo:
        return "Informe musica"
    return spotify_stark.abrir_e_buscar(termo)


async def playlist(cmd: str) -> str:
    termo = normalizar(cmd).replace("playlist", "").strip()
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
    termo = normalizar(cmd).replace("youtube", "").strip()
    return _jarvis_web.run(_jarvis_web.tocar_youtube(termo))


async def pesquisa(cmd: str) -> str:
    from tasks.browser import _jarvis_web
    termo = normalizar(cmd).replace("pesquisar", "").replace("pesquisa", "").strip()
    return _jarvis_web.run(_jarvis_web.smart_search(termo))


# FIX: comandos de monitor existiam no core.py mas nunca chegavam aqui
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


COMMANDS: Dict[str, Handler] = {
    "encerrar": encerrar,
    "desligar": encerrar,
    "silencio": silencio,
    "mutar": silencio,
    "bloquear": bloquear,
    "lock": bloquear,
    "minimizar": minimizar,
    "fechar": fechar,
    "print": comando_print,
    "screenshot": comando_print,
    "limpar": limpar_lixo,
    "trabalho": modo_trabalho,
    "tv ligar": tv_ligar,
    "tv desligar": tv_desligar,
    "volume": tv_volume,
    "musica": musica,
    "playlist": playlist,
    "favoritas": favoritas,
    "pausar": pausar,
    "continuar": continuar,
    "proxima": proxima,
    "anterior": anterior,
    "youtube": youtube,
    "pesquisa": pesquisa,
    "pesquisar": pesquisa,
    # FIX: monitor commands were defined in core.py but never wired to COMMANDS
    "monitorar tela": monitorar_tela,
    "monitorar": monitorar_tela,
    "desligar monitor": desligar_monitor,
    "desativar monitor": desligar_monitor,
    "monitor status": status_monitor,
    "olha a tela": olha_tela,
    "analisa a tela": olha_tela,
}


def buscar_comando(cmd: str) -> Optional[str]:
    # Prioriza chaves maiores (mais específicas) para evitar match errado
    # Ex: "tv ligar" deve bater antes de "tv"
    for key in sorted(COMMANDS, key=len, reverse=True):
        if key in cmd:
            return key
    return None


async def processar_diretriz(texto: str) -> Optional[str]:
    cmd = normalizar(texto)
    key = buscar_comando(cmd)
    if not key:
        return None
    handler = COMMANDS[key]
    try:
        return await handler(cmd)
    except Exception:
        return "Erro execução"