import os
import asyncio
import queue
import threading
import time
import pygame
import speech_recognition as sr
import edge_tts
import config





# LOCK GLOBAL DE AUDIO (geral)
audio_io_lock = threading.RLock()

# LOCK EXCLUSIVO DO MICROFONE (CRÍTICO)
mic_lock = threading.Lock()





# FILAS
mic_cmd: queue.Queue = queue.Queue()
mic_rpy: queue.Queue = queue.Queue()

mic_thread: threading.Thread | None = None





# CONTROLE DE ESTADO
sleep_event = threading.Event()
falando = False
interrompido = False
barge_stop_event = threading.Event()
barge_thread: threading.Thread | None = None





# CONFIG RECONHECEDOR
reconhecedor = sr.Recognizer()
reconhecedor.pause_threshold = 0.4
reconhecedor.non_speaking_duration = 0.2
reconhecedor.energy_threshold = 250
reconhecedor.dynamic_energy_threshold = False





# PARAR SOM DO PYGAME
def suspender_pygame_mixer_para_capture():
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except:
                pass
            pygame.mixer.quit()
    except:
        pass





# NORMALIZAR MICROFONE
def normalizar_indice_microfone(idx):
    try:
        return int(idx) if idx is not None and int(idx) >= 0 else None
    except:
        return None





# UI VOZ
def ui_falar(on, vol=1.0):
    try:
        config.notificar_voz_painel(on, vol)
    except:
        pass





# INTERROMPER VOZ
def interromper_voz():
    global interrompido

    interrompido = True
    ui_falar(False)
    sleep_event.set()

    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except:
        pass





# LOOP DE INTERRUPÇÃO (BARGE-IN)
def barge_loop():
    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))

    rec = sr.Recognizer()
    rec.energy_threshold = 220

    while not barge_stop_event.is_set():

        if not falando or interrompido:
            break

        try:
            kwargs = {}
            if idx is not None:
                kwargs["device_index"] = idx

            #
            with mic_lock:
                with sr.Microphone(**kwargs) as source:

                    audio = rec.listen(source, timeout=0.3, phrase_time_limit=1)

            try:
                txt = rec.recognize_google(audio, language="pt-BR").lower().strip()
            except:
                txt = ""

            if txt:
                print(f"ouvido durante fala: {txt}")
                interromper_voz()
                break

        except sr.WaitTimeoutError:
            pass
        except:
            pass

        time.sleep(0.05)





# INICIAR BARGE
def iniciar_listener_interrupcao():
    global barge_thread

    barge_stop_event.clear()

    if barge_thread and barge_thread.is_alive():
        return

    barge_thread = threading.Thread(target=barge_loop, daemon=True)
    barge_thread.start()





# PARAR BARGE
def parar_listener_interrupcao():
    barge_stop_event.set()





# REPRODUZIR AUDIO
def reproduzir_sync(arquivo):
    global falando, interrompido

    with audio_io_lock:

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(arquivo)
        pygame.mixer.music.play()

        falando = True
        interrompido = False
        sleep_event.clear()

        iniciar_listener_interrupcao()

        while pygame.mixer.music.get_busy():
            if interrompido:
                break
            sleep_event.wait(0.05)

        pygame.mixer.music.stop()

    parar_listener_interrupcao()

    falando = False
    ui_falar(False)





# FALAR
async def falar(texto):
    if not texto.strip():
        return

    arquivo = os.path.join(config.ASSETS_DIR, "output.mp3")

    try:
        if os.path.exists(arquivo):
            os.remove(arquivo)
    except:
        pass

    await edge_tts.Communicate(texto, config.voz_atual).save(arquivo)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, reproduzir_sync, arquivo)





# CAPTURA DE VOZ
def captura_sync():

    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))

    with audio_io_lock:
        suspender_pygame_mixer_para_capture()

    print("\nEscutando...\n")

    try:
        kwargs = {}
        if idx is not None:
            kwargs["device_index"] = idx

        # 🔒 LOCK DO MICROFONE (ESSENCIAL)
        with mic_lock:
            with sr.Microphone(**kwargs) as source:

                reconhecedor.adjust_for_ambient_noise(source, duration=0.2)

                audio = reconhecedor.listen(source, timeout=5, phrase_time_limit=6)

        texto = reconhecedor.recognize_google(audio, language="pt-BR").lower().strip()

        print(f"ouvido: {texto}")

        return texto

    except:
        return ""





# LOOP MICROFONE
def run_mic_loop():
    while True:
        mic_cmd.get()
        resultado = captura_sync()
        mic_rpy.put(resultado)





# GARANTE THREAD
def ensure_mic_thread():
    global mic_thread

    if mic_thread and mic_thread.is_alive():
        return

    mic_thread = threading.Thread(target=run_mic_loop, daemon=True)
    mic_thread.start()





# OUVIR
def ouvir_sync_queued():
    ensure_mic_thread()

    mic_cmd.put(True)

    try:
        return mic_rpy.get(timeout=40)
    except:
        return ""





# ASYNC
async def ouvir_comando():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ouvir_sync_queued)