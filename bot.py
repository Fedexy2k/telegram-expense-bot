# bot.py - Versión actualizada
import logging
import gspread
import os
import json
import base64
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
import asyncio

# Estados de la conversación
DESCRIPCION, CATEGORIA, MONTO, METODO_PAGO, GASTO_RAPIDO, METODO_PAGO_RAPIDO, CAMBIAR_MODO = range(7)
INGRESO_RAPIDO, MONTO_INGRESO = range(2)

class ExpenseBot:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        if os.getenv('GOOGLE_CREDENTIALS'):
            b64_creds = os.getenv('GOOGLE_CREDENTIALS')
            decoded_creds_json = base64.b64decode(b64_creds).decode('utf-8')
            creds_info = json.loads(decoded_creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            SERVICE_ACCOUNT_FILE = 'credenciales.json'
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        self.SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
        self.gc = gspread.authorize(creds)
        spreadsheet = self.gc.open_by_key(self.SPREADSHEET_ID)
        self.sheet_gastos = spreadsheet.worksheet('Gastos')
        self.sheet_ingresos = spreadsheet.worksheet('Ingresos')
        self.sheet_topes = spreadsheet.worksheet('Topes')
        self.sheet_presupuesto = spreadsheet.worksheet('Presupuesto')  # Nueva hoja

        self.categorias = [
            ['🍖 Comida', '🚗 Auto', '☕ Facultad'],
            ['🏠 Casa', '💊 Farmacia', '🍟 Delivery'],
            ['🍻 Salidas', '🎮 Gustos', '☢ Coca-Cola'],
            ['💵 Efectivo', '🍫 De Mas', '🍕 Comida Job'],
        ]

        self.metodos_pago = [['💵 Efectivo', '💳 Débito']]

        self.gastos_rapidos = {
            '☕ Café': {'descripcion': 'Café Facu', 'categoria': '☕ Facultad', 'monto': 1000},
            '☢ Coquita 175': {'descripcion': 'Coca-cola 175', 'categoria': '☢ Coca-Cola', 'monto': 2900},
            '☢ Coquita 225': {'descripcion': 'Coca-cola 225', 'categoria': '☢ Coca-Cola', 'monto': 3500},
        }

        # Nuevos ingresos rápidos
        self.ingresos_rapidos = {
            '💼 Sueldo': {'categoria': '💼 Trabajo'},
            '💰 Préstamo': {'categoria': '💰 Préstamo'},
            '🔄 Devolución': {'categoria': '🔄 Devolución'},
            '🎁 Regalo': {'categoria': '🎁 Regalo'},
            '💳 Reintegro': {'categoria': '💳 Reintegro'},
            '📈 Venta': {'categoria': '📈 Venta'},
        }

        self.user_modes = {}
        self.personality_modes = {
            'estricto': {
                'name': '😤 Estricto',
                'messages': {
                    'start_gasto': "💸 ¿Otra vez gastando? ¡Necesitas controlar tus finanzas!",
                    'success_gasto': "✅ Gasto registrado. Espero que haya sido necesario.",
                    'budget_warning': "⚠️ ¡CUIDADO! Ya gastaste mucho en esta categoría.",
                    'budget_exceeded': "🚨 ¡LÍMITE SUPERADO! Deberías parar de gastar en esto.",
                }
            },
            'motivador': {
                'name': '💪 Motivador',
                'messages': {
                    'start_gasto': "💸 ¡Perfecto! Registremos este gasto.",
                    'success_gasto': "✅ ¡Excelente! ¡Sigue así!",
                    'budget_warning': "💪 ¡Vas bien! Pero cuidado con esta categoría.",
                    'budget_exceeded': "🎯 Superaste el límite, pero sé que puedes controlarlo.",
                }
            },
            'comprensivo': {
                'name': '🤗 Comprensivo',
                'messages': {
                    'start_gasto': "💸 Entiendo que a veces necesitamos gastar.",
                    'success_gasto': "✅ Perfecto, lo importante es que lo estés registrando.",
                    'budget_warning': "🤗 Te aviso que ya gastaste bastante en esta categoría.",
                    'budget_exceeded': "😌 Superaste el presupuesto, pero todo está bien.",
                }
            }
        }

        # Para almacenar chats que quieren recordatorios
        self.chat_recordatorios = set()

    def formatear_pesos(self, monto):
        s = f"{monto:,.0f}"
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"${s}"

    def guardar_gasto(self, descripcion, categoria, monto, metodo_pago):
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.sheet_gastos.append_row([fecha, descripcion, categoria, monto, metodo_pago])

    def guardar_ingreso(self, descripcion, categoria, monto):
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.sheet_ingresos.append_row([fecha, descripcion, categoria, monto])

    async def actualizar_presupuesto(self, monto_ingreso):
        """Actualiza automáticamente el presupuesto con el nuevo ingreso"""
        try:
            # Buscar la celda del presupuesto total y actualizarla
            # Asumiendo que el presupuesto total está en una celda específica
            presupuesto_actual = self.sheet_presupuesto.cell(2, 2).value or 0
            nuevo_presupuesto = float(presupuesto_actual) + monto_ingreso
            self.sheet_presupuesto.update_cell(2, 2, nuevo_presupuesto)
        except Exception as e:
            print(f"Error actualizando presupuesto: {e}")

    def obtener_presupuesto_categoria(self, categoria):
        """Obtiene el presupuesto asignado para una categoría"""
        try:
            # Buscar en la hoja Topes el presupuesto para esta categoría
            registros = self.sheet_topes.get_all_records()
            for registro in registros:
                if registro.get('Categoría') == categoria:
                    return float(registro.get('Presupuesto', 0))
            return 0
        except:
            return 0

    def obtener_gastos_categoria_mes(self, categoria):
        """Obtiene el total gastado en una categoría este mes"""
        try:
            import pandas as pd
            list_of_lists = self.sheet_gastos.get_all_values()
            if len(list_of_lists) < 2:
                return 0
            
            headers = list_of_lists.pop(0)
            df = pd.DataFrame(list_of_lists, columns=headers)
            df['Monto'] = pd.to_numeric(df['Monto'].str.replace(',', '.'), errors='coerce')
            df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y %H:%M')
            
            mes_actual = datetime.now().month
            año_actual = datetime.now().year
            df_mes = df[(df['Fecha'].dt.month == mes_actual) & (df['Fecha'].dt.year == año_actual)]
            
            categoria_gastos = df_mes[df_mes['Categoría'] == categoria]['Monto'].sum()
            return categoria_gastos
        except:
            return 0

    async def verificar_presupuesto(self, categoria, user_id):
        """Verifica si se acerca o supera el presupuesto de una categoría"""
        presupuesto = self.obtener_presupuesto_categoria(categoria)
        if presupuesto == 0:
            return None
        
        gastado = self.obtener_gastos_categoria_mes(categoria)
        porcentaje = (gastado / presupuesto) * 100
        
        if porcentaje >= 100:
            return self.get_message(user_id, 'budget_exceeded')
        elif porcentaje >= 80:
            return self.get_message(user_id, 'budget_warning')
        
        return None

    def agregar_chat_recordatorio(self, chat_id):
        """Agrega un chat para recibir recordatorios"""
        self.chat_recordatorios.add(chat_id)

    def remover_chat_recordatorio(self, chat_id):
        """Remueve un chat de los recordatorios"""
        self.chat_recordatorios.discard(chat_id)

    def get_user_mode(self, user_id):
        return self.user_modes.get(user_id, 'comprensivo')

    def set_user_mode(self, user_id, mode):
        if mode in self.personality_modes:
            self.user_modes[user_id] = mode
            return True
        return False

    def get_message(self, user_id, message_key):
        mode = self.get_user_mode(user_id)
        return self.personality_modes[mode]['messages'].get(message_key, "")

    def get_mode_name(self, user_id):
        mode = self.get_user_mode(user_id)
        return self.personality_modes[mode]['name']