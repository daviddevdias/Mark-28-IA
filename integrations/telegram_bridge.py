import asyncio
import json
import re

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from engine.controller import processar_diretriz
from engine.ia_router import router
from storage.memory_manager import get_nome
from tasks.alarm import adicionar_alarme, listar_alarmes, remover_alarme
from tasks.weather import obter_previsao_hoje, verificar_chuva_amanha
from audio.audio import falar, interromper_voz
import config

TOKEN = getattr(config, "TELEGRAM_TOKEN", "")

app = None

_monitorando = False


def _nome() -> str:
    return get_nome() or "Chefe"


def _cidade_padrao() -> str:
    try:
        dados = config._carregar_json(config.API_DIR / "config_core.json")
        return dados.get("cidade_padrao", "São Paulo")
    except Exception:
        return "São Paulo"


async def _responder_e_falar(update: Update, texto: str):
    if not texto:
        return
    await update.message.reply_text(str(texto))
    asyncio.create_task(falar(str(texto)))


async def cmd_jarvis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    if not texto:
        await update.message.reply_text("Use: /jarvis <comando>")
        return

    resposta = await processar_diretriz(texto)

    if not resposta:
        resposta = await router.responder(texto, nome=_nome())

    await _responder_e_falar(update, resposta)


async def cmd_texto_livre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if not texto:
        return

    resposta = await processar_diretriz(texto)

    if not resposta:
        resposta = await router.responder(texto, nome=_nome())

    await _responder_e_falar(update, resposta)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from engine.ia_router import _DISPONIVEL, _MODELO_DETECTADO
    modelo = _MODELO_DETECTADO or "nenhum"
    ollama_status = "online" if _DISPONIVEL else "offline"
    msg = (
        f"J.A.R.V.I.S — SISTEMAS ATIVOS\n"
        f"Ollama: {ollama_status}\n"
        f"Modelo: {modelo}\n"
        f"Monitor: {'ativo' if _monitorando else 'inativo'}"
    )
    await update.message.reply_text(msg)


async def cmd_clima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cidade = " ".join(context.args).strip() if context.args else ""
    if not cidade:
        cidade = _cidade_padrao()

    await update.message.reply_text(f"Consultando clima em {cidade}...")

    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, obter_previsao_hoje, cidade)

    await _responder_e_falar(update, resposta)


async def cmd_clima_amanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cidade = " ".join(context.args).strip() if context.args else ""
    if not cidade:
        cidade = _cidade_padrao()

    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, verificar_chuva_amanha, cidade)

    await _responder_e_falar(update, resposta)


async def cmd_alarme_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /alarme HH:MM descricao")
        return

    hora = context.args[0]
    missao = " ".join(context.args[1:])
    resposta = adicionar_alarme(hora, missao)

    await _responder_e_falar(update, resposta)


async def cmd_alarme_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alarmes = listar_alarmes()
    if not alarmes:
        await update.message.reply_text("Nenhum alarme ativo.")
        return

    linhas = ["Alarmes ativos:\n"]
    for a in alarmes:
        linhas.append(f"• {a['hora']} — {a['missao']}")

    await update.message.reply_text("\n".join(linhas))


async def cmd_alarme_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /remover HH:MM descricao")
        return

    hora = context.args[0]
    missao = " ".join(context.args[1:])
    resposta = remover_alarme(hora, missao)

    await _responder_e_falar(update, resposta)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    interromper_voz()
    await update.message.reply_text("Voz interrompida.")


async def cmd_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    termo = " ".join(context.args).strip()
    if not termo:
        await update.message.reply_text("Use: /spotify <musica ou artista>")
        return

    resposta = await processar_diretriz(f"spotify {termo}")
    if not resposta:
        resposta = "Comando enviado ao Spotify."

    await _responder_e_falar(update, resposta)


async def cmd_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("pausar")
    await _responder_e_falar(update, resposta or "Música pausada.")


async def cmd_continuar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("continuar")
    await _responder_e_falar(update, resposta or "Reprodução retomada.")


