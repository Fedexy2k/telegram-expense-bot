from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

GASTO_RAPIDO, METODO_PAGO_RAPIDO = range(2)

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

    if seleccion == '❌ Cancelar':
        await update.message.reply_text("❌ Operación cancelada.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    for key, gasto in bot.gastos_rapidos.items():
        if seleccion.startswith(key):
            context.user_data['gasto_rapido'] = gasto
            break
    else:
        await update.message.reply_text("❌ Selección no válida. Intenta de nuevo con /rapido", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("💳 ¿Cómo pagaste?", reply_markup=reply_markup)
    return METODO_PAGO_RAPIDO

async def procesar_metodo_pago_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metodo = update.message.text
    bot = context.bot_data['bot']
    gasto = context.user_data.get('gasto_rapido')

    metodos_validos = [item for sublist in bot.metodos_pago for item in sublist]
    if metodo not in metodos_validos:
        reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("❌ Método no válido. Seleccioná uno correcto:", reply_markup=reply_markup)
        return METODO_PAGO_RAPIDO

    # --- INICIO DE LA CORRECCIÓN ---
    # Ahora pasamos la subcategoría desde el diccionario del gasto rápido
    bot.guardar_gasto(
        gasto['descripcion'],
        gasto['categoria'],
        gasto['subcategoria'], # <- AHORA SÍ LA USAMOS
        gasto['monto'],
        metodo
    )
    # --- FIN DE LA CORRECCIÓN ---

    fecha = datetime.now().strftime("%d/%m/%Y")

    texto_final = (
        f"⚡ ¡Gasto rápido registrado!\n\n"
        f"📅 {fecha}\n📝 {gasto['descripcion']}\n📂 {gasto['categoria']} -> {gasto['subcategoria']}\n"
        f"💰 {bot.formatear_pesos(gasto['monto'])}\n💳 {metodo}\n\n"
        "Para continuar, usa: /gasto, /rapido, /resumen, /modo"
    )
    await update.message.reply_text(texto_final, reply_markup=ReplyKeyboardRemove())

    context.user_data.clear()
    return ConversationHandler.END
