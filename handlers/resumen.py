# handlers/resumen.py
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import locale

async def generar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    bot = context.bot_data['bot']
    
    # ... (El código de locale se mantiene igual) ...
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'es_AR.UTF-8')
        except locale.Error:
            pass

    await context.bot.send_message(chat_id=chat_id, text="📊 Analizando tus gastos... Un momento.")

    try:
        ### MODIFICADO: Usamos el sistema de caché ###
        await bot._cargar_datos() # Aseguramos que los datos estén cargados
        df = bot.df_gastos

        if df is None or df.empty:
            await context.bot.send_message(chat_id=chat_id, text="🤔 Aún no tienes gastos registrados.")
            return

        mes_actual = datetime.now().month
        año_actual = datetime.now().year
        df_mes_actual = df[(df['Fecha'].dt.month == mes_actual) & (df['Fecha'].dt.year == año_actual)]

        if df_mes_actual.empty:
            await context.bot.send_message(chat_id=chat_id, text="👍 ¡No tienes gastos registrados en lo que va del mes!")
            return

        resumen_por_categoria = df_mes_actual.groupby('Categoría')['Monto'].sum().sort_values(ascending=False)
        total_gastado = df_mes_actual['Monto'].sum()

        # ... (El resto del código para generar el mensaje se mantiene igual) ...
        try:
            nombre_mes = datetime.now().strftime('%B').capitalize()
        except:
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            nombre_mes = meses[datetime.now().month - 1]

        mensaje = f"📊 *Resumen de Gastos de {nombre_mes}*\n\n"
        
        for categoria, monto in resumen_por_categoria.items():
            mensaje += f"_{categoria}_: `{bot.formatear_pesos(monto)}`\n"
        
        mensaje += "\n---------------------\n"
        mensaje += f"*Total Gastado:* `{bot.formatear_pesos(total_gastado)}`"
        mensaje += "\n\nPara continuar, usa: /gasto, /rapido, /resumen, /modo"
        
        await context.bot.send_message(chat_id=chat_id, text=mensaje, parse_mode='Markdown')

    except Exception as e:
        print(f"Error al generar resumen: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ ¡Ups! Hubo un error al generar tu resumen.\nError: {str(e)}"
        )
