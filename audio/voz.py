from __future__ import annotations

import abc
import asyncio
import os
import re
import tempfile
import threading
import time
import uuid
from typing import Optional, List, Callable

import pygame
import speech_recognition as sr

class STTProvider(abc.ABC):
    @abc.abstractmethod
    def recognize(self, audio: sr.AudioData) -> str:
        pass

class TTSProvider(abc.ABC):
    @abc.abstractmethod
    async def generate(self, text: str, output_path: str) -> bool:
        pass

def limpar_texto(text: str) -> str:
    t = (text or "").strip().lower()
    if not t:
        return ""
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()

class DeepgramSTT(STTProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def recognize(self, audio: sr.AudioData) -> str:
        if not self.api_key:
            return ""
        try:
            import requests
            wav = audio.get_wav_data(convert_rate=16000, convert_width=2)
            resp = requests.post(
                "https://api.deepgram.com/v1/listen",
                params={"model": "nova-3", "language": "pt", "smart_format": "true"},
                headers={"Authorization": f"Token {self.api_key}", "Content-Type": "audio/wav"},
                data=wav,
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            return limpar_texto(
                data.get("results", {})
                    .get("channels", [{}])[0]
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
            )
        except Exception:
            return ""

class GoogleSTT(STTProvider):
    def __init__(self, recognizer: sr.Recognizer):
        self.recognizer = recognizer

    def recognize(self, audio: sr.AudioData) -> str:
        try:
            texto = self.recognizer.recognize_google(audio, language="pt-BR")
            return limpar_texto(texto)
        except Exception:
            return ""

class WhisperLocalSTT(STTProvider):
    def __init__(self, model_size: str = "small"):
        self._model = None
        self.model_size = model_size
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            return self._model

    def recognize(self, audio: sr.AudioData) -> str:
        model = self._get_model()
        wav = audio.get_wav_data(convert_rate=16000, convert_width=2)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(wav)
                tmp_path = f.name
            segments, _ = model.transcribe(tmp_path, language="pt", vad_filter=True, beam_size=5)
            return limpar_texto(" ".join((s.text or "").strip() for s in segments))
        except Exception:
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

class LocalCloneTTS(TTSProvider):
    def __init__(self, reference_audio_path: str, language: str = "pt"):
        self.reference_audio = reference_audio_path
        self.language = language
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from TTS.api import TTS
                self._model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
            return self._model

    async def generate(self, text: str, output_path: str) -> bool:
        if not os.path.exists(self.reference_audio):
            return False
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._generate_sync, text, output_path)
            return True
        except Exception:
            return False

    def _generate_sync(self, text: str, output_path: str):
        model = self._get_model()
        model.tts_to_file(
            text=text,
            speaker_wav=self.reference_audio,
            language=self.language,
            file_path=output_path
        )

class EdgeTTS(TTSProvider):
    def __init__(self, voice: str = "pt-BR-AntonioNeural"):
        self.voice = voice

    async def generate(self, text: str, output_path: str) -> bool:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
            return True
        except Exception:
            return False

def _device_index_seguro(valor) -> Optional[int]:
    if valor is None:
        return None
    try:
        v = int(valor)
        return v if v >= 0 else None
    except (ValueError, TypeError):
        return None

class AudioManager:
    def __init__(self, device_index=None, ui_callback: Optional[Callable[[bool], None]] = None):
        self.device_index = _device_index_seguro(device_index)
        self.ui_callback = ui_callback
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.55
        self.recognizer.non_speaking_duration = 0.25
        self.is_speaking = False
        self.is_interrupted = False
        self._audio_lock = threading.RLock()
        self._barge_stop_event = threading.Event()
        self._barge_thread = None

    def _kwargs_mic(self) -> dict:
        if self.device_index is not None:
            return {"device_index": self.device_index}
        return {}

    def notify_ui(self, status: bool):
        if self.ui_callback:
            try:
                self.ui_callback(status)
            except Exception:
                pass

    def capture_audio(self, timeout=10, phrase_time_limit=9) -> Optional[sr.AudioData]:
        with self._audio_lock:
            self._suspend_playback_for_capture()
        try:
            with sr.Microphone(**self._kwargs_mic()) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                return self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return None
        except Exception:
            return None

    def play_audio_sync(self, file_path: str):
        with self._audio_lock:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
            except Exception:
                return
            self.is_speaking = True
            self.is_interrupted = False
            self.notify_ui(True)
            self.start_barge_in()
            while pygame.mixer.music.get_busy():
                if self.is_interrupted:
                    break
                time.sleep(0.1)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        self.stop_barge_in()
        self.is_speaking = False
        self.notify_ui(False)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

    def interrupt(self):
        self.is_interrupted = True
        self.notify_ui(False)
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def _suspend_playback_for_capture(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                pygame.mixer.quit()
        except Exception:
            pass

    def start_barge_in(self):
        self._barge_stop_event.clear()
        self._barge_thread = threading.Thread(target=self.barge_in_loop, daemon=True)
        self._barge_thread.start()

    def stop_barge_in(self):
        self._barge_stop_event.set()

    def barge_in_loop(self):
        while not self._barge_stop_event.is_set():
            if not self.is_speaking or self.is_interrupted:
                break
            try:
                with sr.Microphone(**self._kwargs_mic()) as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.15)
                    audio = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=1.5)
                txt = limpar_texto(self.recognizer.recognize_google(audio, language="pt-BR"))
                if txt:
                    self.interrupt()
                    break
            except Exception:
                pass
            time.sleep(0.1)

