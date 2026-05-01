import os
import asyncio
import hashlib
import io
import queue
import threading
import time
import audioop
import wave
import numpy as np
import pygame
import speech_recognition as sr
import config

audio_io_lock = threading.RLock()
mic_lock       = threading.Lock()

mic_cmd: queue.Queue = queue.Queue()
mic_rpy: queue.Queue = queue.Queue()
mic_thread: threading.Thread | None = None

sleep_event      = threading.Event()
falando          = False
interrompido     = False
barge_stop_event = threading.Event()
barge_thread: threading.Thread | None = None

reconhecedor = sr.Recognizer()
reconhecedor.pause_threshold                   = 1.4
reconhecedor.non_speaking_duration             = 0.5
reconhecedor.energy_threshold                  = 300
reconhecedor.dynamic_energy_threshold          = True
reconhecedor.dynamic_energy_adjustment_damping = 0.15
reconhecedor.dynamic_energy_ratio              = 1.5

ENERGY_MIN      = 150
ENERGY_MAX      = 3500
FRASE_MAX       = 20
TIMEOUT_ESCUTA  = 8
TENTATIVAS      = 3
VAD_CHUNK_S     = 0.05
VAD_ONSET_COUNT = 4
VAD_ENERGY_MULT = 1.8

CACHE_MAX       = 64
SAMPLE_RATE     = 24000

arquivo_slot = 0
arquivo_lock = threading.Lock()

tts_engine    = None
tts_device    = "cpu"
tts_lock      = threading.Lock()
tts_pronto    = threading.Event()
frase_cache: dict[str, bytes] = {}
cache_ordem:  list[str]       = []


def detectar_device():
    try:
        import torch
        import torch_directml
        dev = torch_directml.device()
        print("[TTS] DirectML (AMD GPU) ativado.")
        return dev
    except Exception:
        pass
    try:
        import torch
        if torch.cuda.is_available():
            print("[TTS] CUDA ativado.")
            return "cuda"
    except Exception:
        pass
    print("[TTS] Usando CPU.")
    return "cpu"


def prewarm_tts():
    global tts_engine, tts_device
    try:
        tts_device = detectar_device()
        from TTS.api import TTS
        engine = TTS(
            model_name="tts_models/multilingual/multi-dataset/xtts_v2",
            progress_bar=False,
            gpu=(tts_device != "cpu"),
        )
        if hasattr(engine, "synthesizer") and hasattr(engine.synthesizer, "tts_model"):
            engine.synthesizer.tts_model.to(tts_device)
        tts_engine = engine
        voz = getattr(config, "voz_cone", None)
        if voz and os.path.exists(voz):
            print("[TTS] Pré-aquecendo modelo com voz_cone...")
            pcm = sintetizar_xtts_raw("Olá.", voz)
            if pcm:
                guardar_cache("Olá.", pcm)
        print("[TTS] XTTS v2 pronto.")
    except Exception as exc:
        print(f"[TTS] Falha ao carregar XTTS v2: {exc}")
        tts_engine = None
    finally:
        tts_pronto.set()


threading.Thread(target=prewarm_tts, daemon=True, name="TTS-Prewarm").start()


def guardar_cache(texto: str, pcm: bytes):
    chave = hashlib.md5(texto.encode()).hexdigest()
    frase_cache[chave] = pcm
    cache_ordem.append(chave)
    if len(cache_ordem) > CACHE_MAX:
        antiga = cache_ordem.pop(0)
        frase_cache.pop(antiga, None)


def buscar_cache(texto: str) -> bytes | None:
    return frase_cache.get(hashlib.md5(texto.encode()).hexdigest())


