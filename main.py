from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import time

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from painel import PainelCore, set_loop
from audio.audio import ouvir_comando, falar
from engine.core import processar_comando, inicializar_ia
from engine.controller import get_shutdown_event
from storage.memory_bridge import sincronizar_config
from tasks.monitor import iniciar_sentinela, registrar_falar
from tasks.alarm import iniciar_sistema_alarmes, registrar_falar_alarme
from app_ul.interface import JarvisUI
from storage.wake import processar_wake
from integrations.telegram_bridge import iniciar_telegram

os.environ["QT_LOGGING_RULES"]          = "qt.qpa.window=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)







def achar_ollama() -> str | None:
    candidatos = [
        shutil.which("ollama"),
        rf"C:\Users\{os.environ.get('USERNAME', '')}\AppData\Local\Programs\Ollama\ollama.exe",
        r"C:\Program Files\Ollama\ollama.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
    ]
    return next((c for c in candidatos if c and os.path.isfile(c)), None)







def iniciar_ollama():
    caminho = achar_ollama()
    if not caminho:
        print("[OLLAMA] Executável não encontrado.")
        return

    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        print("[OLLAMA] Já ativo.")
    except Exception:
        print("[OLLAMA] Iniciando serviço...")
        subprocess.Popen(
            [caminho, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        time.sleep(3)







async def executar(comando: str, ui: PainelCore):
    if not isinstance(comando, str):
        return
        
    ui.bridge.dados_para_ui.emit(json.dumps({"log": f"Comando: {comando}"}))
    resposta = await processar_comando(comando)
    
    if resposta:
        ui.bridge.dados_para_ui.emit(json.dumps({"resposta": resposta}))
        await falar(resposta)







async def engine(ui: PainelCore):
    await inicializar_ia()
    registrar_falar(falar)
    registrar_falar_alarme(falar)

    iniciar_sentinela()
    iniciar_sistema_alarmes()

    threading.Thread(target=iniciar_telegram, daemon=True, name="TelegramBot").start()

    print("[Jarvis] Motor Sentinela - Ativado verificando tudo")

    while not get_shutdown_event().is_set():
        try:
            sincronizar_config()
            resultado = await ouvir_comando()

            if not resultado or not isinstance(resultado, str):
                continue

            lower = resultado.lower()
            if "jarvis" in lower:
                cmd = lower.replace("jarvis", "").strip()
            else:
                ativo, cmd = processar_wake(resultado)
                if not (ativo and cmd and isinstance(cmd, str)):
                    continue

            try:
                await asyncio.wait_for(executar(cmd, ui), timeout=45.0)
            except asyncio.TimeoutError:
                print("[SISTEMA] Comando cancelado por timeout.")

        except Exception as e:
            print(f"[LOOP] Erro: {e}")
            await asyncio.sleep(0.3)







def engine_thread(ui: PainelCore):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    set_loop(loop)
    try:
        loop.run_until_complete(engine(ui))
    finally:
        loop.close()







def iniciar_sistema():
    iniciar_ollama()
    try:
        ui = PainelCore()
        ui.closeEvent = lambda e: (e.ignore(), ui.hide())

        hud = JarvisUI()
        try:
            hud.btn_code.clicked.disconnect()
        except TypeError:
            pass

        hud.btn_code.clicked.connect(lambda: (ui.show(), ui.raise_(), ui.activateWindow()))
        hud.show()

        threading.Thread(target=engine_thread, args=(ui,), daemon=True, name="CoreEngine").start()
        sys.exit(app.exec())

    except Exception as e:
        print(f"[CRÍTICO] Erro na inicialização: {e}")







if __name__ == "__main__":
    iniciar_sistema()