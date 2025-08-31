# main.py (Corregido)
import os
import sys
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, MenuButtonCommands
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from bot import ExpenseBot

# --- Configuración Inicial ---
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
sys.path.insert(0, current_dir)

# --- Importaciones de Handlers ---
from handlers.gasto import iniciar_gasto, recibir_descripcion, recibir_categoria, recibir_subcategoria, recibir_monto
from handlers.rapido import iniciar_gasto_rapido, procesar_gasto_rapido, procesar_metodo_pago_rapido
from handlers.ingresos import iniciar_ingreso_rapido, procesar_ingreso_rapido, procesar_monto_ingreso
from handlers.modo import cambiar_modo, procesar_cambio_modo
from handlers.ahorro import (
    iniciar_ahorro, recibir_monto_ahorro, recibir_destino_ahorro, recibir_monto_dolares,
    MONTO_AHORRO, DESTINO_AHORRO, MONTO_DOLARES
)
from handlers.resumen import generar_resumen
from handlers.recordatorios import RecordatorioManager, toggle_recordatorios, configurar_presupuesto
from datetime import datetime

# --- Definición de Estados de Conversación ---
DESCRIPCION, CATEGORIA, SUBCATEGORIA, MONTO, METODO_PAGO = range(5)
(GASTO_RAPIDO, METODO_PAGO_RAPIDO) = range(5, 7)
(INGRESO_RAPIDO, MONTO_INGRESO) = range(7, 9)
CAMBIAR_MODO = 9

# --- Configuración de Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Teclado del Menú Principal ---
menu_keyboard = [
    ['💸 Gasto', '⚡ Rápido'],
    ['💰 Ingreso', '💹 Ahorro'],
    ['📊 Resumen', '❓ Ayuda']
]
menu_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

# --- Funciones Principales ---
async def post_init(application: Application):
    """Tareas post-inicialización: configurar menú y recordatorios."""
    recordatorio_manager = RecordatorioManager(application)
    application.create_task(recordatorio_manager.loop_recordatorios())
    
    commands = [
        ('start', '🚀 Inicia el bot y muestra el menú'),
        ('menu', '📖 Muestra el menú principal'),
        ('cancel', '❌ Cancela la operación actual')
    ]
    await application.bot.set_my_commands(commands)
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Botón de menú y comandos configurados.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función de bienvenida que muestra el menú."""
    await update.message.reply_text(
        "🤖 ¡Hola! Soy tu asistente de finanzas. Elige una opción para empezar:",
        reply_markup=menu_markup
    )

async def mostrar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú principal."""
    await update.message.reply_text("📖 Menú Principal", reply_markup=menu_markup)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la conversación y muestra el menú principal."""
    await update.message.reply_text(
        "❌ Operación cancelada.",
        reply_markup=menu_markup
    )
    context.user_data.clear()
    return ConversationHandler.END

async def ayuda_extendida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la ayuda extendida."""
    mensaje = (
        "🤖 *Bot de Gastos Personales*\n\n"
        "Puedes usar los botones del menú o los siguientes comandos:\n\n"
        "💸 /gasto - Registrar gasto paso a paso\n"
        "⚡ /rapido - Gastos frecuentes rápidos\n"
        "💰 /ingreso - Registrar ingresos\n"
        "💹 /ahorro - Registrar un ahorro\n"
        "📊 /resumen - Resumen mensual\n\n"
        "*Configuración:*\n"
        "🎭 /modo - Cambiar personalidad del bot\n"
        "🔔 /recordatorios - Activar/desactivar recordatorios diarios\n\n"
        "*Otros:*\n"
        "❌ /cancel - Cancelar operación\n"
        "❓ /help o /menu - Ver esta ayuda o el menú"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=menu_markup)