async def cmd_proxima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("proxima")
    await _responder_e_falar(update, resposta or "Próxima faixa.")


async def cmd_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    termo = " ".join(context.args).strip()
    if not termo:
        await update.message.reply_text("Use: /youtube <busca>")
        return

    resposta = await processar_diretriz(f"youtube {termo}")
    await _responder_e_falar(update, resposta or "Abrindo YouTube.")


async def cmd_monitorar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _monitorando

    intervalo_arg = context.args[0] if context.args else "10"
    intervalo = max(5, int(intervalo_arg)) if intervalo_arg.isdigit() else 10

    _monitorando = True
    resposta = await processar_diretriz(f"monitorar tela {intervalo}")

    await _responder_e_falar(update, resposta or f"Monitoramento ativo. Intervalo: {intervalo}s.")


async def cmd_parar_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _monitorando
    _monitorando = False

    resposta = await processar_diretriz("desligar monitoramento")
    await _responder_e_falar(update, resposta or "Monitoramento desativado.")


async def cmd_tela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Capturando e analisando a tela...")

    resposta = await processar_diretriz("olha tela")
    await _responder_e_falar(update, resposta or "Análise concluída.")


async def cmd_abrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app_nome = " ".join(context.args).strip()
    if not app_nome:
        await update.message.reply_text("Use: /abrir <nome do app>")
        return

    resposta = await processar_diretriz(f"abrir {app_nome}")
    if not resposta:
        from tasks.open_app import open_app
        resposta = open_app({"app_name": app_nome}) or f"Abrindo {app_nome}."

    await _responder_e_falar(update, resposta)


async def cmd_bloquear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("bloquear")
    await _responder_e_falar(update, resposta or "Tela bloqueada.")


async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("screenshot")
    await _responder_e_falar(update, resposta or "Screenshot capturado.")


async def cmd_tv_ligar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("ligar tv")
    await _responder_e_falar(update, resposta or "Ligando TV.")


async def cmd_tv_desligar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("desligar tv")
    await _responder_e_falar(update, resposta or "Desligando TV.")


async def cmd_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nivel = context.args[0] if context.args else ""
    if not nivel.isdigit():
        await update.message.reply_text("Use: /volume <0-100>")
        return

    resposta = await processar_diretriz(f"volume {nivel}")
    await _responder_e_falar(update, resposta or f"Volume ajustado para {nivel}.")


async def cmd_trabalho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = await processar_diretriz("trabalho")
    await _responder_e_falar(update, resposta or "Modo trabalho ativado.")


async def cmd_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    modo = " ".join(context.args).strip().lower()
    if modo not in ("ollama", "gemini", "auto"):
        await update.message.reply_text("Use: /ia ollama | gemini | auto")
        return

    msg = router.definir_modo(modo)
    await _responder_e_falar(update, msg)


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "J.A.R.V.I.S — COMANDOS DISPONÍVEIS\n\n"
        "GERAL\n"
        "/jarvis <cmd>   — envia qualquer comando\n"
        "/status         — status do sistema\n"
        "/stop           — para a voz\n\n"
        "CLIMA\n"
        "/clima [cidade] — clima atual\n"
        "/amanha [cidade]— previsão amanhã\n\n"
        "ALARMES\n"
        "/alarme HH:MM descricao\n"
        "/listar         — listar alarmes\n"
        "/remover HH:MM descricao\n\n"
        "MÚSICA\n"
        "/spotify <busca>\n"
        "/pausar\n"
        "/continuar\n"
        "/proxima\n"
        "/youtube <busca>\n\n"
        "SISTEMA\n"
        "/abrir <app>\n"
        "/bloquear\n"
        "/screenshot\n"
        "/trabalho\n"
        "/volume <0-100>\n\n"
        "TV\n"
        "/tvligar\n"
        "/tvdesligar\n\n"
        "VISÃO\n"
        "/tela           — analisa a tela agora\n"
        "/monitorar [s]  — monitoramento contínuo\n"
        "/pararmonitor   — para monitoramento\n\n"
        "IA\n"
        "/ia ollama|gemini|auto\n\n"
        "Ou fale diretamente comigo sem comandos."
    )
    await update.message.reply_text(texto)


