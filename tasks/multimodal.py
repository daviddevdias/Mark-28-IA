import speech_recognition as sr
import asyncio


from audio.voz import limpar_texto_stt






def capturar_audio_sincrono(segundos: int) -> str:
    reconhecedor = sr.Recognizer()
    with sr.Microphone() as fonte:
        reconhecedor.adjust_for_ambient_noise(fonte, duration=1)
        try:
            audio = reconhecedor.record(fonte, duration=segundos)
            return limpar_texto_stt(reconhecedor.recognize_google(audio, language="pt-BR"))
        except Exception:
            return ""







async def traduzir_ambiente(segundos: int = 10) -> str:
    loop = asyncio.get_running_loop()
    texto_capturado = await loop.run_in_executor(None, capturar_audio_sincrono, segundos)
    if not texto_capturado:
        return "Não consegui captar nenhum áudio claro para traduzir."
    from engine.ia_router import router
    prompt = f"Você é um tradutor simultâneo. Corrija possíveis erros de transcrição e traduza o seguinte texto para o português do Brasil. Responda APENAS com a tradução, sem aspas e sem explicações: '{texto_capturado}'"
    resposta = await router.responder(prompt)
    return f"Tradução ambiental concluída: {resposta}"