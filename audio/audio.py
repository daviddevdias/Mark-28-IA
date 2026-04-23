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

_INTERRUPT_WORDS = {
    "para",
    "chega",
    "silencio",
    "silêncio",
    "para de falar",
    "cala",
    "stop",
    "ei jarvis",
    "hey jarvis",
}

_falando = False
_interrompido = False
_mic_lock = threading.Lock()
_fala_thread_lock = threading.Lock()


def esta_falando() -> bool:
    return _falando


def interromper_voz() -> None:
    global _interrompido
    _interrompido = True
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
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if _interrompido:
                break
            threading.Event().wait(0.03)

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