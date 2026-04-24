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







def iniciar_ollama() -> bool:
    try:
        r      = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"[OLLAMA] Já ativo. Modelos: {models}")
        return True
    except Exception:
        pass

    exe = achar_ollama()
    if not exe:
        print("[OLLAMA] Executável não encontrado. Instale em https://ollama.com")
        return False

    print(f"[OLLAMA] Iniciando via: {exe}")
    try:
        subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception as e:
        print(f"[OLLAMA] Erro ao iniciar: {e}")
        return False

    for _ in range(15):
        time.sleep(1)
        try:
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"[OLLAMA] Online. Modelos: {models or ['nenhum — rode: ollama pull llama3.2']}")
            return True
        except Exception:
            continue

    print("[OLLAMA] Não respondeu após 15s.")
    return False







def iniciar_subsistemas():
    sincronizar_config()
    iniciar_sentinela()
    iniciar_sistema_alarmes()
    threading.Thread(target=iniciar_telegram, daemon=True, name="TelegramBot").start()







async def executar(comando: str, ui: PainelCore) -> None:
    try:
        if await processar_comando(comando):
            ui.bridge.dados_para_ui.emit(json.dumps({"resposta": f"Executado: {comando}"}))
    except Exception as e:
        print(f"[COMANDO] Erro: {e}")







async def engine(ui: PainelCore):
    await inicializar_ia()
    iniciar_subsistemas()

    loop = asyncio.get_running_loop()
    registrar_falar_alarme(lambda txt: asyncio.run_coroutine_threadsafe(falar(txt), loop))

    shutdown = get_shutdown_event()
    while not shutdown.is_set():
        try:
            resultado = await ouvir_comando()
            if not resultado:
                continue

            lower = resultado.lower()
            if "jarvis" in lower:
                cmd = lower.replace("jarvis", "").strip()
            else:
                ativo, cmd = processar_wake(resultado)
                if not (ativo and cmd):
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
        print(f"[SISTEMA] Erro fatal: {e}")
        sys.exit(1)







if __name__ == "__main__":
    iniciar_sistema()