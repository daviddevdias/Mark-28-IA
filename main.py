"""
main.py — Ponto de entrada do Jarvis
Sobe a interface gráfica, inicia o Ollama e dispara a engine em thread separada.
"""

from __future__ import annotations

import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "hide")
os.environ["QT_LOGGING_RULES"]         = "qt.qpa.window=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"

import asyncio
import logging
import shutil
import subprocess
import sys
import threading
import time

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

import config
from painel import PainelCore, set_loop
from audio.voz import ouvir_comando, falar
from engine.core import processar_comando, inicializar_ia
from engine.controller import get_shutdown_event
from storage.memory_bridge import sincronizar_config
from tasks.monitor import iniciar_sentinela, registrar_falar, registrar_loop_monitor_voz
from tasks.alarm import iniciar_sistema_alarmes, registrar_falar_alarme, registrar_loop_alarme
from app_ul.interface import JarvisUI
from storage.wake import processar_wake, resposta_ativacao_aleatoria
from integrations.telegram_bridge_auth_patch import iniciar_telegram

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

log = logging.getLogger(__name__)


# ── Ollama ────────────────────────────────────────────────────────────────────

def achar_ollama() -> str | None:
    """Procura o executável do Ollama nos lugares comuns."""
    candidatos = [
        shutil.which("ollama"),
        rf"C:\Users\{os.environ.get('USERNAME', '')}\AppData\Local\Programs\Ollama\ollama.exe",
        r"C:\Program Files\Ollama\ollama.exe",
    ]
    return next((c for c in candidatos if c and os.path.exists(c)), None)


def iniciar_ollama():
    """Liga o Ollama se ainda não estiver rodando."""
    try:
        if requests.get("http://127.0.0.1:11434/api/tags", timeout=2).status_code == 200:
            print("OLLAMA Já ativo.")
            return
    except Exception:
        pass

    path = achar_ollama()
    if path:
        print("OLLAMA Inicializando com suporte AMD RX 580...")
        env = {**os.environ, "HSA_OVERRIDE_GFX_VERSION": "8.0.3", "OLLAMA_ORIGINS": "*"}
        subprocess.Popen([path, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        time.sleep(3)


# ── Loop principal assíncrono ─────────────────────────────────────────────────

async def engine(ui: PainelCore):
    """Loop principal: inicializa tudo e fica escutando comandos de voz."""
    await inicializar_ia()
    iniciar_sentinela()
    iniciar_sistema_alarmes()
    sincronizar_config()

    # Watchdog e event bus (monitoramento de saúde dos módulos)
    try:
        from brain.event_bus import bus
        from brain.watchdog import watchdog, registrar_modulos_padrao
        bus.registrar_loop(asyncio.get_running_loop())
        registrar_modulos_padrao()
        watchdog.iniciar()
    except Exception as e:
        log.warning("watchdog/event_bus não carregou: %s", e)

    # Observabilidade (logs de ações)
    try:
        from storage.observability import registrar_acao, purgar_antigos
        purgar_antigos(dias=7)
        registrar_acao("startup", modulo="main", descricao="Jarvis inicializado", sucesso=True)
    except Exception as e:
        log.warning("observability não carregou: %s", e)

    # Bot do Telegram (roda em thread separada)
    threading.Thread(target=iniciar_telegram, daemon=True, name="TelegramBot").start()

    # Ciclo de escuta de voz
    while not get_shutdown_event().is_set():
        try:
            config.recarregar_identidade_painel()

            resultado = await ouvir_comando()
            if not resultado or not isinstance(resultado, str):
                continue

            # Verifica se a palavra de ativação foi dita
            ativo, cmd = processar_wake(resultado)
            if not ativo or not isinstance(cmd, str):
                continue

            cmd = cmd.strip()
            if not cmd:
                # Ativação sem comando — responde algo curto
                await falar(resposta_ativacao_aleatoria())
                continue

            # Processa o comando (a função já chama falar() internamente)
            await processar_comando(cmd)

        except Exception:
            log.exception("erro no ciclo principal")
            await asyncio.sleep(0.3)


def engine_thread(ui: PainelCore):
    """Roda o loop assíncrono da engine em uma thread dedicada."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    set_loop(loop)
    registrar_loop_alarme(loop)
    registrar_loop_monitor_voz(loop)
    try:
        loop.run_until_complete(engine(ui))
    except Exception as e:
        log.critical("Engine finalizada com erro: %s", e)
    finally:
        loop.close()


# ── Inicialização ─────────────────────────────────────────────────────────────

def iniciar_sistema():
    """Monta a UI, liga o Ollama e dispara a engine."""
    try:
        ui  = PainelCore()   # Painel de configuração (janela secundária)
        hud = JarvisUI()     # HUD principal (janela flutuante)

        iniciar_ollama()

        # Botão do HUD abre o painel de configuração
        try:
            hud.btn_code.clicked.disconnect()
        except TypeError:
            pass
        hud.btn_code.clicked.connect(lambda: (ui.show(), ui.raise_(), ui.activateWindow()))
        hud.show()

        # Registra a função falar() nos sistemas de alarme e sentinela
        registrar_falar(falar)
        registrar_falar_alarme(falar)

        # Engine roda em thread separada para não travar a UI
        threading.Thread(target=engine_thread, args=(ui,), daemon=True, name="CoreEngine").start()

        exit_code = app.exec()
        get_shutdown_event().set()
        sys.exit(exit_code)

    except Exception as e:
        print(f"Falha na subida do sistema: {e}")
        sys.exit(1)


if __name__ == "__main__":
    iniciar_sistema()