async def recibir_metodo_pago_con_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el gasto, verifica presupuesto y finaliza mostrando el menú."""
    metodo = update.message.text
    bot = context.bot_data['bot']
    user_id = update.effective_user.id
    metodos_validos = [item for sublist in bot.metodos_pago for item in sublist]

    if metodo not in metodos_validos:
        reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("❌ Método no válido. Seleccioná uno correcto:", reply_markup=reply_markup)
        return METODO_PAGO

    desc = context.user_data['descripcion']
    cat = context.user_data['categoria']
    subcat = context.user_data.get('subcategoria', '')
    monto = context.user_data['monto']

    await bot.guardar_gasto(desc, cat, subcat, monto, metodo)
    alerta_presupuesto = await bot.verificar_presupuesto(cat, subcat, user_id)
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    mensaje_personalizado = bot.get_message(user_id, 'success_gasto')

    texto_final = (
        f"✅ ¡Gasto registrado!\n\n"
        f"📅 {fecha}\n📝 {desc}\n📂 {cat} -> {subcat}\n💰 {bot.formatear_pesos(monto)}\n💳 {metodo}\n\n"
        f"{mensaje_personalizado}\n"
    )
    
    if alerta_presupuesto:
        texto_final += f"\n{alerta_presupuesto}\n"
    
    await update.message.reply_text(texto_final, reply_markup=menu_markup)
    context.user_data.clear()
    return ConversationHandler.END

def main():
    TOKEN = os.getenv('BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ BOT_TOKEN no configurado!")
        return

    logger.info("🔧 Iniciando bot con menú principal...")

    try:
        bot = ExpenseBot()
        application = Application.builder().token(TOKEN).post_init(post_init).build()
        application.bot_data['bot'] = bot
        application.bot_data['menu_markup'] = menu_markup

        # --- Definición de Handlers de Conversación ---
        gasto_handler = ConversationHandler(
            entry_points=[CommandHandler('gasto', iniciar_gasto), MessageHandler(filters.Regex('^💸 Gasto$'), iniciar_gasto)],
            states={
                DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
                CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_categoria)],
                SUBCATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_subcategoria)],
                MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
                METODO_PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_metodo_pago_con_alerta)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        rapido_handler = ConversationHandler(
            entry_points=[CommandHandler('rapido', iniciar_gasto_rapido), MessageHandler(filters.Regex('^⚡ Rápido$'), iniciar_gasto_rapido)],
            states={
                GASTO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_gasto_rapido)],
                METODO_PAGO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_metodo_pago_rapido)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        ingreso_handler = ConversationHandler(
            entry_points=[CommandHandler('ingreso', iniciar_ingreso_rapido), MessageHandler(filters.Regex('^💰 Ingreso$'), iniciar_ingreso_rapido)],
            states={
                INGRESO_RAPIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_ingreso_rapido)],
                MONTO_INGRESO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_monto_ingreso)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        ahorro_handler = ConversationHandler(
            entry_points=[CommandHandler('ahorro', iniciar_ahorro), MessageHandler(filters.Regex('^💹 Ahorro$'), iniciar_ahorro)],
            states={
                MONTO_AHORRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto_ahorro)],
                DESTINO_AHORRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_destino_ahorro)],
                MONTO_DOLARES: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto_dolares)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        modo_handler = ConversationHandler(
            entry_points=[CommandHandler('modo', cambiar_modo)],
            states={CAMBIAR_MODO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_cambio_modo)]},
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        # --- Añadir Handlers a la Aplicación ---
        application.add_handler(gasto_handler)
        application.add_handler(rapido_handler)
        application.add_handler(ingreso_handler)
        application.add_handler(ahorro_handler)
        application.add_handler(modo_handler)
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", mostrar_menu))
        application.add_handler(CommandHandler("help", ayuda_extendida))
        
        application.add_handler(MessageHandler(filters.Regex('^📊 Resumen$'), generar_resumen))
        application.add_handler(MessageHandler(filters.Regex('^❓ Ayuda$'), ayuda_extendida))
        
        application.add_handler(CommandHandler("recordatorios", toggle_recordatorios))
        application.add_handler(CommandHandler("presupuesto", configurar_presupuesto))

        logger.info("🚀 Bot listo y corriendo...")
        application.run_polling()

    except Exception as e:
        logger.error(f"❌ Error al iniciar el bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()