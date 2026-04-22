import os
import asyncio
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
    "silêncio",
    "para de falar",
    "cala",
    "stop",
    "ei jarvis",
    "hey jarvis"
}

_falando = False
_interrompido = False
_fala_lock = asyncio.Lock()







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








def _ouvir_interrupcao_sync() -> None:

    idx = getattr(config, "DEVICE_INDEX", None)

    try:
        with sr.Microphone(device_index=idx) as source:
            audio = _reconhecedor.listen(source, timeout=0.5, phrase_time_limit=1)

            texto = _reconhecedor.recognize_google(audio, language="pt-BR")
            texto = texto.lower().strip()

            for word in _INTERRUPT_WORDS:
                if word in texto:
                    interromper_voz()
                    break

    except Exception:
        pass








async def _escutar_enquanto_fala() -> None:

    loop = asyncio.get_event_loop()

    try:
        while _falando and not _interrompido:
            await loop.run_in_executor(None, _ouvir_interrupcao_sync)
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        raise








def get_lock() -> asyncio.Lock:

    global _fala_lock
    return _fala_lock








async def falar(texto: str) -> None:

    global _falando, _interrompido

    async with get_lock():

        if not texto:
            return

        print(f"Jarvis: {texto}")

        arquivo = os.path.join(config.ASSETS_DIR, "output.mp3")

        try:
            os.makedirs(config.ASSETS_DIR, exist_ok=True)

            comm = edge_tts.Communicate(texto, config.voz_atual)
            await comm.save(arquivo)

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=256)

            pygame.mixer.music.load(arquivo)
            pygame.mixer.music.set_volume(1.0)

            _falando = True
            _interrompido = False

            pygame.mixer.music.play()

            escuta_task = asyncio.create_task(_escutar_enquanto_fala())

            while pygame.mixer.music.get_busy():
                if _interrompido:
                    break
                await asyncio.sleep(0.03)

            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

        finally:

            _falando = False

            if 'escuta_task' in locals():
                escuta_task.cancel()
                try:
                    await escuta_task
                except:
                    pass








async def ouvir_comando() -> str:

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _ouvir_sync)








def _ouvir_sync() -> str:

    idx = getattr(config, "DEVICE_INDEX", None)

    try:
        with sr.Microphone(device_index=idx) as source:

            print("\n[*] Escaneando...")

            audio = _reconhecedor.listen(source, timeout=5, phrase_time_limit=6)

            texto = _reconhecedor.recognize_google(audio, language="pt-BR")

            print(f"[VOCÊ]: {texto}")

            return texto.lower().strip()

    except Exception:
        return ""








def listar_microfones() -> list:

    return [
        f"{i}: {name}"
        for i, name in enumerate(sr.Microphone.list_microphone_names())
    ]