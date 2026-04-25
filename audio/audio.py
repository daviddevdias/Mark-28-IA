from __future__ import annotations

import asyncio
import os
import queue
import tempfile
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

_tts_queue: asyncio.Queue = asyncio.Queue()
_tts_worker_started = False


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
_barge_stop_event = threading.Event()
_barge_thread: threading.Thread | None = None


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


def barge_loop() -> None:
    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))
    rec = sr.Recognizer()
    rec.pause_threshold = 0.2
    rec.non_speaking_duration = 0.1
    rec.dynamic_energy_threshold = True
    rec.energy_threshold = 220
    while not _barge_stop_event.is_set():
        if not falando or interrompido:
            break
        try:
            kwargs: dict = {}
            if idx is not None:
                kwargs["device_index"] = idx
            with sr.Microphone(**kwargs) as source:
                try:
                    rec.adjust_for_ambient_noise(source, duration=0.08)
                except Exception:
                    pass
                try:
                    audio = rec.listen(source, timeout=0.35, phrase_time_limit=1.0)
                except sr.WaitTimeoutError:
                    continue
                try:
                    txt = rec.recognize_google(audio, language="pt-BR").strip().lower()
                except Exception:
                    txt = ""
                if txt:
                    print(f"ouvido durante fala: {txt!r}")
                    interromper_voz()
                    break
        except Exception:
            time.sleep(0.08)


def iniciar_listener_interrupcao() -> None:
    global _barge_thread
    _barge_stop_event.clear()
    if _barge_thread is not None and _barge_thread.is_alive():
        return
    _barge_thread = threading.Thread(target=barge_loop, daemon=True, name="JarvisBargeIn")
    _barge_thread.start()


def parar_listener_interrupcao() -> None:
    _barge_stop_event.set()


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
            iniciar_listener_interrupcao()
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
            parar_listener_interrupcao()
            globals()["falando"] = False
            ui_falar(False)
            try:
                os.unlink(arquivo)
            except Exception:
                pass


async def _tts_worker() -> None:
    while True:
        texto = await _tts_queue.get()
        try:
            await _falar_impl(texto)
        except Exception as e:
            print(f"[TTS] Erro no worker: {e}")
        finally:
            _tts_queue.task_done()


def _garantir_worker(loop: asyncio.AbstractEventLoop) -> None:
    global _tts_worker_started
    if not _tts_worker_started:
        _tts_worker_started = True
        loop.create_task(_tts_worker())


async def falar(texto: str) -> None:
    if not texto or not texto.strip():
        return
    loop = asyncio.get_running_loop()
    _garantir_worker(loop)
    await _tts_queue.put(texto.strip())


async def _falar_impl(texto: str) -> None:
    print(f"Jarvis: {texto}")

    with audio_io_lock:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    arquivo = tmp.name
    tmp.close()

    try:
        await edge_tts.Communicate(texto, config.voz_atual).save(arquivo)
    except Exception as e:
        print(f"[TTS] Erro edge_tts: {e}")
        try:
            os.unlink(arquivo)
        except Exception:
            pass
        return

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, reproduzir_sync, arquivo)


def _reconhecer_offline(audio) -> str:
    try:
        import vosk
        import json as _json
        model_path = getattr(config, "VOSK_MODEL_PATH", "vosk-model-small-pt")
        if not os.path.exists(model_path):
            return ""
        model = vosk.Model(model_path)
        rec = vosk.KaldiRecognizer(model, 16000)
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        rec.AcceptWaveform(raw)
        result = _json.loads(rec.Result())
        return result.get("text", "").strip()
    except Exception:
        pass
    try:
        import faster_whisper
        model = faster_whisper.WhisperModel("small", device="cpu", compute_type="int8")
        raw = audio.get_wav_data()
        import io
        segments, _ = model.transcribe(io.BytesIO(raw), language="pt")
        return " ".join(s.text for s in segments).strip()
    except Exception:
        return ""


def captura_sync() -> str:
    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))
    with audio_io_lock:
        suspender_pygame_mixer_para_capture()
        time.sleep(0.08)
        print("\n\n\nEscutando...\n\n\n")
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
                try:
                    texto = reconhecedor.recognize_google(audio, language="pt-BR")
                    tx = texto.lower().strip()
                    if tx:
                        print(f"ouvido: {tx!r}")
                    return tx
                except sr.UnknownValueError:
                    return ""
                except sr.RequestError:
                    print("[STT] Google offline, tentando fallback local...")
                    tx = _reconhecer_offline(audio).lower().strip()
                    if tx:
                        print(f"ouvido (offline): {tx!r}")
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