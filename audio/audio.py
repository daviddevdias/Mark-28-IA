import os
import asyncio
import threading
import pygame
import speech_recognition as sr
import edge_tts
import config

_reconhecedor = sr.Recognizer()
_reconhecedor.pause_threshold = 0.4
_reconhecedor.non_speaking_duration = 0.2
_reconhecedor.energy_threshold = 250
_reconhecedor.dynamic_energy_threshold = False

_falando = False
_interrompido = False
_mic_lock = threading.Lock()
_sleep_event = threading.Event()


def esta_falando() -> bool:
    return _falando


def interromper_voz() -> None:
    global _interrompido
    _interrompido = True
    _sleep_event.set()
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass


def _reproduzir_sync(arquivo: str) -> None:
    global _falando, _interrompido
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        pygame.mixer.music.load(arquivo)
        pygame.mixer.music.set_volume(1.0)

        _falando = True
        _interrompido = False
        _sleep_event.clear()
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if _interrompido:
                break
            _sleep_event.wait(timeout=0.05)
            _sleep_event.clear()

        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
    finally:
        _falando = False


async def falar(texto: str) -> None:
    if not texto or not texto.strip():
        return

    print(f"Jarvis: {texto}")

    arquivo = os.path.join(config.ASSETS_DIR, "output.mp3")

    # --- INÍCIO DA BLINDAGEM CONTRA O ERRO 13 ---
    # 1. Força o pygame a soltar qualquer arquivo que esteja preso na memória
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

    # 2. Tenta apagar o arquivo antigo. O loop garante que, se o SO demorar, ele tenta de novo.
    for _ in range(3):
        try:
            if os.path.exists(arquivo):
                os.remove(arquivo)
            break
        except PermissionError:
            await asyncio.sleep(0.2)
    # --- FIM DA BLINDAGEM ---

    try:
        os.makedirs(config.ASSETS_DIR, exist_ok=True)
        comm = edge_tts.Communicate(texto, config.voz_atual)
        await comm.save(arquivo)
    except Exception as e:
        print(f"[TTS] Erro ao gerar audio: {e}")
        return

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _reproduzir_sync, arquivo)


def _ouvir_sync() -> str:
    idx = getattr(config, "DEVICE_INDEX", None)

    with _mic_lock:
        try:
            with sr.Microphone(device_index=idx) as source:
                print("\n[*] Escaneando...")
                audio = _reconhecedor.listen(source, timeout=5, phrase_time_limit=6)
                texto = _reconhecedor.recognize_google(audio, language="pt-BR")
                print(f"[VOCÊ]: {texto}")
                return texto.lower().strip()
        except Exception:
            return ""


async def ouvir_comando() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _ouvir_sync)


def listar_microfones() -> list:
    return [
        f"{i}: {name}"
        for i, name in enumerate(sr.Microphone.list_microphone_names())
    ]