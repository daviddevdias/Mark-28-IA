from __future__ import annotations

import asyncio
import logging
import webbrowser
from typing import Any, Callable

from tasks.browser import jarvis_web
from tasks.spotify_manager import spotify_stark
from tasks.open_app import open_app
from tasks.weather import obter_previsao_hoje, verificar_chuva_amanha
from tasks.alarm import adicionar_alarme, listar_alarmes, remover_alarme
from tasks.computer_control import computer_settings
from storage.memory_manager import load_memory, update_memory
from engine.cmd_security import avaliar, executar
from engine.tool_cache import despachar as cache_despachar, stats_cache, invalidar_cache_tool

log = logging.getLogger("jarvis.tools_mapper")







def executar_corotina(coro) -> Any:
    try:
        loop = asyncio.get_running_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    except RuntimeError:
        return asyncio.run(coro)







def gerenciador_web(argumentos: dict) -> str:
    pesquisa = argumentos.get("query", "").strip()
    if not pesquisa:
        return "Nenhum termo de pesquisa informado."
    return jarvis_web.run(jarvis_web.smart_search(pesquisa)) or "Sem resultados na web."







def gerenciador_browser(argumentos: dict) -> str:
    acao  = argumentos.get("action", "open").lower()
    url   = argumentos.get("url", "").strip()
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
    cidade   = argumentos.get("city", "")
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
    d = argumentos.get("data") or None
    if isinstance(d, str) and not d.strip():
        d = None
    return adicionar_alarme(hora, missao, data=d)







def gerenciador_memoria(argumentos: dict) -> str:
    categoria = argumentos.get("category")
    chave     = argumentos.get("key")
    valor     = argumentos.get("value")
    if not all([categoria, chave, valor]):
        return "Dados incompletos para salvar memória."
    memoria       = load_memory()
    secao         = memoria.get(categoria, {})
    secao[chave]  = valor
    sucesso       = update_memory(f"{categoria}.json", secao)
    return f"{categoria}/{chave} salvo." if sucesso else "Erro ao salvar memória."







def gerenciador_plano(argumentos: dict) -> str:
    from engine.ia_router import router
    objetivo = argumentos.get("goal", "").strip()
    contexto = argumentos.get("context", "")
    if not objetivo:
        return "Objetivo não informado."
    coro = router.responder(f"Crie um plano objetivo para: {objetivo}. Contexto: {contexto}")
    return executar_corotina(coro) or "Não foi possível criar o plano."







def gerenciador_computador(argumentos: dict) -> str:
    return computer_settings(argumentos)







def gerenciador_codigo(argumentos: dict) -> str:
    from engine.ia_router import router
    descricao   = argumentos.get("description", "")
    linguagem   = argumentos.get("language", "python")
    codigo_base = argumentos.get("code", "")
    executar_flag = argumentos.get("execute", False)
    if not descricao:
        return "Descrição do código ausente."
    comando_ia    = f"Gere APENAS código {linguagem}: {descricao}. {codigo_base}"
    codigo_gerado = executar_corotina(router.responder(comando_ia))
    if executar_flag and codigo_gerado:
        cmd = f"python -c {codigo_gerado}" if linguagem == "python" else f"bash -c {codigo_gerado}"
        av  = avaliar(cmd)
        if not av.permitido:
            return f"Bloqueado por segurança: {av.motivo}"
        return executar(cmd, timeout=15)
    return codigo_gerado or "Falha ao gerar código."







def gerenciador_visao(argumentos: dict) -> str:
    from vision.capture import analisar_tela
    pergunta = argumentos.get("question", "O que está na tela?")
    return executar_corotina(analisar_tela(pergunta)) or "Falha na análise visual."







def gerenciador_casa_inteligente(argumentos: dict) -> str:
    from tasks.smart_home import (
        abrir_youtube_tv,
        buscar_id_tv,
        energia_tv,
        msg_tv_nao_encontrada,
        status_tv,
    )

    dispositivo = argumentos.get("device", "").lower()
    acao = argumentos.get("action", "").lower()
    valor = argumentos.get("value")

    if "tv" in dispositivo:
        if acao in ("youtube", "abrir_youtube", "app_youtube"):
            return abrir_youtube_tv()
        if acao == "on":
            if energia_tv(True):
                return "TV ligada."
            if not buscar_id_tv():
                return msg_tv_nao_encontrada()
            return "Falha ao ligar a TV (comando ou modelo incompatível)."
        if acao == "off":
            if energia_tv(False):
                return "TV desligada."
            if not buscar_id_tv():
                return msg_tv_nao_encontrada()
            return "Erro ao desligar a TV."
        if acao == "status":
            return status_tv()

    return "Use smart_home apenas para a TV (device 'tv'). Lâmpadas foram desativadas nesta build."







def gerenciador_troca_ia(argumentos: dict) -> str:
    from engine.ia_router import router
    modo = argumentos.get("mode", "ollama").lower()
    return router.definir_modo(modo)







def gerenciador_cmd(argumentos: dict) -> str:
    comando    = argumentos.get("command", "").strip()
    tarefa     = argumentos.get("task", "").strip()
    confirmado = argumentos.get("confirmado", False)

    if not comando and tarefa:
        from engine.ia_router import router
        prompt = (
            f"Gere APENAS o comando de terminal para: {tarefa}. "
            "Responda somente com o comando puro, sem explicação, sem markdown, sem backticks."
        )
        try:
            comando = executar_corotina(router.responder(prompt)).strip().strip("`").strip()
        except Exception:
            return f"Erro ao gerar comando:"

    if not comando:
        return "Nenhum comando gerado ou informado."

    av = avaliar(comando)

    if not av.permitido:
        log.warning("Comando bloqueado: %s", comando[:80])
        return f"Bloqueado por segurança: {av.motivo}"

    if av.confirmar and not confirmado:
        return (
            f"Comando classificado como '{av.categoria.value}' — requer confirmação.\n"
            f"Comando: `{comando}`\n"
            f"Para executar, diga: 'confirmar e executar: {comando}'"
        )

    return executar(comando, timeout=20)







def gerenciador_cache_status(argumentos: dict) -> str:
    acao = argumentos.get("action", "stats").lower()
    if acao == "limpar":
        from engine.tool_cache import limpar_cache
        return limpar_cache()
    if acao == "invalidar":
        tool = argumentos.get("tool", "")
        return invalidar_cache_tool(tool) if tool else "Informe o nome da ferramenta."
    stats = stats_cache()
    return (
        f"Cache — Hits: {stats['hits']} | Misses: {stats['misses']} | "
        f"Taxa: {stats['taxa_hit']} | Entradas ativas: {stats['entradas_vivas']}"
    )

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
}







async def despachar(nome: str, args: dict) -> str:
    func = EXECUTOR_FERRAMENTAS.get(nome)
    if func is None:
        log.warning("Ferramenta desconhecida: %s", nome)
        return f"Ferramenta '{nome}' não encontrada."
    return await cache_despachar(nome, args, func)