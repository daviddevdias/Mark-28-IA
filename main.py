from __future__ import annotations

import os
import sys
import faulthandler

# 1. Habilita o rastreio de quedas silenciosas (C/C++) que fecham o Python do nada
faulthandler.enable()

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "hide")

# 2. Desativa a renderização via GPU da interface para evitar crashs na RX 580
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging --disable-gpu --no-sandbox"

import asyncio
import json
import logging
import shutil
import subprocess
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
try:
    app.setQuitOnLastWindowClosed(False)
except Exception:
    pass
log = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("faster_whisper").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
sys.argv.append("--disable-gpu")
sys.argv.append("--disable-software-rasterizer")
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"

async def executar(cmd: str, ui: PainelCore):
    await processar_comando(cmd)

async def engine(ui: PainelCore):
    await inicializar_ia()
    iniciar_sentinela()
    iniciar_sistema_alarmes()
    sincronizar_config()
    try:
        from brain.event_bus import bus
        from brain.watchdog import watchdog, registrar_modulos_padrao
        loop = asyncio.get_running_loop()
        bus.registrar_loop(loop)
        registrar_modulos_padrao()
        watchdog.iniciar()
    except Exception as e:
        log.warning("watchdog/event_bus não carregou: %s", e)
    try:
        from storage.observability import registrar_acao, purgar_antigos
        purgar_antigos(dias=7)
        registrar_acao("startup", modulo="main", descricao="Jarvis inicializado", sucesso=True)
    except Exception as e:
        log.warning("observability não carregou: %s", e)
    
    threading.Thread(target=iniciar_telegram, daemon=True, name="TelegramBot").start()
    
    while not get_shutdown_event().is_set():
        try:
            config.recarregar_identidade_painel()
            resultado = await ouvir_comando()
            if not resultado or not isinstance(resultado, str):
                continue
            ativo, cmd = processar_wake(resultado)
            if not ativo or not isinstance(cmd, str):
                continue
            cmd = cmd.strip()
            if not cmd:
                await falar(resposta_ativacao_aleatoria())
                continue
            await executar(cmd, ui)
        except Exception:
            log.exception("erro no ciclo principal")
            await asyncio.sleep(0.3)

def engine_thread(ui: PainelCore):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    set_loop(loop)
    registrar_loop_alarme(loop)
    registrar_loop_monitor_voz(loop)
    try:
        loop.run_until_complete(engine(ui))
    finally:
        loop.close()

def iniciar_sistema():
    try:
        ui = PainelCore()
        hud = JarvisUI()
        try:
            hud.btn_code.clicked.disconnect()
        except TypeError:
            pass
        hud.btn_code.clicked.connect(lambda: (ui.show(), ui.raise_(), ui.activateWindow()))
        hud.show()
        registrar_falar(falar)
        registrar_falar_alarme(falar)
        threading.Thread(target=engine_thread, args=(ui,), daemon=True, name="CoreEngine").start()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Falha na subida: {e}")

if __name__ == "__main__":
    iniciar_sistema()