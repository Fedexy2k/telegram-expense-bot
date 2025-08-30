# handlers/ahorro.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

# Estados de la conversación
MONTO_AHORRO, DESTINO_AHORRO, MONTO_DOLARES = range(10, 13)

async def iniciar_ahorro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación para registrar un ahorro."""
    await update.message.reply_text(
        "💰 ¡Vamos a registrar un ahorro!\n\n"
        "¿Cuánto dinero (en pesos) ahorraste?",
        reply_markup=ReplyKeyboardRemove()
    )
    return MONTO_AHORRO

async def recibir_monto_ahorro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto en pesos y pregunta el destino."""
    try:
        monto = float(update.message.text.replace(',', '.'))
        context.user_data['monto_pesos'] = monto
        
        keyboard = [
            ['💵 Guardé Pesos', '📈 Compré Dólares'],
            ['🏦 Invertí (PF, FCI, etc.)', 'Otro'],
            ['❌ Cancelar']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Perfecto. Ahorraste {context.bot_data['bot'].formatear_pesos(monto)}.\n\n"
            "✅ ¿Qué hiciste con ese ahorro?",
            reply_markup=reply_markup
        )
        return DESTINO_AHORRO
        
    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido.")
        return MONTO_AHORRO

async def recibir_destino_ahorro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el destino y actúa en consecuencia."""
    destino = update.message.text
    context.user_data['destino'] = destino
    
    # --- MODIFICADO: Agregamos el menú al mensaje final ---
    # Obtenemos el teclado del menú desde el contexto principal
    menu_markup = context.bot_data.get('menu_markup')
    
    if destino == '📈 Compré Dólares':
        await update.message.reply_text(
            "💵 ¡Genial! ¿Cuántos dólares compraste? (solo el número)",
            reply_markup=ReplyKeyboardRemove()
        )
        return MONTO_DOLARES
    else:
        bot = context.bot_data['bot']
        await bot.guardar_ahorro(
            monto_pesos=context.user_data['monto_pesos'],
            destino=destino
        )
        
        texto_final = (
            f"✅ ¡Ahorro registrado!\n\n"
            f"💰 {bot.formatear_pesos(context.user_data['monto_pesos'])}\n"
            f"🎯 Destino: {destino}\n\n"
            "Para continuar, usa /menu o elige una opción."
        )
        await update.message.reply_text(texto_final, reply_markup=menu_markup)
        context.user_data.clear()
        return ConversationHandler.END

async def recibir_monto_dolares(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto en dólares, guarda todo y termina."""
    try:
        monto_dolares = float(update.message.text.replace(',', '.'))
        bot = context.bot_data['bot']
        
        await bot.guardar_ahorro(
            monto_pesos=context.user_data['monto_pesos'],
            destino=context.user_data['destino'],
            monto_dolares=monto_dolares
        )
        
        cotizacion = context.user_data['monto_pesos'] / monto_dolares
        
        # --- MODIFICADO: Agregamos el menú al mensaje final ---
        menu_markup = context.bot_data.get('menu_markup')
        
        texto_final = (
            f"✅ ¡Ahorro en dólares registrado!\n\n"
            f"💰 {bot.formatear_pesos(context.user_data['monto_pesos'])}\n"
            f"💵 US$ {monto_dolares:,.2f}\n"
            f"📊 Cotización implícita: ${cotizacion:,.2f}\n\n"
            "Para continuar, usa /menu o elige una opción."
        )
        await update.message.reply_text(texto_final, reply_markup=menu_markup)
        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido para los dólares.")
        return MONTO_DOLARES