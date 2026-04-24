import asyncio
import json
import time
from typing import Optional, Any

from audio.audio import falar
from storage.memory_manager import load_memory, get_nome, process_memory_logic
from engine.ia_router import (
    router,
    ligar_monitor as iniciar_hardware_monitor,
    desligar_monitor as parar_hardware_monitor,
    info_monitor as obter_status_hardware,
    _detectar_modelo,
)
from engine.controller import processar_diretriz

AGUARDANDO_CONFIRMACAO = False
ULTIMA_ANALISE_OBJ = None
ULTIMA_SUGESTAO = 0.0

_ui_bridge = None

ALERTAS_POR_TIPO = {
    "erro":        "Senhor, detectei um erro na tela.",
    "crash":       "Senhor, houve um crash no sistema.",
    "travado":     "Senhor, algo parece travado na tela.",
    "aviso":       "Senhor, há um aviso importante na tela.",
    "instalacao":  "Senhor, há uma instalação em andamento.",
    "compilacao":  "Senhor, processo de compilação detectado.",
    "terminal":    "Senhor, atividade no terminal identificada.",
    "codigo":      "Senhor, código com possível problema detectado.",
}


def registrar_ui_bridge(bridge) -> None:
    global _ui_bridge
    _ui_bridge = bridge


def _emitir_para_ui(dados: dict) -> None:
    if _ui_bridge is None:
        return
    try:
        _ui_bridge.dados_para_ui.emit(json.dumps(dados))
    except Exception:
        pass


def contexto() -> str:
    nome = get_nome()
    memoria = load_memory()
    ctx = f"Mestre: {nome} (Dev ADS)."
    if isinstance(memoria, dict) and "preferences" in memoria:
        ctx += f" Pref: {memoria['preferences']}."
    return ctx


async def inicializar_ia() -> None:
    await _detectar_modelo()


async def analisar_tela_agora() -> None:
    await falar("Iniciando varredura óptica, senhor.")

    from vision.capture import capturar_frame_base64, gerar_dica_profunda, _parse_resultado, _chamar_qwen, _SYSTEM_VISAO_RAPIDA

    loop = asyncio.get_running_loop()
    img_b64 = await loop.run_in_executor(None, capturar_frame_base64)

    if not img_b64:
        await falar("Falha na captura de tela, senhor.")
        return

    raw = await _chamar_qwen(
        _SYSTEM_VISAO_RAPIDA,
        "Analise esta tela detalhadamente. Há erros, avisos ou situações relevantes?",
        img_b64,
        max_tokens=150,
    )

    resultado = _parse_resultado(raw, img_b64)

    _emitir_para_ui({
        "visao_img": img_b64,
        "visao_status": "Análise concluída.",
        "visao_resultado": resultado.resumo,
        "monitor_evento": {
            "ok": resultado.ok,
            "tipo": resultado.tipo,
            "resumo": resultado.resumo,
            "problema": resultado.problema,
            "sugestao_rapida": resultado.sugestao_rapida,
            "timestamp": time.time(),
        }
    })

    if not resultado.ok:
        dica = await gerar_dica_profunda(img_b64, resultado.problema, resultado.tipo)
        resultado.dica_profunda = dica

        _emitir_para_ui({
            "monitor_dica": dica,
            "monitor_tipo": resultado.tipo,
        })

        print(f"\n[Jarvis - VISAO]: {resultado.resumo}")
        print(f"[Jarvis - DICA]: {dica}\n")
        await falar(f"{resultado.resumo}. {resultado.sugestao_rapida}")
    else:
        print(f"\n[Jarvis - VISAO]: {resultado.resumo}\n")
        await falar(resultado.resumo)


async def ligar_monitoramento(comando: str) -> None:
    from vision.capture import MonitorConfig, parar_monitor, _monitor_state

    # FIX: Garante que monitor anterior foi encerrado antes de religar
    if _monitor_state.rodando:
        parar_monitor()
        await asyncio.sleep(0.5)

    intervalo = 8.0
    for token in comando.split():
        if token.isdigit():
            intervalo = max(5.0, float(token))
            break

    cfg = MonitorConfig(
        intervalo_s=intervalo,
        apenas_mudancas=True,
        gerar_dica_automatica=True,
        cooldown_alerta_s=45.0,
        callback=loop_monitoramento_automatico,
    )

    from vision.capture import iniciar_monitor
    loop = asyncio.get_running_loop()
    await iniciar_monitor(cfg)

    _emitir_para_ui({
        "monitor_status": "ativo",
        "monitor_intervalo": int(intervalo),
    })

    await falar(f"Monitoramento ativo, senhor. Intervalo de {int(intervalo)} segundos.")


async def desligar_monitoramento() -> None:
    global AGUARDANDO_CONFIRMACAO
    AGUARDANDO_CONFIRMACAO = False  # FIX: reseta flag ao desligar

    stats = parar_hardware_monitor()

    _emitir_para_ui({
        "monitor_status": "inativo",
        "monitor_stats": stats,
    })

    economizados = stats.get("economizados", 0)
    problemas    = stats.get("total_problemas", 0)

    await falar(
        f"Monitoramento suspenso, senhor. "
        f"{problemas} problema(s) detectado(s) na sessão."
    )

    print(
        f"[SISTEMA] Monitor desligado — "
        f"frames economizados: {economizados} | "
        f"problemas: {problemas}"
    )


