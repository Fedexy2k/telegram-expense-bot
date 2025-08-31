# handlers/ingresos.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

# --- LÍNEA CORREGIDA ---
# Los estados ahora coinciden con los definidos en main.py
(INGRESO_RAPIDO, MONTO_INGRESO) = range(7, 9)

async def iniciar_ingreso_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    bot = context.bot_data['bot']
    keyboard = []
    temp_row = []

    for key, ingreso in bot.ingresos_rapidos.items():
        temp_row.append(f"{key}")
        if len(temp_row) == 2:
            keyboard.append(temp_row)
            temp_row = []

    if temp_row:
        keyboard.append(temp_row)
    keyboard.append(['❌ Cancelar'])

    await update.message.reply_text(
        "💰 *Ingresos Rápidos*\n\nSelecciona el tipo de ingreso:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return INGRESO_RAPIDO

async def procesar_ingreso_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    seleccion = update.message.text
    bot = context.bot_data['bot']
    menu_markup = context.bot_data.get('menu_markup')

    if seleccion == '❌ Cancelar':
        await update.message.reply_text("❌ Operación cancelada.", reply_markup=menu_markup)
        return ConversationHandler.END

    if seleccion in bot.ingresos_rapidos:
        context.user_data['tipo_ingreso'] = seleccion
        context.user_data['categoria_ingreso'] = bot.ingresos_rapidos[seleccion]['categoria']
        
        await update.message.reply_text(
            f"💰 {seleccion}\n\n¿Cuánto recibiste? (solo números):",
            reply_markup=ReplyKeyboardRemove()
        )
        return MONTO_INGRESO
    else:
        await update.message.reply_text("❌ Selección no válida. Intenta de nuevo.", reply_markup=menu_markup)
        return ConversationHandler.END

async def procesar_monto_ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(update.message.text.replace(',', '.'))
        bot = context.bot_data['bot']
        menu_markup = context.bot_data.get('menu_markup')
        
        tipo_ingreso = context.user_data['tipo_ingreso']
        categoria = context.user_data['categoria_ingreso']
        
        await bot.guardar_ingreso(tipo_ingreso, categoria, monto)
        
        # await bot.actualizar_presupuesto(monto) # Comentado por ahora
        
        fecha = datetime.now().strftime("%d/%m/%Y")
        
        texto_final = (
            f"✅ ¡Ingreso registrado!\n\n"
            f"📅 {fecha}\n💰 {tipo_ingreso}\n📂 {categoria}\n"
            f"💵 {bot.formatear_pesos(monto)}\n\n"
            "Para continuar, usa /menu o elige una opción."
        )
        await update.message.reply_text(texto_final, reply_markup=menu_markup)
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Por favor ingresá un número válido. Ejemplo: 1500 o 1500.50")
        return MONTO_INGRESO