from __future__ import annotations

import asyncio
import webbrowser
import subprocess
import os
import json
from typing import Any, Callable

from tasks.browser import jarvis_web, busca_web_sync
from tasks.spotify_manager import spotify_stark
from tasks.open_app import open_app
from tasks.weather import obter_previsao_hoje, verificar_chuva_amanha
from tasks.alarm import adicionar_alarme, listar_alarmes, remover_alarme
from tasks.computer_control import computer_settings
from storage.memory_manager import load_memory, update_memory
from engine.cmd_security import avaliar, executar, audit_recente
from brain.tool_cache import despachar as cache_despachar, stats_cache, invalidar_cache_tool

log = __import__("logging").getLogger("jarvis.tools_mapper")

def executar_no_loop_atual(coro) -> Any:
    """Executa uma corrotina a partir de contexto síncrono, sem deadlock.

    Estratégia:
    - Se NÃO há loop rodando (thread de worker / import-time): usa asyncio.run().
    - Se HÁ um loop rodando mas estamos em uma thread diferente (ex: executor do tool_cache):
      usa run_coroutine_threadsafe — seguro porque a thread atual NÃO está bloqueando o loop.
    - Nunca chama fut.result() a partir da própria thread do loop (causaria deadlock).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Nenhum loop ativo nesta thread — pode criar um novo com segurança
        return asyncio.run(coro)

    # Há um loop rodando. Verificamos se esta thread É a thread do loop.
    import threading
    loop_thread = getattr(loop, "_thread_id", None)
    current_thread = threading.get_ident()

    if loop_thread is not None and loop_thread == current_thread:
        # Estamos NA thread do loop — run_coroutine_threadsafe bloquearia com fut.result().
        # Lançamos exceção explícita: o chamador síncrono não deveria estar aqui;
        # deve ser refatorado para async ou chamado via executor.
        raise RuntimeError(
            "executar_no_loop_atual() chamado dentro da thread do loop de eventos. "
            "Refatore o gerenciador para async ou chame-o via run_in_executor()."
        )

    # Thread diferente da do loop — run_coroutine_threadsafe é seguro
    fut = asyncio.run_coroutine_threadsafe(coro, loop)
    return fut.result(timeout=30)

def gerenciador_web(argumentos: dict) -> str:
    pesquisa = argumentos.get("query", "").strip()
    if not pesquisa:
        return "Nenhum termo de pesquisa informado."
    resultado = busca_web_sync(pesquisa)
    if not resultado or resultado.startswith("Sem resultados"):
        resultado = jarvis_web.run(jarvis_web.smart_search(pesquisa))
    return resultado or "Sem resultados na web."

def gerenciador_browser(argumentos: dict) -> str:
    acao = argumentos.get("action", "open").lower()
    url = argumentos.get("url", "").strip()
    query = argumentos.get("query", "").strip()
    if acao == "open" and url:
        webbrowser.open(url)
        return f"Abrindo {url} no navegador."
    if acao in ("search", "open") and query:
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return f"Pesquisando '{query}' no Google."
    if url:
        webbrowser.open(url)
        return f"Abrindo {url}."
    if query:
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return f"Pesquisando '{query}'."
    return "Informe uma URL ou termo de pesquisa."

def gerenciador_youtube(argumentos: dict) -> str:
    pesquisa = argumentos.get("query", "").strip()
    if not pesquisa:
        return "Nenhum termo informado para YouTube."
    return jarvis_web.run(jarvis_web.tocar_youtube(pesquisa)) or "Nada encontrado no YouTube."

def gerenciador_spotify(argumentos: dict) -> str:
    acao = argumentos.get("action", "").lower()
    if argumentos.get("playlist_name"):
        return spotify_stark.listar_e_tocar_playlist(argumentos["playlist_name"])
    if argumentos.get("search_query"):
        return spotify_stark.abrir_e_buscar(argumentos["search_query"])
    return spotify_stark.controlar_reproducao(acao or "playpause") or "Spotify controlado."

def gerenciador_clima(argumentos: dict) -> str:
    cidade = argumentos.get("city", "")
    previsao = argumentos.get("forecast", "hoje").lower()
    if previsao == "amanha":
        return verificar_chuva_amanha(cidade) or "Sem previsão disponível."
    return obter_previsao_hoje(cidade) or "Sem informações de clima."

def gerenciador_alarme(argumentos: dict) -> str:
    operacao = argumentos.get("op", "add").lower()
    if operacao == "list":
        itens = listar_alarmes()
        if isinstance(itens, list):
            return "\n".join(f"• {item['hora']} — {item['missao']}" for item in itens)
        return str(itens)
    if operacao == "remove":
        return remover_alarme(argumentos.get("hora", ""), argumentos.get("missao", ""))
    hora = argumentos.get("hora", "")
    missao = argumentos.get("missao", "Lembrete")
    if not hora:
        return "Horário não informado."
    data_alarme = argumentos.get("data") or None
    if isinstance(data_alarme, str) and not data_alarme.strip():
        data_alarme = None
    return adicionar_alarme(hora, missao, data=data_alarme)

def gerenciador_memoria(argumentos: dict) -> str:
    categoria = argumentos.get("category")
    chave = argumentos.get("key")
    valor = argumentos.get("value")
    if not all([categoria, chave, valor]):
        return "Dados incompletos para salvar memória."
    memoria = load_memory()
    secao = memoria.get(categoria, {})
    secao[chave] = valor
    sucesso = update_memory(f"{categoria}.json", secao)
    return f"{categoria}/{chave} salvo." if sucesso else "Erro ao salvar memória."

def gerenciador_plano(argumentos: dict) -> str:
    from engine.ia_router import router
    objetivo = argumentos.get("goal", "").strip()
    contexto = argumentos.get("context", "")
    if not objetivo:
        return "Objetivo não informado."
    coro = router.responder(f"Crie um plano objetivo para: {objetivo}. Contexto: {contexto}")
    return executar_no_loop_atual(coro) or "Não foi possível criar o plano."

def gerenciador_computador(argumentos: dict) -> str:
    return computer_settings(argumentos)

def gerenciador_codigo(argumentos: dict) -> str:
    from engine.ia_router import router
    descricao = argumentos.get("description", "")
    linguagem = argumentos.get("language", "python")
    codigo_base = argumentos.get("code", "")
    executar_flag = argumentos.get("execute", False)
    if not descricao:
        return "Descrição do código ausente."
    comando_ia = f"Gere APENAS código {linguagem}: {descricao}. {codigo_base}"
    codigo_gerado = executar_no_loop_atual(router.responder(comando_ia))
    if executar_flag and codigo_gerado:
        cmd = f"python -c {codigo_gerado}" if linguagem == "python" else f"bash -c {codigo_gerado}"
        av = avaliar(cmd)
        if not av.permitido:
            return f"Bloqueado por segurança: {av.motivo}"
        return executar(cmd, timeout=15, ferramenta="code_helper")
    return codigo_gerado or "Falha ao gerar código."

def gerenciador_visao(argumentos: dict) -> str:
    from vision.capture import analisar_tela
    pergunta = argumentos.get("question", "O que está na tela?")
    return executar_no_loop_atual(analisar_tela(pergunta)) or "Falha na análise visual."

def gerenciador_casa_inteligente(argumentos: dict) -> str:
    from tasks.smart_home import (abrir_youtube_tv, buscar_id_tv, energia_tv, diagnosticar_falha_tv, status_tv)
    dispositivo = argumentos.get("device", "").lower()
    acao = argumentos.get("action", "").lower()
    if "tv" in dispositivo:
        if acao in ("youtube", "abrir_youtube", "app_youtube"):
            return abrir_youtube_tv()
        if acao == "on":
            if energia_tv(True): return "TV ligada."
            if not buscar_id_tv(): return diagnosticar_falha_tv()
            return "Falha ao ligar a TV."
        if acao == "off":
            if energia_tv(False): return "TV desligada."
            if not buscar_id_tv(): return diagnosticar_falha_tv()
            return "Erro ao desligar a TV."
        if acao == "status":
            return status_tv()
    return "Use smart_home apenas para a TV."

def gerenciador_troca_ia(argumentos: dict) -> str:
    from engine.ia_router import router
    modo = argumentos.get("mode", "ollama").lower()
    return router.definir_modo(modo)

def gerenciador_cmd(argumentos: dict) -> str:
    comando = argumentos.get("command", "").strip()
    tarefa = argumentos.get("task", "").strip()
    confirmado = argumentos.get("confirmado", False)
    if not comando and tarefa:
        from engine.ia_router import router
        prompt = f"Gere APENAS o comando de terminal para: {tarefa}. Responda somente com o comando puro."
        try:
            comando = executar_no_loop_atual(router.responder(prompt)).strip().strip("`").strip()
        except Exception as e:
            return f"Erro ao gerar comando: {e}"
    if not comando:
        return "Nenhum comando gerado ou informado."
    av = avaliar(comando)
    if not av.permitido:
        return f"Bloqueado por segurança: {av.motivo}"
    if av.confirmar and not confirmado:
        return f"Comando requer confirmação.\nComando: `{comando}`"
    return executar(comando, timeout=20, ferramenta="cmd_control")

def gerenciador_cache_status(argumentos: dict) -> str:
    acao = argumentos.get("action", "stats").lower()
    if acao == "limpar":
        from brain.tool_cache import limpar_cache
        return limpar_cache()
    if acao == "invalidar":
        tool = argumentos.get("tool", "")
        return invalidar_cache_tool(tool) if tool else "Informe o nome da ferramenta."
    if acao == "audit":
        registros = audit_recente(20)
        if not registros:
            return "Nenhum registro de auditoria."
        linhas = [f"[{r['ts']}] {r['ferramenta'] or r['origem']} — {r['comando'][:60]}" for r in registros]
        return "\n".join(linhas)
    stats = stats_cache()
    return f"Cache — Hits: {stats['hits']} | Misses: {stats['misses']} | Taxa: {stats['taxa_hit']}"

def gerenciador_agente_visual(argumentos: dict) -> str:
    tarefa = argumentos.get("task", "")
    if not tarefa:
        return "Nenhuma tarefa visual informada."
    wrapper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_s_wrapper.py"))
    try:
        processo = subprocess.run(["python", wrapper_path, tarefa, "--json"], capture_output=True, text=True, timeout=300)
        if processo.returncode == 0:
            try:
                dados = json.loads(processo.stdout)
                return f"Ação visual executada. Status: {dados.get('status')}. Info: {dados.get('message')}"
            except Exception:
                return f"Ação visual executada. Saída bruta: {processo.stdout[:200]}"
        else:
            return f"Falha na ação visual. Erro: {processo.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return "Agente visual abortado. Excedeu tempo limite de 5 minutos."
    except Exception as e:
        return f"Erro fatal ao invocar Agente S: {e}"

def gerenciador_visao_3d(argumentos: dict) -> str:
    try:
        from vision.capture import MotorVisaoEspacial
        import cv2
        motor_3d = MotorVisaoEspacial()
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Falha ao aceder à câmara para visão 3D."
        resultado = motor_3d.analisar_medida_cena(frame)
        if resultado["status"] == "sucesso":
            return f"Visão 3D ativada. Escala atual: {resultado['pixels_por_cm']} pixels por centímetro. Profundidade da referência: {resultado['profundidade']}."
        else:
            return f"Falha na visão 3D: {resultado['motivo']}"
    except Exception as e:
        return f"Erro ao processar visão 3D: {e}"

def gerenciador_traducao_multimodal(argumentos: dict) -> str:
    segundos = argumentos.get("segundos", 10)
    try:
        from tasks.multimodal import traduzir_ambiente
        resultado = executar_no_loop_atual(traduzir_ambiente(segundos))
        return resultado
    except Exception as e:
        return f"Falha no pipeline multimodal de tradução: {e}"

def gerenciador_otimizacao_dados(argumentos: dict) -> str:
    try:
        from storage.optimizer import comprimir_banco_auditoria
        resultado = executar_no_loop_atual(comprimir_banco_auditoria())
        return resultado
    except Exception as e:
        return f"Falha no módulo de otimização de banco de dados: {e}"

EXECUTOR_FERRAMENTAS: dict[str, Callable[[dict], str]] = {
    "open_app":         open_app,
    "computer_control": gerenciador_computador,
    "web_search":       gerenciador_web,
    "browser_control":  gerenciador_browser,
    "youtube_video":    gerenciador_youtube,
    "spotify_control":  gerenciador_spotify,
    "weather_report":   gerenciador_clima,
    "set_reminder":     gerenciador_alarme,
    "save_memory":      gerenciador_memoria,
    "agent_task":       gerenciador_plano,
    "code_helper":      gerenciador_codigo,
    "screen_analysis":  gerenciador_visao,
    "smart_home":       gerenciador_casa_inteligente,
    "switch_ia_mode":   gerenciador_troca_ia,
    "cmd_control":      gerenciador_cmd,
    "cache_status":     gerenciador_cache_status,
    "visual_gui_actuator": gerenciador_agente_visual,
    "medir_ambiente_3d": gerenciador_visao_3d,
    "traduzir_audio_ambiente": gerenciador_traducao_multimodal,
    "otimizar_banco_dados": gerenciador_otimizacao_dados,
}

async def despachar(nome: str, args: dict) -> str:
    func = EXECUTOR_FERRAMENTAS.get(nome)
    if func is None:
        return f"Ferramenta '{nome}' não encontrada."
    return await cache_despachar(nome, args, func)