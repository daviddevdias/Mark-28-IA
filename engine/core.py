from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from audio.audio import falar
from storage.memory_manager import load_memory, get_nome, process_memory_logic
from engine.ia_router import router, detectar_modelo, desligar_monitor, info_monitor
from engine.controller import processar_diretriz
from tasks.alarm import alarme_ativo, parar_alarme_total

try:
    from logs.observability import registrar_acao, registrar_metrica, Temporizador as _Temporizador
    _OBS = True
except Exception:
    _OBS = False

ui_bridge = None
AGUARDANDO_CONFIRMACAO = False
ULTIMA_ANALISE_OBJ = None
ULTIMA_SUGESTAO = 0.0

ALERTAS = {
    "erro": "Detectei um erro na tela.",
    "crash": "Parece ter ocorrido um crash.",
    "travado": "Algo parece travado.",
    "aviso": "Há um aviso importante na tela.",
    "instalacao": "Instalação em andamento.",
    "compilacao": "Compilação em andamento.",
    "terminal": "Atividade no terminal.",
    "codigo": "Possível problema no código.",
}


def registrar_ui_bridge(bridge) -> None:
    global ui_bridge
    ui_bridge = bridge


def emitir(dados: dict) -> None:
    if ui_bridge is None:
        return
    try:
        ui_bridge.dados_para_ui.emit(json.dumps(dados))
    except Exception:
        pass


def contexto() -> str:
    nome = get_nome()
    mem = load_memory()
    try:
        from tasks.weather import get_cidade_painel

        cidade = get_cidade_painel()
    except Exception:
        cidade = ""
    ctx = f"Mestre: {nome}. Cidade padrão (clima): {cidade}."
    if isinstance(mem, dict) and "preferences" in mem:
        ctx += f" Pref: {mem['preferences']}."
    return ctx


async def inicializar_ia() -> None:
    await detectar_modelo()


async def analisar_tela_agora() -> None:
    await falar("Iniciando análise da tela.")

    from vision.capture import capturar_frame_base64, gerar_dica_profunda, parse, chamar_qwen, SYSTEM_RAPIDO

    img = await asyncio.get_running_loop().run_in_executor(None, capturar_frame_base64)
    if not img:
        await falar("Não consegui capturar a tela.")
        return

    raw = await chamar_qwen(SYSTEM_RAPIDO, "Analise esta tela. Há erros ou situações relevantes?", img, 150)
    resultado = parse(raw, img)

    emitir(
        {
            "visao_img": img,
            "visao_resultado": resultado.resumo,
            "monitor_evento": {
                "ok": resultado.ok,
                "tipo": resultado.tipo,
                "resumo": resultado.resumo,
                "problema": resultado.problema,
                "sugestao_rapida": resultado.sugestao_rapida,
                "timestamp": time.time(),
            },
        }
    )

    if not resultado.ok:
        dica = await gerar_dica_profunda(img, resultado.problema, resultado.tipo)
        resultado.dica_profunda = dica
        emitir({"monitor_dica": dica, "monitor_tipo": resultado.tipo})
        print(f"\n[VISAO]: {resultado.resumo}\n[DICA]: {dica}\n")
        await falar(f"{resultado.resumo}. {resultado.sugestao_rapida}")
    else:
        print(f"\n[VISAO]: {resultado.resumo}\n")
        await falar(resultado.resumo)


async def analisar_camera_agora() -> None:
    await falar("A capturar a camara.")

    from vision.capture import gerar_dica_profunda, parse, chamar_qwen, SYSTEM_RAPIDO
    from vision.webcam import capturar_webcam_base64

    img = await asyncio.get_running_loop().run_in_executor(None, capturar_webcam_base64, 0)
    if not img:
        await falar("Camara indisponivel. Instale opencv-python e ligue a webcam.")
        return

    raw = await chamar_qwen(
        SYSTEM_RAPIDO,
        "Analise esta imagem da camara: codigo no ecra, erros, ou o que ve.",
        img,
        180,
    )
    resultado = parse(raw, img)
    emitir(
        {
            "visao_img": img,
            "visao_resultado": resultado.resumo,
            "monitor_evento": {
                "ok": resultado.ok,
                "tipo": resultado.tipo,
                "resumo": resultado.resumo,
                "problema": resultado.problema,
                "sugestao_rapida": resultado.sugestao_rapida,
                "timestamp": time.time(),
            },
        }
    )
    if not resultado.ok:
        dica = await gerar_dica_profunda(img, resultado.problema, resultado.tipo)
        emitir({"monitor_dica": dica, "monitor_tipo": resultado.tipo})
        await falar(f"{resultado.resumo}. {resultado.sugestao_rapida}")
    else:
        await falar(resultado.resumo)


async def ligar_monitoramento(comando: str) -> None:
    from vision.capture import MonitorConfig, parar_monitor, estado

    if estado.rodando:
        parar_monitor()
        await asyncio.sleep(0.5)

    intervalo = max(5.0, float(next((t for t in comando.split() if t.isdigit()), "8")))

    from vision.capture import iniciar_monitor

    await iniciar_monitor(
        MonitorConfig(
            intervalo_s=intervalo,
            apenas_mudancas=True,
            gerar_dica_auto=True,
            cooldown_s=45.0,
            callback=loop_monitoramento,
        )
    )

    emitir({"monitor_status": "ativo", "monitor_intervalo": int(intervalo)})
    await falar(f"Monitoramento ativo. Intervalo de {int(intervalo)} segundos.")


