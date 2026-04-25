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

_mic_cmd: queue.Queue = queue.Queue()
_mic_rpy: queue.Queue = queue.Queue()
_mic_thread: threading.Thread | None = None


def suspender_pygame_mixer_para_capture() -> None:
    try:
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.quit()
    except Exception:
        pass


def normalizar_indice_microfone(idx) -> int | None:
    if idx is None:
        return None
    try:
        n = int(idx)
        if n < 0:
            return None
        return n
    except (TypeError, ValueError):
        return None


def ui_falar(on: bool, vol: float = 1.0) -> None:
    try:
        config.notificar_voz_painel(on, vol)
    except Exception:
        pass
    try:
        if on:
            from app_ul.interface import falar_on

            falar_on(vol)
        else:
            from app_ul.interface import falar_off

            falar_off()
    except Exception:
        pass


reconhecedor = sr.Recognizer()
reconhecedor.pause_threshold = 0.4
reconhecedor.non_speaking_duration = 0.2
reconhecedor.energy_threshold = 250
reconhecedor.dynamic_energy_threshold = False

sleep_event = threading.Event()
falando = False
interrompido = False


def esta_falando() -> bool:
    return falando


def interromper_voz() -> None:
    global interrompido
    interrompido = True
    ui_falar(False)
    sleep_event.set()
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass


def reproduzir_sync(arquivo: str) -> None:
    global falando, interrompido
    with audio_io_lock:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.music.load(arquivo)
            pygame.mixer.music.set_volume(1.0)
            falando = True
            ui_falar(True, 1.0)
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
            ui_falar(False)


_tts_lock = asyncio.Lock()


async def falar(texto: str) -> None:
    if not texto or not texto.strip():
        return
    async with _tts_lock:
        await falar_impl(texto.strip())


async def falar_impl(texto: str) -> None:
    print(f"Jarvis: {texto}")
    arquivo = os.path.join(config.ASSETS_DIR, "output.mp3")

    with audio_io_lock:
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


def captura_sync() -> str:
    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))
    with audio_io_lock:
        suspender_pygame_mixer_para_capture()
        time.sleep(0.08)
        try:
            kwargs: dict = {}
            if idx is not None:
                kwargs["device_index"] = idx
            with sr.Microphone(**kwargs) as source:
                try:
                    reconhecedor.adjust_for_ambient_noise(source, duration=0.2)
                except Exception:
                    pass
                audio = reconhecedor.listen(source, timeout=5, phrase_time_limit=6)
                texto = reconhecedor.recognize_google(audio, language="pt-BR")
                tx = texto.lower().strip()
                if tx:
                    print(f"ouvido: {tx!r}")
                return tx
        except Exception:
            return ""


def run_mic_loop() -> None:
    while True:
        token = _mic_cmd.get()
        if token is None:
            break
        try:
            out = captura_sync()
        except Exception:
            out = ""
        _mic_rpy.put(out)


def ensure_mic_thread() -> None:
    global _mic_thread
    if _mic_thread is not None and _mic_thread.is_alive():
        return
    _mic_thread = threading.Thread(target=run_mic_loop, daemon=True, name="JarvisMicLoop")
    _mic_thread.start()
    time.sleep(0.12)


def ouvir_sync_queued() -> str:
    ensure_mic_thread()
    try:
        while True:
            _mic_rpy.get_nowait()
    except queue.Empty:
        pass
    _mic_cmd.put(True)
    try:
        return _mic_rpy.get(timeout=42)
    except queue.Empty:
        print("[AUDIO] Timeout ao aguardar resultado do microfone.")
        return ""


async def ouvir_comando() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ouvir_sync_queued)


def listar_microfones() -> list:
    with audio_io_lock:
        try:
            suspender_pygame_mixer_para_capture()
            time.sleep(0.05)
            return [f"{i}: {n}" for i, n in enumerate(sr.Microphone.list_microphone_names())]
        except Exception:
            return []