async def status_do_sistema() -> None:
    s = obter_status_hardware()
    if s["rodando"]:
        msg = (
            f"Sistema operacional, senhor. "
            f"Monitor ativo com {s['chamadas_api']} consultas realizadas "
            f"e {s.get('total_problemas', 0)} problema(s) detectado(s)."
        )
    else:
        msg = "Sistema em repouso. Monitoramento desligado."
    await falar(msg)


async def processar_comando(comando: str, imagem_monitor: Optional[Any] = None) -> bool:
    global AGUARDANDO_CONFIRMACAO, ULTIMA_ANALISE_OBJ

    if not comando.strip() and not imagem_monitor:
        return False

    if AGUARDANDO_CONFIRMACAO:
        cmd_lower = comando.lower()

        if any(p in cmd_lower for p in ("sim", "pode", "analisa", "continua", "vai")):
            AGUARDANDO_CONFIRMACAO = False

            obj = ULTIMA_ANALISE_OBJ
            if obj is not None and obj.img_b64:
                from vision.capture import gerar_dica_profunda
                dica = await gerar_dica_profunda(obj.img_b64, obj.problema, obj.tipo)
            else:
                dica = await router.responder(
                    f"Sugira solução técnica para: {obj.problema if obj else 'problema na tela'}",
                    memoria=contexto(),
                )

            _emitir_para_ui({
                "monitor_dica": dica,
                "monitor_tipo": obj.tipo if obj else "erro",
            })

            print(f"\n[Jarvis - SOLUÇÃO]: {dica}\n")
            await falar(dica)
            return True

        if any(p in cmd_lower for p in ("nao", "não", "ignora", "ok", "beleza")):
            AGUARDANDO_CONFIRMACAO = False
            await falar("Entendido, senhor. Monitoramento continua.")
            return True

        # FIX: se aguardando confirmação, qualquer outro comando ainda processa normalmente
        # mas notifica que há uma confirmação pendente
        await falar("Senhor, ainda aguardo sua confirmação sobre o problema detectado. Diga 'sim' ou 'não'.")
        return True

    resultado_local = await processar_diretriz(comando)

    if resultado_local is not None:
        if resultado_local:
            print(f"\n[Jarvis - LOCAL]: {resultado_local}\n")
            await falar(resultado_local)
        return True

    resposta = await router.responder(
        pergunta=comando,
        nome=get_nome(),
        memoria=contexto(),
        imagem=imagem_monitor,
    )

    if resposta:
        print(f"\n[Jarvis - IA]: {resposta}\n")
        await falar(resposta)
        asyncio.create_task(process_memory_logic(comando, resposta))

    return True


async def loop_monitoramento_automatico(resultado) -> None:
    global AGUARDANDO_CONFIRMACAO, ULTIMA_ANALISE_OBJ, ULTIMA_SUGESTAO

    from vision.capture import ResultadoAnalise

    if not isinstance(resultado, ResultadoAnalise):
        return

    # FIX: se aguardando confirmação, NÃO emite novos alertas — pausa completa
    if AGUARDANDO_CONFIRMACAO:
        return

    agora = time.time()

    # Sempre emite o evento para o painel (inclusive OK)
    _emitir_para_ui({
        "monitor_evento": {
            "ok":             resultado.ok,
            "tipo":           resultado.tipo,
            "resumo":         resultado.resumo,
            "problema":       resultado.problema,
            "sugestao_rapida": resultado.sugestao_rapida,
            "timestamp":      agora,
        }
    })

    if resultado.ok:
        # Emite status OK também para o painel ver
        _emitir_para_ui({"monitor_ultimo_ok": resultado.resumo})
        return

    if (agora - ULTIMA_SUGESTAO) < 45.0:
        return

    ULTIMA_ANALISE_OBJ   = resultado
    AGUARDANDO_CONFIRMACAO = True
    ULTIMA_SUGESTAO      = agora

    alerta = ALERTAS_POR_TIPO.get(resultado.tipo, "Senhor, detectei algo incomum na tela.")

    if resultado.dica_profunda:
        _emitir_para_ui({
            "monitor_dica":  resultado.dica_profunda,
            "monitor_tipo":  resultado.tipo,
            "monitor_alerta": alerta,
            "aguardando_confirmacao": True,
        })
        print(f"\n[Jarvis - MONITOR]: {alerta}")
        print(f"[Jarvis - DICA]: {resultado.dica_profunda}\n")
        await falar(f"{alerta} {resultado.sugestao_rapida}. Deseja a análise completa?")
    else:
        _emitir_para_ui({
            "monitor_alerta": alerta,
            "monitor_tipo":   resultado.tipo,
            "aguardando_confirmacao": True,
        })
        print(f"\n[Jarvis - MONITOR]: {alerta} — {resultado.problema}\n")
        await falar(f"{alerta} Deseja que eu analise uma solução?")