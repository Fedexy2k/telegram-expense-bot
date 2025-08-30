# handlers/ahorro.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

# Definimos los estados de la conversación
MONTO_AHORRO, DESTINO_AHORRO, MONTO_DOLARES = range(10, 13) # Usamos números altos para no superponer

async def iniciar_ahorro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación para registrar un ahorro."""
    await update.message.reply_text(
        "💰 ¡Dale papá a registrar un ahorro!\n\n"
        "¿Cuánta plata (en pesos) ahorramos?",
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
            "✅ ¿Donde pusimos ese ahorro?",
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
    
    if destino == '📈 Compré Dólares':
        await update.message.reply_text(
            "💵 ¡Genial! ¿Cuántos verdolagas compramos? (solo el número)",
            reply_markup=ReplyKeyboardRemove()
        )
        return MONTO_DOLARES
    else:
        # Para cualquier otra opción, guardamos y terminamos
        bot = context.bot_data['bot']
        await bot.guardar_ahorro(
            monto_pesos=context.user_data['monto_pesos'],
            destino=destino
        )
        
        texto_final = (
            f"✅ ¡Ahorro registrado!\n\n"
            f"💰 {bot.formatear_pesos(context.user_data['monto_pesos'])}\n"
            f"🎯 Destino: {destino}"
        )
        await update.message.reply_text(texto_final, reply_markup=ReplyKeyboardRemove())
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
        
        texto_final = (
            f"✅ ¡Ahorro en verdes registrado!\n\n"
            f"💰 {bot.formatear_pesos(context.user_data['monto_pesos'])}\n"
            f"💵 US$ {monto_dolares:,.2f}\n"
            f"📊 Cotización : ${cotizacion:,.2f}"
        )
        await update.message.reply_text(texto_final, reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Por favor, ingresa un número válido para los dólares.")
        return MONTO_DOLARES