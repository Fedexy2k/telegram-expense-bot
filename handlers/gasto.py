from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

DESCRIPCION, CATEGORIA, MONTO, METODO_PAGO = range(4)

async def iniciar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    bot = context.bot_data['bot']
    mensaje_personalizado = bot.get_message(user_id, 'start_gasto')

    await update.message.reply_text(
        f"{mensaje_personalizado}\n\nIngresa una descripción para tu gasto:",
        reply_markup=ReplyKeyboardRemove()
    )
    return DESCRIPCION

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    descripcion = update.message.text
    context.user_data['descripcion'] = descripcion
    reply_markup = ReplyKeyboardMarkup(context.bot_data['bot'].categorias, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"📝 Descripción: {descripcion}\n\nMarca la categoría:",
        reply_markup=reply_markup
    )
    return CATEGORIA

async def recibir_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    categoria = update.message.text
    context.user_data['categoria'] = categoria

    await update.message.reply_text(
        f"📝 Descripción: {context.user_data['descripcion']}\n"
        f"📂 Categoría: {categoria}\n\n"
        "💰 ¿Cuánto gastaste? (solo números):",
        reply_markup=ReplyKeyboardRemove()
    )
    return MONTO

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        monto = float(update.message.text.replace(',', '.'))
        context.user_data['monto'] = monto

        reply_markup = ReplyKeyboardMarkup(context.bot_data['bot'].metodos_pago, one_time_keyboard=True, resize_keyboard=True)

        await update.message.reply_text(
            f"📝 {context.user_data['descripcion']}\n"
            f"📂 {context.user_data['categoria']}\n"
            f"💰 Monto: {context.bot_data['bot'].formatear_pesos(monto)}\n\n"
            "💳 ¿Cómo pagaste?",
            reply_markup=reply_markup
        )
        return METODO_PAGO

    except ValueError:
        await update.message.reply_text("❌ Por favor ingresá un número válido. Ejemplo: 1500 o 1500.50")
        return MONTO

async def recibir_metodo_pago(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    metodo = update.message.text
    bot = context.bot_data['bot']
    user_id = update.effective_user.id

    if metodo not in ['💵 Efectivo', '💳 Débito']:
        reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("❌ Método no válido. Seleccioná uno correcto:", reply_markup=reply_markup)
        return METODO_PAGO

    desc = context.user_data['descripcion']
    cat = context.user_data['categoria']
    monto = context.user_data['monto']

    bot.guardar_gasto(desc, cat, monto, metodo)
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    mensaje_personalizado = bot.get_message(user_id, 'success_gasto')

    # Mensaje final SIN botones
    texto_final = (
        f"✅ ¡Gasto registrado!\n\n"
        f"📅 {fecha}\n📝 {desc}\n📂 {cat}\n💰 {bot.formatear_pesos(monto)}\n💳 {metodo}\n\n"
        f"{mensaje_personalizado}\n\n"
        "Para continuar, usa: /gasto, /rapido, /resumen, /modo"
    )
    await update.message.reply_text(texto_final, reply_markup=ReplyKeyboardRemove())
    
    context.user_data.clear()
    return ConversationHandler.END
