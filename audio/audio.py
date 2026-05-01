import os
import asyncio
import queue
import threading
import time
import pygame
import speech_recognition as sr
import edge_tts
import config











audio_io_lock = threading.RLock()

mic_lock = threading.Lock()






mic_cmd: queue.Queue = queue.Queue()
mic_rpy: queue.Queue = queue.Queue()



mic_thread: threading.Thread | None = None





sleep_event = threading.Event()
falando = False
interrompido = False
barge_stop_event = threading.Event()
barge_thread: threading.Thread | None = None





reconhecedor = sr.Recognizer()
reconhecedor.pause_threshold = 0.4
reconhecedor.non_speaking_duration = 0.2
reconhecedor.energy_threshold = 250
reconhecedor.dynamic_energy_threshold = False







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







def normalizar_indice_microfone(idx):
    try:
        return int(idx) if idx is not None and int(idx) >= 0 else None
    except:
        return None







def ui_falar(on, vol=1.0):
    try:
        config.notificar_voz_painel(on, vol)
    except:
        pass







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

            with mic_lock:
                with sr.Microphone(**kwargs) as source:
                    try:
                        audio = rec.listen(source, timeout=0.5, phrase_time_limit=1.5)
                    except sr.WaitTimeoutError:
                        continue

            try:
                txt = rec.recognize_google(audio, language="pt-BR").lower().strip()
            except:
                txt = ""

            if txt:
                print(f"ouvido durante fala: {txt}")
                interromper_voz()
                break

        except:
            pass

        time.sleep(0.1)







def iniciar_listener_interrupcao():
    global barge_thread

    barge_stop_event.clear()

    if barge_thread and barge_thread.is_alive():
        return

    barge_thread = threading.Thread(target=barge_loop, daemon=True)
    barge_thread.start()







def parar_listener_interrupcao():
    barge_stop_event.set()







def reproduzir_sync(arquivo):
    global falando, interrompido

    with audio_io_lock:

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        try:
            pygame.mixer.music.load(arquivo)
            pygame.mixer.music.play()
        except:
            return

        falando = True
        interrompido = False
        sleep_event.clear()

        iniciar_listener_interrupcao()

        while pygame.mixer.music.get_busy():
            if interrompido:
                break
            sleep_event.wait(0.1)

        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.unload()
        except:
            pass

    parar_listener_interrupcao()

    falando = False
    ui_falar(False)







async def falar(texto):
    if not texto.strip():
        return

    arquivo = os.path.join(config.ASSETS_DIR, "output.mp3")

    try:
        if os.path.exists(arquivo):
            if pygame.mixer.get_init():
                pygame.mixer.music.unload()
            os.remove(arquivo)
    except:
        pass

    try:
        communicate = edge_tts.Communicate(texto, config.voz_atual)
        await communicate.save(arquivo)
    except:
        return

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, reproduzir_sync, arquivo)







def captura_sync():

    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))

    with audio_io_lock:
        suspender_pygame_mixer_para_capture()

    print("\nEscutando...\n")

    try:
        kwargs = {}
        if idx is not None:
            kwargs["device_index"] = idx

        with mic_lock:
            with sr.Microphone(**kwargs) as source:

                reconhecedor.adjust_for_ambient_noise(source, duration=0.3)

                try:
                    audio = reconhecedor.listen(source, timeout=8, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    return ""

        texto = reconhecedor.recognize_google(audio, language="pt-BR").lower().strip()

        print(f"ouvido: {texto}")

        return texto

    except Exception as e:
        print(f"Erro na captura: {e}")
        return ""







def run_mic_loop():
    while True:
        try:
            mic_cmd.get()
            resultado = captura_sync()
            mic_rpy.put(resultado)
        except:
            time.sleep(1)







def ensure_mic_thread():
    global mic_thread

    if mic_thread and mic_thread.is_alive():
        return

    mic_thread = threading.Thread(target=run_mic_loop, daemon=True)
    mic_thread.start()







def ouvir_sync_queued():
    ensure_mic_thread()

    mic_cmd.put(True)

    try:
        return mic_rpy.get(timeout=40)
    except:
        return ""







async def ouvir_comando():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ouvir_sync_queued)