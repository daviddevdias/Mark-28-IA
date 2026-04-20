from __future__ import annotations

import asyncio
import subprocess
from typing import Callable

from tasks.browser import _jarvis_web
from tasks.spotify_manager import spotify_stark
from tasks.open_app import open_app
from tasks.weather import obter_previsao_hoje, verificar_chuva_amanha
from tasks.alarm import adicionar_alarme, listar_alarmes, remover_alarme
from tasks.file_controller import file_controller
from tasks.computer_control import computer_settings
from storage.memory_manager import load_memory, update_memory







def executar_corotina(coro):
    try:
        loop = asyncio.get_running_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    except RuntimeError:
        return asyncio.run(coro)










def gerenciador_web(argumentos: dict) -> str:
    pesquisa = argumentos.get("query", "").strip()

    if not pesquisa:
        return ""

    return _jarvis_web.run(_jarvis_web.smart_search(pesquisa)) or "Sem resultados na web."





def gerenciador_youtube(argumentos: dict) -> str:
    pesquisa = argumentos.get("query", "").strip()

    if not pesquisa:
        return ""

    return (
        _jarvis_web.run(_jarvis_web.tocar_youtube(pesquisa))
        or "Nada encontrado no YouTube."
    )






def gerenciador_spotify(argumentos: dict) -> str:
    acao = argumentos.get("action", "").lower()

    if argumentos.get("playlist_name"):
        return spotify_stark.listar_e_tocar_playlist(argumentos["playlist_name"])

    if argumentos.get("search_query"):
        return spotify_stark.abrir_e_buscar(argumentos["search_query"])

    return spotify_stark.controlar_reproducao(acao or "playpause") or ""







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

    return adicionar_alarme(hora, missao)







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

    return f"{categoria}/{chave} salvo com sucesso." if sucesso else "Erro ao salvar memória."






def gerenciador_plano(argumentos: dict) -> str:

    from engine.ia_router import router

    objetivo = argumentos.get("goal", "").strip()
    contexto = argumentos.get("context", "")

    if not objetivo:
        return ""

    plano_coro = router.responder(
        f"Crie um plano objetivo para: {objetivo}. Contexto: {contexto}"
    )

    return executar_corotina(plano_coro) or "Não foi possível criar o plano estratégico."







def gerenciador_computador(argumentos: dict) -> str:
    return computer_settings(argumentos)






def gerenciador_arquivos(argumentos: dict) -> str:
    file_controller(argumentos)
    return "Comando de arquivo processado."






def gerenciador_codigo(argumentos: dict) -> str:
    from engine.ia_router import router

    descricao = argumentos.get("description", "")
    linguagem = argumentos.get("language", "python")
    codigo_base = argumentos.get("code", "")
    executar = argumentos.get("execute", False)

    if not descricao:
        return "Descrição do código ausente."

    comando_ia = f"Gere APENAS código {linguagem}: {descricao}. {codigo_base}"
    codigo_gerado = executar_corotina(router.responder(comando_ia))

    if executar and codigo_gerado:
        try:
            resultado = subprocess.run(
                ["python", "-c", codigo_gerado]
                if linguagem == "python"
                else ["bash", "-c", codigo_gerado],
                capture_output=True,
                text=True,
                timeout=15,
            )

            saida = (resultado.stdout or resultado.stderr or "").strip()
            return saida[:300] if saida else "Código executado sem retorno."

        except Exception:
            return "Erro na execução."

    return codigo_gerado or "Falha ao gerar código."







def gerenciador_visao(argumentos: dict) -> str:
    from vision.capture import analisar_tela 

    pergunta = argumentos.get("question", "O que está na tela?")
    
    return executar_corotina(analisar_tela(pergunta)) or "Falha na análise visual."








def gerenciador_casa_inteligente(argumentos: dict) -> str:
    from tasks.smart_home import enviar_comando_tv, ligar_tv

    dispositivo = argumentos.get("device", "").lower()
    acao = argumentos.get("action", "").lower()

    if "tv" in dispositivo:
        if acao == "on":
            return "TV ligada" if ligar_tv() else "Falha ao ligar TV"

        if acao == "off":
            return "TV desligada" if enviar_comando_tv("off", "switch") else "Erro ao desligar TV"

    if "lamp" in dispositivo or "luz" in dispositivo:
        return "Comando de iluminação enviado."

    return "Dispositivo não reconhecido."









def gerenciador_troca_ia(argumentos: dict) -> str:
    from engine.ia_router import router 
    
    modo = argumentos.get("mode", "gemini").lower()
    return router.definir_modo(modo)







def gerenciador_cmd(argumentos: dict) -> str:
    comando = argumentos.get("command")
    
    if not comando:
        return "Comando não gerado."
    
    try:
        resultado = subprocess.run(
            comando, shell=True, capture_output=True, text=True, timeout=10
        )
        saida = resultado.stdout or resultado.stderr or "Comando executado."
        return saida[:500]
    except Exception:
        return "Erro ao executar comando."







EXECUTOR_FERRAMENTAS: dict[str, Callable[[dict], str]] = {
    "open_app": open_app,
    "computer_control": gerenciador_computador,
    "web_search": gerenciador_web,
    "youtube_video": gerenciador_youtube,
    "spotify_control": gerenciador_spotify,
    "weather_report": gerenciador_clima,
    "set_reminder": gerenciador_alarme,
    "file_controller": gerenciador_arquivos,
    "save_memory": gerenciador_memoria,
    "agent_task": gerenciador_plano,
    "code_helper": gerenciador_codigo,
    "screen_analysis": gerenciador_visao,
    "smart_home": gerenciador_casa_inteligente,
    "switch_ia_mode": gerenciador_troca_ia,
    "cmd_control": gerenciador_cmd,
}