def sintetizar_xtts_raw(texto: str, voz: str) -> bytes | None:
    try:
        chunks = []
        for chunk in tts_engine.tts_stream(
            text=texto,
            speaker_wav=voz,
            language="pt",
            stream_chunk_size=20,
        ):
            if chunk is not None:
                arr = np.array(chunk, dtype=np.float32)
                pcm = (arr * 32767).astype(np.int16).tobytes()
                chunks.append(pcm)
        return b"".join(chunks) if chunks else None
    except Exception as exc:
        print(f"[TTS] XTTS erro síntese: {exc}")
        return None


def pcm_para_wav(pcm: bytes, rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def proximo_arquivo() -> str:
    global arquivo_slot
    with arquivo_lock:
        arquivo_slot = (arquivo_slot + 1) % 3
        return os.path.join(config.ASSETS_DIR, f"output_{arquivo_slot}.wav")


def remover_arquivo(caminho: str, tentativas: int = 6):
    for _ in range(tentativas):
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
            return
        except PermissionError:
            time.sleep(0.12)
        except Exception:
            return


def liberar_pygame():
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass


def suspender_pygame_para_capture():
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.quit()
    except Exception:
        pass


def normalizar_indice_microfone(idx):
    try:
        return int(idx) if idx is not None and int(idx) >= 0 else None
    except Exception:
        return None


def ui_falar(on, vol=1.0):
    try:
        config.notificar_voz_painel(on, vol)
    except Exception:
        pass


def interromper_voz():
    global interrompido
    interrompido = True
    ui_falar(False)
    sleep_event.set()
    liberar_pygame()


def barge_loop():
    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))
    rec = sr.Recognizer()
    rec.energy_threshold         = 200
    rec.dynamic_energy_threshold = False

    HOLD_COUNT = 3
    acima      = 0

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
                        audio = rec.listen(source, timeout=VAD_CHUNK_S, phrase_time_limit=VAD_CHUNK_S)
                        rms   = audioop.rms(audio.get_raw_data(), 2)
                        acima = acima + 1 if rms > rec.energy_threshold else max(0, acima - 1)
                    except sr.WaitTimeoutError:
                        acima = max(0, acima - 1)
            if acima >= HOLD_COUNT:
                interromper_voz()
                break
        except Exception:
            pass
        time.sleep(0.02)


def iniciar_listener_interrupcao():
    global barge_thread
    barge_stop_event.clear()
    if barge_thread and barge_thread.is_alive():
        return
    barge_thread = threading.Thread(target=barge_loop, daemon=True)
    barge_thread.start()


def parar_listener_interrupcao():
    barge_stop_event.set()


def reproduzir_sync(arquivo: str):
    global falando, interrompido

    with audio_io_lock:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)

        pygame.mixer.music.load(arquivo)
        pygame.mixer.music.play()

        falando      = True
        interrompido = False
        sleep_event.clear()

        iniciar_listener_interrupcao()

        while pygame.mixer.music.get_busy():
            if interrompido:
                break
            sleep_event.wait(0.05)

        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

    parar_listener_interrupcao()
    falando = False
    ui_falar(False)


async def sintetizar_edge(texto: str, caminho: str) -> bool:
    try:
        import edge_tts
        voz = getattr(config, "voz_atual", "pt-BR-AntonioNeural")
        await edge_tts.Communicate(texto, voz).save(caminho)
        return os.path.exists(caminho) and os.path.getsize(caminho) > 0
    except Exception as exc:
        print(f"[TTS] edge_tts erro: {exc}")
        return False


