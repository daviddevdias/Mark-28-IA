import sys
import os
import threading
import asyncio
import json
import subprocess
import requests
import time
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from painel import PainelCore, set_loop
from audio.audio import ouvir_comando, falar, interromper_voz
from engine.core import processar_comando, inicializar_ia
from engine.controller import get_shutdown_event
from storage.memory_bridge import sincronizar_config
from tasks.monitor import iniciar_sentinela, registrar_falar
from tasks.alarm import iniciar_sistema_alarmes, registrar_falar_alarme
from app_ul.interface import JarvisUI
from storage.wake import processar_wake, e_comando_monitoramento, e_comando_parar_monitor
from integrations.telegram_bridge import iniciar_telegram

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)







def _encontrar_ollama() -> str | None:
    candidatos = [
        shutil.which("ollama"),
        r"C:\Users\{}\AppData\Local\Programs\Ollama\ollama.exe".format(os.environ.get("USERNAME", "")),
        r"C:\Program Files\Ollama\ollama.exe",
        r"C:\Program Files (x86)\Ollama\ollama.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
    ]
    for caminho in candidatos:
        if caminho and os.path.isfile(caminho):
            return caminho
    return None







def iniciar_ollama() -> bool:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        modelos = [m["name"] for m in r.json().get("models", [])]
        print(f"[OLLAMA] Servico ja ativo. Modelos: {modelos}")
        return True
    except Exception:
        pass
    ollama_exe = _encontrar_ollama()
    if not ollama_exe:
        print("[OLLAMA] Executavel nao encontrado. Instale em https://ollama.com")
        return False
    print(f"[OLLAMA] Iniciando servico via: {ollama_exe}")
    try:
        subprocess.Popen(
            [ollama_exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception as e:
        print(f"[OLLAMA] Erro ao iniciar processo: {e}")
        return False
    for _ in range(15):
        time.sleep(1)
        try:
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            modelos = [m["name"] for m in r.json().get("models", [])]
            if modelos:
                print(f"[OLLAMA] Online. Modelos: {modelos}")
            else:
                print("[OLLAMA] Online mas sem modelos. Rode: ollama pull llama3.2")
            return True
        except Exception:
            continue
    print("[OLLAMA] AVISO: servico nao respondeu apos 15s.")
    return False







def _iniciar_subsistemas():
    sincronizar_config()
    iniciar_sentinela()
    iniciar_sistema_alarmes()
    t_telegram = threading.Thread(
        target=iniciar_telegram,
        daemon=True,
        name="TelegramBot",
    )
    t_telegram.start()







async def _executar_comando(resultado: str, ui: PainelCore) -> None:
    try:
        processou = await processar_comando(resultado)
        if processou:
            ui.bridge.dados_para_ui.emit(
                json.dumps({"resposta": f"Executado: {resultado}"})
            )
    except Exception as e:
        print(f"[COMANDO] Erro crítico: {e}")







async def engine_core_async(ui: PainelCore):
    await inicializar_ia()
    _iniciar_subsistemas()
    
    loop = asyncio.get_running_loop()
    registrar_falar_alarme(lambda texto: asyncio.run_coroutine_threadsafe(falar(texto), loop))
    
    shutdown_evt = get_shutdown_event()
    while not shutdown_evt.is_set():
        try:
            resultado = await ouvir_comando()
            if not resultado: 
                continue
            
            texto_lower = resultado.lower()
            comando_pronto = ""
            
            if "jarvis" in texto_lower:
                comando_pronto = texto_lower.replace("jarvis", "").strip()
            else:
                ativo, cmd_wake = processar_wake(resultado)
                if ativo and cmd_wake:
                    comando_pronto = cmd_wake
                    
            if not comando_pronto:
                continue
            
            try:
                await asyncio.wait_for(_executar_comando(comando_pronto, ui), timeout=45.0)
            except asyncio.TimeoutError:
                print("\n[SISTEMA] O comando demorou demais e foi cancelado para evitar travamentos.")
            
        except Exception as e:
            print(f"[LOOP] Erro: {e}")
            await asyncio.sleep(0.3)







def engine_core_wrapper(ui: PainelCore):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    set_loop(loop)
    try:
        loop.run_until_complete(engine_core_async(ui))
    finally:
        loop.close()







def iniciar_sistema():
    iniciar_ollama()
    try:
        ui = PainelCore()
        def ocultar_painel(event):
            event.ignore()
            ui.hide()
        ui.closeEvent = ocultar_painel
        hud = JarvisUI()
        def mostrar_painel_web():
            ui.show()
            ui.raise_()
            ui.activateWindow()
        try:
            hud.btn_code.clicked.disconnect()
        except TypeError: pass
        hud.btn_code.clicked.connect(mostrar_painel_web)
        hud.show()
        t = threading.Thread(
            target=engine_core_wrapper,
            args=(ui,),
            daemon=True,
            name="CoreEngine",
        )
        t.start()
        sys.exit(app.exec())
    except Exception as e:
        print(f"[SISTEMA] Erro fatal: {e}")
        sys.exit(1)







if __name__ == "__main__":
    iniciar_sistema()