import os
import sys
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot import ExpenseBot

# FIX: Asegurar que el directorio de trabajo sea correcto
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
sys.path.insert(0, current_dir)

# Importaciones directas con nombres en minúsculas
from handlers.gasto import iniciar_gasto, recibir_descripcion, recibir_categoria, recibir_monto, recibir_metodo_pago
from handlers.rapido import iniciar_gasto_rapido, procesar_gasto_rapido, procesar_metodo_pago_rapido
from handlers.ingresos import iniciar_ingreso_rapido, procesar_ingreso_rapido, procesar_monto_ingreso
from handlers.modo import cambiar_modo, procesar_cambio_modo
from handlers.resumen import generar_resumen
from handlers.recordatorios import RecordatorioManager, toggle_recordatorios, configurar_presupuesto
from datetime import datetime

# Estados de conversación
DESCRIPCION, CATEGORIA, MONTO, METODO_PAGO = range(4)
GASTO_RAPIDO, METODO_PAGO_RAPIDO = range(2)
INGRESO_RAPIDO, MONTO_INGRESO = range(2)
CAMBIAR_MODO = 6

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)


async def post_init(application: Application):
    """Tareas que se ejecutan después de que el bot se inicializa pero antes de que empiece a recibir mensajes."""
    # Inicializar y arrancar el sistema de recordatorios
    recordatorio_manager = RecordatorioManager(application)
    application.create_task(recordatorio_manager.loop_recordatorios())

# Función para cancelar conversaciones
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Operación cancelada. Comandos disponibles:\n\n"
        "💸 /gasto - Registrar gasto detallado\n"
        "⚡ /rapido - Gasto rápido\n"
        "💰 /ingreso - Registrar ingreso\n"
        "📊 /resumen - Ver resumen del mes\n"
        "🎭 /modo - Cambiar personalidad\n"
        "🔔 /recordatorios - Activar/desactivar recordatorios\n"
        "💰 /presupuesto - Info sobre presupuestos",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def ayuda_extendida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "🤖 *Bot de Gastos Personales*\n\n"
        "*Comandos principales:*\n"
        "💸 /gasto - Registrar gasto paso a paso\n"
        "⚡ /rapido - Gastos frecuentes rápidos\n"
        "💰 /ingreso - Registrar ingresos\n"
        "📊 /resumen - Resumen mensual\n\n"
        "*Configuración:*\n"
        "🎭 /modo - Cambiar personalidad del bot\n"
        "🔔 /recordatorios - Recordatorios diarios\n"
        "💰 /presupuesto - Configurar alertas\n\n"
        "*Otros:*\n"
        "❌ /cancel - Cancelar operación\n"
        "❓ /help - Ver esta ayuda\n\n"
        "*Funcionalidades:*\n"
        "• Alertas de presupuesto por categoría\n"
        "• Actualización automática del presupuesto\n"
        "• Recordatorios a las 13:00 y 22:00\n"
        "• Tres modos de personalidad\n"
        "• Integración completa con Google Sheets"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# Función mejorada para el gasto que incluye verificación de presupuesto
async def recibir_metodo_pago_con_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metodo = update.message.text
    bot = context.bot_data['bot']
    user_id = update.effective_user.id

    if metodo not in ['💵 Efectivo', '💳 Débito']:
        from telegram import ReplyKeyboardMarkup
        reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("❌ Método no válido. Seleccioná uno correcto:", reply_markup=reply_markup)
        return METODO_PAGO

    desc = context.user_data['descripcion']
    cat = context.user_data['categoria']
    monto = context.user_data['monto']

    # Guardar el gasto
    bot.guardar_gasto(desc, cat, monto, metodo)
    
    # Verificar presupuesto y obtener alerta si corresponde
    alerta_presupuesto = await bot.verificar_presupuesto(cat, user_id)
    
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    mensaje_personalizado = bot.get_message(user_id, 'success_gasto')

    # Construir mensaje final
    texto_final = (
        f"✅ ¡Gasto registrado!\n\n"
        f"📅 {fecha}\n📝 {desc}\n📂 {cat}\n💰 {bot.formatear_pesos(monto)}\n💳 {metodo}\n\n"
        f"{mensaje_personalizado}\n\n"
    )
    
    # Agregar alerta de presupuesto si existe
    if alerta_presupuesto:
        texto_final += f"{alerta_presupuesto}\n\n"
    
    texto_final += "Para continuar, usa: /gasto, /rapido, /ingreso, /resumen"
    
    await update.message.reply_text(texto_final, reply_markup=ReplyKeyboardRemove())
    
    context.user_data.clear()
    return ConversationHandler.END

# Funciones placeholder para configuración (hasta que tengas el archivo)


def main():
    TOKEN = os.getenv('BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ BOT_TOKEN no configurado!")
        return

    logger.info("🔧 Iniciando bot modularizado...")
    logger.info(f"Token configurado: {TOKEN[:10]}...")

    try:
        bot = ExpenseBot()
        logger.info("✅ Bot creado exitosamente")

        application = Application.builder().token(TOKEN).post_init(post_init).build()
        application.bot_data['bot'] = bot

        
        # Handler: gasto paso a paso (con alertas de presupuesto y subcategorías)
        gasto_handler = ConversationHandler(
            entry_points=[CommandHandler('gasto', iniciar_gasto)],
            states={
                DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
                CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_categoria)],

                # --- CORRECCIÓN 1: AÑADIR EL ESTADO SUBCATEGORIA ---
                SUBCATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_subcategoria)],

                MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],

                # --- CORRECCIÓN 2: USAR LA FUNCIÓN CON ALERTA ---
                METODO_PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_metodo_pago_con_alerta)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        # Handler: gasto rápido
        rapido_handler = ConversationHandler(
            entry_points=[CommandHandler('rapido', iniciar_gasto_rapido)],
            states={
                GASTO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_gasto_rapido)],
                METODO_PAGO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_metodo_pago_rapido)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        # Handler: ingresos rápidos
        ingreso_handler = ConversationHandler(
            entry_points=[CommandHandler('ingreso', iniciar_ingreso_rapido)],
            states={
                INGRESO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_ingreso_rapido)],
                MONTO_INGRESO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_monto_ingreso)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        # Handler: cambio de modo
        modo_handler = ConversationHandler(
            entry_points=[CommandHandler('modo', cambiar_modo)],
            states={
                CAMBIAR_MODO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_cambio_modo)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        # Registro de handlers
        application.add_handler(gasto_handler)
        application.add_handler(rapido_handler)
        application.add_handler(ingreso_handler)
        application.add_handler(modo_handler)

        # Comandos simples
        application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("🤖 Bot de gastos iniciado. Usa /help para ver comandos.")))
        application.add_handler(CommandHandler("resumen", generar_resumen))
        application.add_handler(CommandHandler("help", ayuda_extendida))
        application.add_handler(CommandHandler("cancel", cancel))
        application.add_handler(CommandHandler("recordatorios", toggle_recordatorios))
        application.add_handler(CommandHandler("presupuesto", configurar_presupuesto))

        logger.info("🚀 Bot listo y corriendo...")
        logger.info("🔗 Iniciando polling...")
        
        application.run_polling()

    except Exception as e:
        logger.error(f"❌ Error al iniciar el bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()