async def falar(texto: str):
    if not texto.strip():
        return

    loop    = asyncio.get_running_loop()
    arquivo = proximo_arquivo()

    await loop.run_in_executor(None, liberar_pygame)
    await loop.run_in_executor(None, remover_arquivo, arquivo)

    voz      = getattr(config, "voz_cone", None)
    pcm_cache = buscar_cache(texto)

    if pcm_cache:
        wav_bytes = pcm_para_wav(pcm_cache)
        with open(arquivo, "wb") as f:
            f.write(wav_bytes)
        await loop.run_in_executor(None, reproduzir_sync, arquivo)
        return

    if tts_engine is not None and voz and os.path.exists(voz):
        pcm = await loop.run_in_executor(None, sintetizar_xtts_raw, texto, voz)
        if pcm:
            guardar_cache(texto, pcm)
            wav_bytes = pcm_para_wav(pcm)
            with open(arquivo, "wb") as f:
                f.write(wav_bytes)
            await loop.run_in_executor(None, reproduzir_sync, arquivo)
            return

    mp3 = arquivo.replace(".wav", ".mp3")
    await loop.run_in_executor(None, remover_arquivo, mp3)
    ok  = await sintetizar_edge(texto, mp3)
    if ok:
        await loop.run_in_executor(None, reproduzir_sync, mp3)
    else:
        print("[TTS] Falha em todos os motores.")


def calibrar_microfone(source):
    reconhecedor.adjust_for_ambient_noise(source, duration=0.6)
    reconhecedor.energy_threshold = max(ENERGY_MIN, min(ENERGY_MAX, reconhecedor.energy_threshold))


def vad_aguardar_voz(source, baseline_energy: float) -> bool:
    onset_energy = baseline_energy * VAD_ENERGY_MULT
    onset_hits   = 0
    deadline     = time.time() + TIMEOUT_ESCUTA

    rec_vad = sr.Recognizer()
    rec_vad.energy_threshold         = onset_energy
    rec_vad.dynamic_energy_threshold = False

    while time.time() < deadline:
        try:
            chunk = rec_vad.listen(source, timeout=VAD_CHUNK_S, phrase_time_limit=VAD_CHUNK_S)
            rms   = audioop.rms(chunk.get_raw_data(), 2)
            if rms >= onset_energy:
                onset_hits += 1
                if onset_hits >= VAD_ONSET_COUNT:
                    return True
            else:
                onset_hits = max(0, onset_hits - 1)
        except sr.WaitTimeoutError:
            onset_hits = max(0, onset_hits - 1)
        except Exception:
            break
    return False


def captura_vad_sync() -> str:
    idx = normalizar_indice_microfone(getattr(config, "DEVICE_INDEX", None))

    with audio_io_lock:
        suspender_pygame_para_capture()

    kwargs = {}
    if idx is not None:
        kwargs["device_index"] = idx

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with mic_lock:
                with sr.Microphone(**kwargs) as source:
                    calibrar_microfone(source)
                    baseline = reconhecedor.energy_threshold

                    print("\nEscutando...\n")

                    if not vad_aguardar_voz(source, baseline):
                        return ""

                    reconhecedor.energy_threshold = baseline
                    audio = reconhecedor.listen(
                        source,
                        timeout=None,
                        phrase_time_limit=FRASE_MAX,
                    )

            texto = reconhecedor.recognize_google(audio, language="pt-BR", show_all=False)
            if isinstance(texto, str):
                texto = texto.lower().strip()
            else:
                texto = ""

            if texto:
                print(f"ouvido: {texto}")
                return texto

        except sr.UnknownValueError:
            pass
        except sr.RequestError as exc:
            print(f"[audio] API Google indisponível: {exc}")
            time.sleep(1.5 * tentativa)
        except Exception as exc:
            print(f"[audio] Erro inesperado (tentativa {tentativa}): {exc}")
            time.sleep(0.4)

    return ""


def run_mic_loop():
    while True:
        mic_cmd.get()
        resultado = captura_vad_sync()
        mic_rpy.put(resultado)


def ensure_mic_thread():
    global mic_thread
    if mic_thread and mic_thread.is_alive():
        return
    mic_thread = threading.Thread(target=run_mic_loop, daemon=True)
    mic_thread.start()


def ouvir_sync_queued() -> str:
    ensure_mic_thread()
    mic_cmd.put(True)
    try:
        return mic_rpy.get(timeout=90)
    except Exception:
        return ""


async def ouvir_comando() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ouvir_sync_queued)