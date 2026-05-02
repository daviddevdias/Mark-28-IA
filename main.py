from __future__ import annotations

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "hide")

import asyncio
import json
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
from audio.audio import ouvir_comando, falar
from engine.core import processar_comando, inicializar_ia
from engine.controller import get_shutdown_event
from storage.memory_bridge import sincronizar_config
from tasks.monitor import iniciar_sentinela, registrar_falar, registrar_loop_monitor_voz
from tasks.alarm import iniciar_sistema_alarmes, registrar_falar_alarme, registrar_loop_alarme
from app_ul.interface import JarvisUI
from storage.wake import processar_wake, resposta_ativacao_aleatoria
from integrations.telegram_bridge_auth_patch import iniciar_telegram

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"







QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)
try:
    app.setQuitOnLastWindowClosed(False)
except Exception:
    pass
log = logging.getLogger(__name__)







def achar_ollama() -> str | None:
    candidatos = [
        shutil.which("ollama"),
        rf"C:\Users\{os.environ.get('USERNAME', '')}\AppData\Local\Programs\Ollama\ollama.exe",
        r"C:\Program Files\Ollama\ollama.exe",
    ]
    for c in candidatos:
        if c and os.path.exists(c):
            return c
    return None







def iniciar_ollama():
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        if r.status_code == 200:
            print("OLLAMA Já ativo.")
            return
    except Exception:
        pass


    path = achar_ollama()
    if path:
        print("OLLAMA Inicializando com suporte AMD RX 580...")
        env = os.environ.copy()
        env["HSA_OVERRIDE_GFX_VERSION"] = "8.0.3"
        env["OLLAMA_ORIGINS"] = "*"
        subprocess.Popen([path, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        time.sleep(3)







async def executar(cmd: str, ui: PainelCore):
    resposta = await processar_comando(cmd)
    if resposta:
        await falar(resposta)







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
    except Exception as e:
        log.critical("Engine finalizada com erro: %s", e)
    finally:
        loop.close()







def iniciar_sistema():
    ui = PainelCore()


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


        core_thread = threading.Thread(target=engine_thread, args=(ui,), daemon=True, name="CoreEngine")
        core_thread.start()


        exit_code = app.exec()
        get_shutdown_event().set()
        sys.exit(exit_code)


    except Exception as e:
        print(f"Falha na subida do sistema: {e}")
        sys.exit(1)







if __name__ == "__main__":
    iniciar_sistema()