# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 14:10:05 2025

@author: federico.dean
"""
# handlers/resumen.py
import pandas as pd
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from datetime import datetime
import locale

async def generar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        chat_id = query.message.chat_id
    else:
        chat_id = update.message.chat_id

    bot = context.bot_data['bot']
    
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'es_AR.UTF-8')
        except locale.Error:
            pass
    
    await context.bot.send_message(chat_id=chat_id, text="📊 Analizando tus gastos... Un momento.")

    try:
        list_of_lists = bot.sheet_gastos.get_all_values()
        
        if len(list_of_lists) < 2:
            await context.bot.send_message(chat_id=chat_id, text="🤔 Aún no tienes gastos registrados.")
            return

        headers = list_of_lists.pop(0)
        df = pd.DataFrame(list_of_lists, columns=headers)
        
        df['Monto'] = df['Monto'].str.replace(',', '.', regex=False)
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce')
        
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y %H:%M')

        mes_actual = datetime.now().month
        año_actual = datetime.now().year
        df_mes_actual = df[(df['Fecha'].dt.month == mes_actual) & (df['Fecha'].dt.year == año_actual)]

        if df_mes_actual.empty:
            await context.bot.send_message(chat_id=chat_id, text="👍 ¡No tienes gastos registrados en lo que va del mes!")
            return

        resumen_por_categoria = df_mes_actual.groupby('Categoría')['Monto'].sum().sort_values(ascending=False)
        total_gastado = df_mes_actual['Monto'].sum()

        nombre_mes = datetime.now().strftime('%B').capitalize()
        mensaje = f"📊 *Resumen de Gastos de {nombre_mes}*\n\n"
        
        for categoria, monto in resumen_por_categoria.items():
            mensaje += f"_{categoria}_: `{bot.formatear_pesos(monto)}`\n"
        
        mensaje += "\n---------------------\n"
        mensaje += f"*Total Gastado:* `{bot.formatear_pesos(total_gastado)}`"
        mensaje += "\n\n*¿Qué más quieres hacer?*"

        keyboard = [
            [
                InlineKeyboardButton("Nuevo Gasto", callback_data="/gasto"),
                InlineKeyboardButton("Gasto Rápido", callback_data="/rapido"),
            ],
            [
                InlineKeyboardButton("Ver Resumen", callback_data="/resumen"),
                InlineKeyboardButton("Cambiar Modo", callback_data="/modo"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # --- LÍNEA CORREGIDA ---
        await context.bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Error al generar resumen: {e}")
        # --- LÍNEA CORREGIDA ---
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ ¡Ups! Hubo un error al generar tu resumen.\nError: {e}"
        )