async def _configurar_comandos(application: Application):
    comandos = [
        BotCommand("jarvis",       "Enviar comando ao Jarvis"),
        BotCommand("status",       "Status do sistema"),
        BotCommand("clima",        "Clima atual"),
        BotCommand("amanha",       "Previsão amanhã"),
        BotCommand("alarme",       "Criar alarme HH:MM desc"),
        BotCommand("listar",       "Listar alarmes"),
        BotCommand("remover",      "Remover alarme"),
        BotCommand("spotify",      "Tocar no Spotify"),
        BotCommand("pausar",       "Pausar música"),
        BotCommand("continuar",    "Continuar música"),
        BotCommand("proxima",      "Próxima faixa"),
        BotCommand("youtube",      "Tocar no YouTube"),
        BotCommand("abrir",        "Abrir aplicativo"),
        BotCommand("bloquear",     "Bloquear tela"),
        BotCommand("screenshot",   "Capturar tela"),
        BotCommand("tela",         "Analisar tela"),
        BotCommand("monitorar",    "Monitoramento contínuo"),
        BotCommand("pararmonitor", "Parar monitoramento"),
        BotCommand("tvligar",      "Ligar TV"),
        BotCommand("tvdesligar",   "Desligar TV"),
        BotCommand("volume",       "Ajustar volume"),
        BotCommand("trabalho",     "Modo trabalho"),
        BotCommand("ia",           "Trocar modelo IA"),
        BotCommand("stop",         "Parar voz"),
        BotCommand("ajuda",        "Lista de comandos"),
    ]
    await application.bot.set_my_commands(comandos)


def iniciar_telegram():
    global app

    if not TOKEN:
        print("[TELEGRAM] TELEGRAM_TOKEN não configurado em config. Bot não iniciado.")
        return

    print("[TELEGRAM] Jarvis FULL iniciado")

    app = Application.builder().token(TOKEN).post_init(_configurar_comandos).build()

    app.add_handler(CommandHandler("jarvis",       cmd_jarvis))
    app.add_handler(CommandHandler("status",       cmd_status))
    app.add_handler(CommandHandler("clima",        cmd_clima))
    app.add_handler(CommandHandler("amanha",       cmd_clima_amanha))
    app.add_handler(CommandHandler("stop",         cmd_stop))
    app.add_handler(CommandHandler("ajuda",        cmd_ajuda))

    app.add_handler(CommandHandler("alarme",       cmd_alarme_add))
    app.add_handler(CommandHandler("listar",       cmd_alarme_list))
    app.add_handler(CommandHandler("remover",      cmd_alarme_remove))

    app.add_handler(CommandHandler("spotify",      cmd_spotify))
    app.add_handler(CommandHandler("pausar",       cmd_pausar))
    app.add_handler(CommandHandler("continuar",    cmd_continuar))
    app.add_handler(CommandHandler("proxima",      cmd_proxima))
    app.add_handler(CommandHandler("youtube",      cmd_youtube))

    app.add_handler(CommandHandler("abrir",        cmd_abrir))
    app.add_handler(CommandHandler("bloquear",     cmd_bloquear))
    app.add_handler(CommandHandler("screenshot",   cmd_screenshot))
    app.add_handler(CommandHandler("trabalho",     cmd_trabalho))
    app.add_handler(CommandHandler("volume",       cmd_volume))

    app.add_handler(CommandHandler("tvligar",      cmd_tv_ligar))
    app.add_handler(CommandHandler("tvdesligar",   cmd_tv_desligar))

    app.add_handler(CommandHandler("tela",         cmd_tela))
    app.add_handler(CommandHandler("monitorar",    cmd_monitorar))
    app.add_handler(CommandHandler("pararmonitor", cmd_parar_monitor))

    app.add_handler(CommandHandler("ia",           cmd_ia))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_texto_livre))

    app.run_polling()