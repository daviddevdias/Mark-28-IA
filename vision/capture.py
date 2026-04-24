from __future__ import annotations

import asyncio

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import config
from engine.controller import processar_diretriz
from engine.ia_router import router
from storage.memory_manager import get_nome
from tasks.alarm import adicionar_alarme, listar_alarmes, remover_alarme, parar_alarme_total
from tasks.weather import obter_previsao_hoje, verificar_chuva_amanha
from audio.audio import falar, interromper_voz

TOKEN      = getattr(config, "TELEGRAM_TOKEN", "")
monitorando = False







def nome() -> str:
    return get_nome() or "Chefe"







def cidade_padrao() -> str:
    try:
        return config.carregar_tudo().get("cidade_padrao", "São Paulo")
    except Exception:
        return "São Paulo"







async def responder(update: Update, texto: str) -> None:
    if not texto:
        return
    await update.message.reply_text(str(texto))
    asyncio.create_task(falar(str(texto)))







async def processar(update: Update, texto: str) -> None:
    resposta = await processar_diretriz(texto)
    if not resposta:
        resposta = await router.responder(texto, nome=nome())
    await responder(update, resposta)







async def cmd_jarvis(u: Update, c: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(c.args)
    if not texto:
        await u.message.reply_text("Use: /jarvis <comando>")
        return
    await processar(u, texto)







async def cmd_livre(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.message.text:
        await processar(u, u.message.text)







async def cmd_status(u: Update, c: ContextTypes.DEFAULT_TYPE):
    from engine.ia_router import modelo, disponivel
    await u.message.reply_text(
        f"J.A.R.V.I.S\nOllama: {'online' if disponivel else 'offline'}\n"
        f"Modelo: {modelo or 'nenhum'}\nMonitor: {'ativo' if monitorando else 'inativo'}"
    )







async def cmd_clima(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cidade = " ".join(c.args).strip() or cidade_padrao()
    loop   = asyncio.get_event_loop()
    await responder(u, await loop.run_in_executor(None, obter_previsao_hoje, cidade))







async def cmd_amanha(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cidade = " ".join(c.args).strip() or cidade_padrao()
    loop   = asyncio.get_event_loop()
    await responder(u, await loop.run_in_executor(None, verificar_chuva_amanha, cidade))







async def cmd_alarme(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if len(c.args) < 2:
        await u.message.reply_text("Use: /alarme HH:MM descricao")
        return
    await responder(u, adicionar_alarme(c.args[0], " ".join(c.args[1:])))







async def cmd_listar(u: Update, c: ContextTypes.DEFAULT_TYPE):
    itens = listar_alarmes()
    if not itens:
        await u.message.reply_text("Nenhum alarme ativo.")
        return
    await u.message.reply_text("Alarmes:\n" + "\n".join(f"• {a['hora']} — {a['missao']}" for a in itens))







async def cmd_remover(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if len(c.args) < 2:
        await u.message.reply_text("Use: /remover HH:MM descricao")
        return
    await responder(u, remover_alarme(c.args[0], " ".join(c.args[1:])))







async def cmd_parar_alarme(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, parar_alarme_total())







async def cmd_stop(u: Update, c: ContextTypes.DEFAULT_TYPE):
    interromper_voz()
    await u.message.reply_text("Voz interrompida.")







async def cmd_spotify(u: Update, c: ContextTypes.DEFAULT_TYPE):
    termo = " ".join(c.args).strip()
    if not termo:
        await u.message.reply_text("Use: /spotify <música>")
        return
    await processar(u, f"spotify {termo}")







async def cmd_pausar(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("pausar") or "Pausado.")







async def cmd_continuar(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("continuar") or "Retomado.")







async def cmd_proxima(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("proxima") or "Próxima.")







async def cmd_youtube(u: Update, c: ContextTypes.DEFAULT_TYPE):
    termo = " ".join(c.args).strip()
    if not termo:
        await u.message.reply_text("Use: /youtube <busca>")
        return
    await processar(u, f"youtube {termo}")







async def cmd_monitorar(u: Update, c: ContextTypes.DEFAULT_TYPE):
    global monitorando
    intervalo = int(c.args[0]) if c.args and c.args[0].isdigit() else 10
    monitorando = True
    await responder(u, await processar_diretriz(f"monitorar tela {intervalo}") or f"Monitor ativo. Intervalo: {intervalo}s.")







async def cmd_parar_monitor(u: Update, c: ContextTypes.DEFAULT_TYPE):
    global monitorando
    monitorando = False
    await responder(u, await processar_diretriz("desligar monitoramento") or "Monitor desativado.")







async def cmd_tela(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Analisando tela...")
    await responder(u, await processar_diretriz("olha tela") or "Análise concluída.")







async def cmd_abrir(u: Update, c: ContextTypes.DEFAULT_TYPE):
    nome_app = " ".join(c.args).strip()
    if not nome_app:
        await u.message.reply_text("Use: /abrir <app>")
        return
    resp = await processar_diretriz(f"abrir {nome_app}")
    if not resp:
        from tasks.open_app import open_app
        resp = open_app({"app_name": nome_app}) or f"Abrindo {nome_app}."
    await responder(u, resp)







async def cmd_bloquear(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("bloquear") or "Bloqueado.")







async def cmd_screenshot(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("screenshot") or "Screenshot capturado.")







async def cmd_tvligar(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("ligar tv") or "Ligando TV.")







async def cmd_tvdesligar(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("desligar tv") or "Desligando TV.")







async def cmd_volume(u: Update, c: ContextTypes.DEFAULT_TYPE):
    nivel = c.args[0] if c.args else ""
    if not nivel.isdigit():
        await u.message.reply_text("Use: /volume <0-100>")
        return
    await responder(u, await processar_diretriz(f"volume {nivel}") or f"Volume {nivel}.")







async def cmd_trabalho(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await responder(u, await processar_diretriz("trabalho") or "Modo trabalho ativado.")







async def cmd_ia(u: Update, c: ContextTypes.DEFAULT_TYPE):
    modo = " ".join(c.args).strip().lower()
    if modo not in ("ollama", "gemini", "auto"):
        await u.message.reply_text("Use: /ia ollama | gemini | auto")
        return
    await responder(u, router.definir_modo(modo))







async def cmd_ajuda(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(
        "J.A.R.V.I.S — COMANDOS\n\n"
        "GERAL: /jarvis /status /stop\n"
        "CLIMA: /clima /amanha\n"
        "ALARMES: /alarme /listar /remover /paralarme\n"
        "MÚSICA: /spotify /pausar /continuar /proxima /youtube\n"
        "SISTEMA: /abrir /bloquear /screenshot /trabalho /volume\n"
        "TV: /tvligar /tvdesligar\n"
        "VISÃO: /tela /monitorar /pararmonitor\n"
        "IA: /ia ollama|gemini|auto\n\n"
        "Ou fale diretamente sem comandos."
    )







async def setup_comandos(app: Application):
    await app.bot.set_my_commands([
        BotCommand("jarvis",       "Enviar comando"),
        BotCommand("status",       "Status do sistema"),
        BotCommand("clima",        "Clima atual"),
        BotCommand("amanha",       "Previsão amanhã"),
        BotCommand("alarme",       "Criar alarme"),
        BotCommand("listar",       "Listar alarmes"),
        BotCommand("remover",      "Remover alarme"),
        BotCommand("paralarme",    "Parar alarme"),
        BotCommand("spotify",      "Tocar no Spotify"),
        BotCommand("pausar",       "Pausar"),
        BotCommand("continuar",    "Continuar"),
        BotCommand("proxima",      "Próxima faixa"),
        BotCommand("youtube",      "YouTube"),
        BotCommand("abrir",        "Abrir app"),
        BotCommand("bloquear",     "Bloquear tela"),
        BotCommand("screenshot",   "Capturar tela"),
        BotCommand("tela",         "Analisar tela"),
        BotCommand("monitorar",    "Monitoramento"),
        BotCommand("pararmonitor", "Parar monitor"),
        BotCommand("tvligar",      "Ligar TV"),
        BotCommand("tvdesligar",   "Desligar TV"),
        BotCommand("volume",       "Volume"),
        BotCommand("trabalho",     "Modo trabalho"),
        BotCommand("ia",           "Trocar IA"),
        BotCommand("stop",         "Parar voz"),
        BotCommand("ajuda",        "Ajuda"),
    ])







def iniciar_telegram():
    if not TOKEN:
        print("[TELEGRAM] Token não configurado. Bot não iniciado.")
        return

    print("[TELEGRAM] Iniciando...")
    app = Application.builder().token(TOKEN).post_init(setup_comandos).build()

    handlers = [
        ("jarvis",       cmd_jarvis),
        ("status",       cmd_status),
        ("clima",        cmd_clima),
        ("amanha",       cmd_amanha),
        ("stop",         cmd_stop),
        ("ajuda",        cmd_ajuda),
        ("alarme",       cmd_alarme),
        ("listar",       cmd_listar),
        ("remover",      cmd_remover),
        ("paralarme",    cmd_parar_alarme),
        ("spotify",      cmd_spotify),
        ("pausar",       cmd_pausar),
        ("continuar",    cmd_continuar),
        ("proxima",      cmd_proxima),
        ("youtube",      cmd_youtube),
        ("abrir",        cmd_abrir),
        ("bloquear",     cmd_bloquear),
        ("screenshot",   cmd_screenshot),
        ("trabalho",     cmd_trabalho),
        ("volume",       cmd_volume),
        ("tvligar",      cmd_tvligar),
        ("tvdesligar",   cmd_tvdesligar),
        ("tela",         cmd_tela),
        ("monitorar",    cmd_monitorar),
        ("pararmonitor", cmd_parar_monitor),
        ("ia",           cmd_ia),
    ]

    for nome_handler, fn in handlers:
        app.add_handler(CommandHandler(nome_handler, fn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_livre))

    app.run_polling()