async def desligar_monitoramento() -> None:
    global AGUARDANDO_CONFIRMACAO
    AGUARDANDO_CONFIRMACAO = False

    stats = desligar_monitor()
    emitir({"monitor_status": "inativo", "monitor_stats": stats})

    problemas = stats.get("total_problemas", 0)
    await falar(f"Monitoramento suspenso. {problemas} problema(s) registrados.")
    print(f"[SISTEMA] Monitor desligado — problemas: {problemas}")


async def status_do_sistema() -> None:
    s = info_monitor()
    if s["rodando"]:
        msg = (
            f"Operacional. {s['chamadas_api']} consultas, "
            f"{s.get('total_problemas', 0)} problema(s)."
        )
    else:
        msg = "Sistema em repouso."
    await falar(msg)


def quer_parar_alarme(cmd: str) -> bool:
    return any(p in cmd.lower() for p in ("parar", "desligar", "acordei", "chega", "ok"))


async def processar_comando(comando: str, imagem_monitor: Optional[Any] = None) -> str | None:
    global AGUARDANDO_CONFIRMACAO, ULTIMA_ANALISE_OBJ

    if not comando.strip() and not imagem_monitor:
        return None

    _ts_inicio = time.time()

    if alarme_ativo and quer_parar_alarme(comando):
        msg = parar_alarme_total()
        await falar(msg)
        return msg or None

    if AGUARDANDO_CONFIRMACAO:
        cmd = comando.lower()
        if any(p in cmd for p in ("analisar","resolver","ajuda jarvis" "continua",)):
            AGUARDANDO_CONFIRMACAO = False
            obj = ULTIMA_ANALISE_OBJ
            if obj and obj.img_b64:
                from vision.capture import gerar_dica_profunda

                dica = await gerar_dica_profunda(obj.img_b64, obj.problema, obj.tipo)
            else:
                dica = await router.responder(
                    f"Sugira solução para: {obj.problema if obj else 'problema na tela'}",
                    memoria=contexto(),
                )
            emitir({"monitor_dica": dica, "monitor_tipo": obj.tipo if obj else "erro"})
            print(f"\n[SOLUÇÃO]: {dica}\n")
            await falar(dica)
            return dica

        if any(p in cmd for p in ("não precisa", "não", "ignora","ignorar isso", "ok", "beleza")):
            AGUARDANDO_CONFIRMACAO = False
            msg = "Entendido. Monitoramento continua."
            await falar(msg)
            return msg

        msg = "Ainda aguardo confirmação. Diga sim ou não."
        await falar(msg)
        return msg

    resultado = await processar_diretriz(comando)
    if resultado is not None:
        if resultado:
            print(f"\n[LOCAL]: {resultado}\n")
            await falar(resultado)
            if _OBS:
                try:
                    _dur = int((time.time() - _ts_inicio) * 1000)
                    registrar_acao("comando_local", descricao=comando[:200],
                                   modulo="controller", duracao_ms=_dur, sucesso=True)
                    registrar_metrica("cmd.duracao_ms", _dur, "ms")
                except Exception:
                    pass
            return resultado
        return None

    resposta = await router.responder(
        pergunta=comando, nome=get_nome(), memoria=contexto(), imagem=imagem_monitor
    )
    if resposta:
        print(f"\n[IA]: {resposta}\n")
        await falar(resposta)
        asyncio.create_task(process_memory_logic(comando, resposta))
        if _OBS:
            try:
                _dur = int((time.time() - _ts_inicio) * 1000)
                registrar_acao("comando_ia", descricao=comando[:200],
                               modulo="ia_router", duracao_ms=_dur, sucesso=True)
                registrar_metrica("cmd.duracao_ms", _dur, "ms")
                registrar_metrica("ia.resposta_ms", _dur, "ms")
            except Exception:
                pass
    return resposta or None


async def loop_monitoramento(resultado) -> None:
    global AGUARDANDO_CONFIRMACAO, ULTIMA_ANALISE_OBJ, ULTIMA_SUGESTAO

    from vision.capture import ResultadoAnalise

    if not isinstance(resultado, ResultadoAnalise) or AGUARDANDO_CONFIRMACAO:
        return

    agora = time.time()
    emitir(
        {
            "monitor_evento": {
                "ok": resultado.ok,
                "tipo": resultado.tipo,
                "resumo": resultado.resumo,
                "problema": resultado.problema,
                "sugestao_rapida": resultado.sugestao_rapida,
                "timestamp": agora,
            }
        }
    )

    if resultado.ok:
        emitir({"monitor_ultimo_ok": resultado.resumo})
        return

    if (agora - ULTIMA_SUGESTAO) < 45.0:
        return

    ULTIMA_ANALISE_OBJ = resultado
    AGUARDANDO_CONFIRMACAO = True
    ULTIMA_SUGESTAO = agora

    alerta = ALERTAS.get(resultado.tipo, "Detectei algo incomum na tela.")

    if resultado.dica_profunda:
        emitir(
            {
                "monitor_dica": resultado.dica_profunda,
                "monitor_tipo": resultado.tipo,
                "monitor_alerta": alerta,
                "aguardando_confirmacao": True,
            }
        )
        print(f"\n[MONITOR]: {alerta}\n[DICA]: {resultado.dica_profunda}\n")
        await falar(f"{alerta} {resultado.sugestao_rapida}. Quer análise completa?")
    else:
        emitir(
            {
                "monitor_alerta": alerta,
                "monitor_tipo": resultado.tipo,
                "aguardando_confirmacao": True,
            }
        )
        print(f"\n[MONITOR]: {alerta} — {resultado.problema}\n")
        await falar(f"{alerta} Quer que eu analise?")