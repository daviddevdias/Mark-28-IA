from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from engine.core import processar_diretriz


TOKEN = "SEU_TOKEN_DO_BOT_AQUI"


# recebe qualquer mensagem do celular
async def receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):






    texto = update.message.text






    






    # manda pro cérebro do Jarvis






    resposta = await processar_diretriz(texto)






    






    # se tiver resposta, devolve






    if resposta:






        await update.message.reply_text(resposta)






    else:






        await update.message.reply_text("Comando executado.")


def iniciar_telegram():






    app = Application.builder().token(TOKEN).build()






    






    app.add_handler(






        MessageHandler(filters.TEXT & ~filters.COMMAND, receber_mensagem)






    )






    






    print("[TELEGRAM] Jarvis conectado ao celular.")



    app.run_polling()