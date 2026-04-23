import sys
import os
import threading
import asyncio
import json

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
from storage.wake import processar_wake, RESPOSTAS_ATIVACAO
from integrations.telegram_bridge import iniciar_telegram




BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

_processando = False


def _iniciar_subsistemas():
    sincronizar_config()
    iniciar_sentinela()
    iniciar_sistema_alarmes()


async def _executar_comando(resultado: str, ui: PainelCore) -> None:
    global _processando
    try:
        processou = await processar_comando(resultado)
        if processou:
            ui.bridge.dados_para_ui.emit(json.dumps({"resposta": "Comando processado."}))
    except Exception as e:
        print(f"[CORE] Erro ao processar: {e}")
    finally:
        _processando = False


async def engine_core_async(ui: PainelCore):
    global _processando

    loop = asyncio.get_running_loop()
    set_loop(loop)

    try:
        from engine.ollama_boot import iniciar_ollama
        await loop.run_in_executor(None, iniciar_ollama)
    except Exception as e:
        print(f"[OLLAMA] Falha ao iniciar: {e}")

    await inicializar_ia()

    _iniciar_subsistemas()

    falar_fn = lambda t: asyncio.run_coroutine_threadsafe(falar(t), loop)
    registrar_falar(falar_fn)
    registrar_falar_alarme(falar_fn)

    shutdown = get_shutdown_event()

    while not shutdown.is_set():
        try:
            frase_bruta = await asyncio.wait_for(ouvir_comando(), timeout=8)

            if not frase_bruta:
                continue

            ativado, resultado = processar_wake(frase_bruta)

            if not ativado:
                continue

            if resultado in RESPOSTAS_ATIVACAO:
                asyncio.create_task(falar(resultado))
                ui.bridge.dados_para_ui.emit(json.dumps({"resposta": resultado}))
                continue

            if frase_bruta.strip().lower() in ("para", "chega", "silencio", "silêncio", "stop"):
                interromper_voz()
                _processando = False
                continue

            if _processando:
                print("[CORE] Comando ignorado — ainda processando anterior.")
                continue

            _processando = True
            asyncio.create_task(_executar_comando(resultado, ui))

        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"[LOOP] Erro: {e}")
            await asyncio.sleep(0.3)


def engine_core_wrapper(ui: PainelCore):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(engine_core_async(ui))
    finally:
        loop.close()


def iniciar_sistema():
    try:
        ui = PainelCore()
        ui.show()

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
        except TypeError:
            pass

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
    iniciar_telegram()