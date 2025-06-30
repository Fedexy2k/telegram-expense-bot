from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

CAMBIAR_MODO = 6

async def cambiar_modo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        chat_id = query.message.chat_id
        user_id = query.from_user.id
    else:
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        
    bot = context.bot_data['bot']
    modo_actual = bot.get_user_mode(user_id)
    nombre_actual = bot.get_mode_name(user_id)

    keyboard = []
    for mode_key, mode_data in bot.personality_modes.items():
        prefix = "✅ " if mode_key == modo_actual else ""
        keyboard.append([f"{prefix}{mode_data['name']}"])
    keyboard.append(['❌ Cancelar'])

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎭 *Cambio de Personalidad*\n\nModo actual: {nombre_actual}\n\nSelecciona tu nuevo modo:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return CAMBIAR_MODO

async def procesar_cambio_modo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    seleccion = update.message.text
    bot = context.bot_data['bot']
    user_id = update.effective_user.id

    if seleccion == '❌ Cancelar':
        await update.message.reply_text("❌ Cambio de modo cancelado.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    modo_seleccionado = None
    for mode_key, mode_data in bot.personality_modes.items():
        if mode_data['name'] in seleccion:
            modo_seleccionado = mode_key
            break

    if not modo_seleccionado:
        await update.message.reply_text("❌ Selección no válida. Usa /modo para intentar de nuevo.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    bot.set_user_mode(user_id, modo_seleccionado)
    nuevo_nombre = bot.get_mode_name(user_id)

    confirmaciones = {
        'estricto': "😤 ¡Perfecto! Seré más estricto contigo. A ahorrar.",
        'motivador': "💪 ¡Excelente! Vamos por tus metas financieras.",
        'comprensivo': "🤗 Genial, estaré para acompañarte sin presiones."
    }

    await update.message.reply_text(
        f"✅ *Modo cambiado exitosamente*\n\nNuevo modo: {nuevo_nombre}\n\n{confirmaciones[modo_seleccionado]}",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