def listar_microfones() -> list[dict]:
    try:
        return [{"index": i, "nome": name} for i, name in enumerate(sr.Microphone.list_microphone_names())]
    except Exception:
        return []

class VoiceSystem:
    def __init__(self, audio_manager: AudioManager, stt_cascade: List[STTProvider], tts_cascade: List[TTSProvider]):
        self.audio = audio_manager
        self.stt_cascade = stt_cascade
        self.tts_cascade = tts_cascade

    def listen(self) -> str:
        audio_data = self.audio.capture_audio()
        if not audio_data:
            return ""
        for provider in self.stt_cascade:
            text = provider.recognize(audio_data)
            if text:
                return text
        return ""

    async def speak(self, text: str):
        if not text.strip():
            return
        file_path = os.path.join(tempfile.gettempdir(), f"voice_{uuid.uuid4().hex}.mp3")
        for provider in self.tts_cascade:
            if await provider.generate(text, file_path):
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.audio.play_audio_sync, file_path)
                return

def _criar_voice_system(ui_callback=None) -> VoiceSystem:
    import config as cfg

    device_index = _device_index_seguro(getattr(cfg, "DEVICE_INDEX", None))
    audio_manager = AudioManager(device_index=device_index, ui_callback=ui_callback)

    stt_providers = [
        DeepgramSTT(api_key=getattr(cfg, "DEEPGRAM_API_KEY", "")),
        GoogleSTT(recognizer=audio_manager.recognizer),
        WhisperLocalSTT(model_size=getattr(cfg, "WHISPER_MODEL", "small")),
    ]

    tts_providers = [
        LocalCloneTTS(reference_audio_path=getattr(cfg, "voz_referencia", "assets/voz_clone.wav")),
        EdgeTTS(voice=getattr(cfg, "voz_atual", "pt-BR-AntonioNeural")),
    ]

    return VoiceSystem(audio_manager, stt_providers, tts_providers)

_voice_system: Optional[VoiceSystem] = None

def _get_voice_system() -> VoiceSystem:
    global _voice_system
    if _voice_system is None:
        from config import notificar_voz_painel
        _voice_system = _criar_voice_system(ui_callback=lambda on: notificar_voz_painel(on))
    return _voice_system

async def falar(texto: str) -> None:
    await _get_voice_system().speak(texto)

def interromper_voz() -> None:
    _get_voice_system().audio.interrupt()

def escutar() -> str:
    return _get_voice_system().listen()

async def ouvir_comando() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_voice_system().listen)