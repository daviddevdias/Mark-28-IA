import asyncio
import time
from typing import Optional, Any

from audio.audio import falar
from storage.memory_manager import load_memory, get_nome, process_memory_logic
from engine.ia_router import (
    router,
    ligar_monitor as iniciar_hardware_monitor,
    desligar_monitor as parar_hardware_monitor,
    info_monitor as obter_status_hardware
)

from engine.controller import processar_diretriz

VOZ_LOCK = asyncio.Lock()
AGUARDANDO_CONFIRMACAO = False
ULTIMA_ANALISE = ""
ULTIMA_SUGESTAO = 0

KEYWORDS_PROBLEMA = ["erro", "falha", "crash", "exception", "não responde", "travou", "problema"]






def contexto() -> str:
    nome = get_nome()
    memoria = load_memory()
    ctx = f"Mestre: {nome} (Dev ADS)."
    if isinstance(memoria, dict) and "preferences" in memoria:
        ctx += f" Pref: {memoria['preferences']}."
    return ctx






async def falar_seguro(texto: str):
    async with VOZ_LOCK:
        await falar(texto)






async def analisar_tela_agora():
    await falar_seguro("Iniciando varredura óptica manual.")
    resposta = await router.responder("Analise a tela agora e me dê um resumo técnico.", imagem="screenshot")
    if resposta:
        print(f"\n[Jarvis - VISÃO]: {resposta}\n")
        await falar_seguro(resposta)






async def ligar_monitoramento(comando: str):
    intervalo = 10.0
    for token in comando.split():
        if token.isdigit():
            intervalo = max(5.0, float(token))
            break
    
    iniciar_hardware_monitor(
        intervalo_s=intervalo, 
        callback=loop_monitoramento_automatico
    )
    await falar_seguro(f"Monitoramento ativo com intervalo de {int(intervalo)} segundos.")






async def desligar_monitoramento():
    stats = parar_hardware_monitor()
    await falar_seguro("Monitoramento suspenso para poupar recursos da API.")
    print(f"[SISTEMA]: Monitor desligado. Chamadas economizadas: {stats.get('frames_economizados', 0)}")






async def status_do_sistema():
    s = obter_status_hardware()
    if s["rodando"]:
        msg = f"Sistema operacional. Monitor ativo. {s['chamadas_api']} consultas realizadas."
    else:
        msg = "Sistema em repouso. Monitoramento automático desligado."
    await falar_seguro(msg)






async def processar_comando(comando: str, imagem_monitor: Optional[Any] = None) -> bool:
    global AGUARDANDO_CONFIRMACAO, ULTIMA_ANALISE

    if not comando.strip() and not imagem_monitor:
        return False

    if AGUARDANDO_CONFIRMACAO:
        if "sim" in comando.lower():
            AGUARDANDO_CONFIRMACAO = False
            pergunta = f"Sugira uma solução técnica para este problema que você viu na tela: {ULTIMA_ANALISE}"
            resposta = await router.responder(pergunta, memoria=contexto())
            await falar_seguro(resposta)
            return True
        if "não" in comando.lower():
            AGUARDANDO_CONFIRMACAO = False
            await falar_seguro("Entendido, monitoramento continua.")
            return True


    resultado_local = await processar_diretriz(comando)
    


    if resultado_local is not None:
        if resultado_local != "": 
            print(f"\n[Jarvis - LOCAL]: {resultado_local}\n")
            await falar_seguro(resultado_local)
        return True

    resposta = await router.responder(
        pergunta=comando,
        nome=get_nome(),
        memoria=contexto(),
        imagem=imagem_monitor
    )

    if resposta:
        print(f"\n[Jarvis - IA]: {resposta}\n")
        await falar_seguro(resposta)
        asyncio.create_task(process_memory_logic(comando, resposta))

    return True






async def loop_monitoramento_automatico(analise: str):
    global AGUARDANDO_CONFIRMACAO, ULTIMA_ANALISE, ULTIMA_SUGESTAO
    
    if AGUARDANDO_CONFIRMACAO:
        return

    texto = analise.lower()
    tem_problema = any(k in texto for k in KEYWORDS_PROBLEMA)
    agora = time.time()

    if tem_problema and (agora - ULTIMA_SUGESTAO > 30):
        ULTIMA_ANALISE = analise
        AGUARDANDO_CONFIRMACAO = True
        ULTIMA_SUGESTAO = agora
        await falar_seguro("Detectei uma anomalia na tela. Deseja que eu analise uma solução?")