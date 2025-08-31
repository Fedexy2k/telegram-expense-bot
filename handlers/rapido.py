# handlers/rapido.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

# --- LÍNEA CORREGIDA ---
# Los estados ahora coinciden con los definidos en main.py
(GASTO_RAPIDO, METODO_PAGO_RAPIDO) = range(5, 7)

async def iniciar_gasto_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    bot = context.bot_data['bot']
    keyboard = []
    temp_row = []

    for key, gasto in bot.gastos_rapidos.items():
        temp_row.append(f"{key} {bot.formatear_pesos(gasto['monto'])}")
        if len(temp_row) == 2:
            keyboard.append(temp_row)
            temp_row = []

    if temp_row:
        keyboard.append(temp_row)
    keyboard.append(['❌ Cancelar'])

    await update.message.reply_text(
        "⚡ *Gastos rápidos*\n\nSelecciona un gasto frecuente para registrarlo:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return GASTO_RAPIDO

async def procesar_gasto_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    seleccion = update.message.text
    bot = context.bot_data['bot']
    menu_markup = context.bot_data.get('menu_markup')

    if seleccion == '❌ Cancelar':
        await update.message.reply_text("❌ Operación cancelada.", reply_markup=menu_markup)
        return ConversationHandler.END

    for key, gasto in bot.gastos_rapidos.items():
        if seleccion.startswith(key):
            context.user_data['gasto_rapido'] = gasto
            break
    else:
        await update.message.reply_text("❌ Selección no válida. Intenta de nuevo.", reply_markup=menu_markup)
        return ConversationHandler.END

    reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("💳 ¿Cómo pagaste?", reply_markup=reply_markup)
    return METODO_PAGO_RAPIDO

async def procesar_metodo_pago_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metodo = update.message.text
    bot = context.bot_data['bot']
    gasto = context.user_data.get('gasto_rapido')
    menu_markup = context.bot_data.get('menu_markup')
    
    metodos_validos = [item for sublist in bot.metodos_pago for item in sublist]
    if metodo not in metodos_validos:
        reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("❌ Método no válido. Seleccioná uno correcto:", reply_markup=reply_markup)
        return METODO_PAGO_RAPIDO

    await bot.guardar_gasto(
        gasto['descripcion'],
        gasto['categoria'],
        gasto['subcategoria'],
        gasto['monto'],
        metodo
    )

    fecha = datetime.now().strftime("%d/%m/%Y")
    texto_final = (
        f"⚡ ¡Gasto rápido registrado!\n\n"
        f"📅 {fecha}\n📝 {gasto['descripcion']}\n📂 {gasto['categoria']} -> {gasto['subcategoria']}\n"
        f"💰 {bot.formatear_pesos(gasto['monto'])}\n💳 {metodo}\n\n"
        "Para continuar, usa /menu o elige una opción."
    )
    await update.message.reply_text(texto_final, reply_markup=menu_markup)

    context.user_data.clear()
    return ConversationHandler.END
