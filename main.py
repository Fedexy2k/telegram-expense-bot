
import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from bot import ExpenseBot
from handlers.gasto import iniciar_gasto, recibir_descripcion, recibir_categoria, recibir_monto, recibir_metodo_pago
from handlers.rapido import iniciar_gasto_rapido, procesar_gasto_rapido, procesar_metodo_pago_rapido
from handlers.modo import cambiar_modo, procesar_cambio_modo
from handlers.resumen import generar_resumen

DESCRIPCION, CATEGORIA, MONTO, METODO_PAGO = range(4)
GASTO_RAPIDO, METODO_PAGO_RAPIDO = range(2)
CAMBIAR_MODO = 6

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

def main():
    TOKEN = os.getenv('BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ BOT_TOKEN no configurado!")
        return

    logger.info("🔧 Iniciando bot modularizado...")

    try:
        bot = ExpenseBot()
        logger.info("✅ Bot creado exitosamente")

        application = Application.builder().token(TOKEN).build()
        application.bot_data['bot'] = bot

        # Handler: gasto paso a paso
        gasto_handler = ConversationHandler(
            entry_points=[CommandHandler('gasto', iniciar_gasto)],
            states={
                DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
                CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_categoria)],
                MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
                METODO_PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_metodo_pago)],
            },
            fallbacks=[]
        )

        # Handler: gasto rápido
        rapido_handler = ConversationHandler(
            entry_points=[CommandHandler('rapido', iniciar_gasto_rapido)],
            states={
                GASTO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_gasto_rapido)],
                METODO_PAGO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_metodo_pago_rapido)],
            },
            fallbacks=[]
        )

        # Handler: cambio de modo
        modo_handler = ConversationHandler(
            entry_points=[CommandHandler('modo', cambiar_modo)],
            states={
                CAMBIAR_MODO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_cambio_modo)],
            },
            fallbacks=[]
        )

        # Registro de handlers
        application.add_handler(gasto_handler)
        application.add_handler(rapido_handler)
        application.add_handler(modo_handler)

        # Comandos simples
        application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("🤖 Bot iniciado.")))
        application.add_handler(CommandHandler("resumen", generar_resumen))
        application.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Comandos disponibles: /gasto /rapido /resumen /modo")))


        logger.info("🚀 Bot listo y corriendo...")
        application.run_polling()

    # --- ESTE ES EL BLOQUE QUE FALTABA ---
    except Exception as e:
        logger.error(f"❌ Error al iniciar el bot: {e}")
        import traceback
        traceback.print_exc()
