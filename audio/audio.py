import os
import asyncio
import threading
import pygame
import speech_recognition as sr
import edge_tts
import config











reconhecedor = sr.Recognizer()
reconhecedor.pause_threshold        = 0.4
reconhecedor.non_speaking_duration  = 0.2
reconhecedor.energy_threshold       = 250
reconhecedor.dynamic_energy_threshold = False

mic_lock    = threading.Lock()
sleep_event = threading.Event()
falando     = False
interrompido = False







def esta_falando() -> bool:
    return falando







def interromper_voz() -> None:
    global interrompido
    interrompido = True
    sleep_event.set()
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass







def reproduzir_sync(arquivo: str) -> None:
    global falando, interrompido
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.music.load(arquivo)
        pygame.mixer.music.set_volume(1.0)
        falando      = True
        interrompido = False
        sleep_event.clear()
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if interrompido:
                break
            sleep_event.wait(timeout=0.05)
            sleep_event.clear()
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
    finally:
        globals()["falando"] = False







async def falar(texto: str) -> None:
    if not texto or not texto.strip():
        return

    print(f"Jarvis: {texto}")
    arquivo = os.path.join(config.ASSETS_DIR, "output.mp3")

    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

    for i in range(3):
        try:
            if os.path.exists(arquivo):
                os.remove(arquivo)
            break
        except PermissionError:
            await asyncio.sleep(0.2)

    try:
        os.makedirs(config.ASSETS_DIR, exist_ok=True)
        await edge_tts.Communicate(texto, config.voz_atual).save(arquivo)
    except Exception as e:
        print(f"[TTS] Erro: {e}")
        return

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, reproduzir_sync, arquivo)







def ouvir_sync() -> str:
    idx = getattr(config, "DEVICE_INDEX", None)
    with mic_lock:
        try:
            with sr.Microphone(device_index=idx) as source:
                print("\n[*] Escaneando...")
                audio = reconhecedor.listen(source, timeout=5, phrase_time_limit=6)
                texto = reconhecedor.recognize_google(audio, language="pt-BR")
                print(f"[VOCÊ]: {texto}")
                return texto.lower().strip()
        except Exception:
            return ""







async def ouvir_comando() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ouvir_sync)







def listar_microfones() -> list:
    return [f"{i}: {n}" for i, n in enumerate(sr.Microphone.list_microphone_names())]