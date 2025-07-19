from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

DESCRIPCION, CATEGORIA, SUBCATEGORIA, MONTO, METODO_PAGO = range(5)

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
    # Obtenemos las llaves (categorías principales) del diccionario
    categorias_principales = list(context.bot_data['bot'].categorias.keys())
    # Creamos el teclado en formato de lista de listas
    keyboard = [[cat] for cat in categorias_principales]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"📝 Descripción: {descripcion}\n\nMarca la categoría:",
        reply_markup=reply_markup
    )
    return CATEGORIA

async def recibir_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    categoria_seleccionada = update.message.text
    context.user_data['categoria'] = categoria_seleccionada

    # Obtenemos las subcategorías del diccionario en bot.py
    subcategorias = context.bot_data['bot'].categorias.get(categoria_seleccionada, [])

    if not subcategorias: # Si no hay subcategorías, se salta el paso
        await update.message.reply_text("💰 ¿Cerramos numeros varon?:", reply_markup=ReplyKeyboardRemove())
        return MONTO

    # Creamos el teclado para las subcategorías
    keyboard = [[sub] for sub in subcategorias]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"📂 Categoría: {categoria_seleccionada}\n\n"
        "Selecciona la subcategoría:",
        reply_markup=reply_markup
    )
    return SUBCATEGORIA

async def recibir_subcategoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['subcategoria'] = update.message.text

    await update.message.reply_text(
        f"📝 {context.user_data['descripcion']}\n"
        f"📂 {context.user_data['categoria']} -> {context.user_data['subcategoria']}\n\n"
        "💰 ¿Cuanto la jodita? (solo números):",
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

    # Obtenemos la lista de métodos válidos directamente desde el bot.py
    # Esto "aplana" la lista de listas en una sola lista para poder verificar.
    metodos_validos = [item for sublist in bot.metodos_pago for item in sublist]

    if metodo not in metodos_validos:
        reply_markup = ReplyKeyboardMarkup(bot.metodos_pago, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("❌ Método no válido. Seleccioná uno correcto:", reply_markup=reply_markup)
        return METODO_PAGO

    desc = context.user_data['descripcion']
    cat = context.user_data['categoria']
    subcat = context.user_data.get('subcategoria', '') # Obtenemos la subcategoría
    monto = context.user_data['monto']

    bot.guardar_gasto(desc, cat, subcat, monto, metodo)
    fecha = datetime.now().strftime("%d/%m/%Y")
    mensaje_personalizado = bot.get_message(user_id, 'success_gasto')

    # Mensaje final SIN botones
    texto_final = (
        f"✅ ¡Gasto registrado!\n\n"
        f"📅 {fecha}\n📝 {desc}\n📂 {cat} -> {subcat}\n💰 {bot.formatear_pesos(monto)}\n💳 {metodo}\n\n"
        f"{mensaje_personalizado}\n\n"
        "Para continuar, usa: /gasto, /rapido, /resumen, /modo"
    )
    await update.message.reply_text(texto_final, reply_markup=ReplyKeyboardRemove())
    
    context.user_data.clear()
    return ConversationHandler.END
