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

        self.categorias = {
            '🍖 Comida': ['🛒 Supermercado', '🍜 Chino', '🍑 Verduleria', '🥩 Carniceria', '🚲 Market', '🍱 Vianda'],
            '🏠 Casa': ['📦 Deco', '🔨 Ferreteria'],
            '🚗 Auto': ['⛽ Nafta', '🅿️ Estacionamiento', '🛡️ Seguro', '🔧Mantenimiento'],
            '🎈 Lujitos': ['🎮 Videojuegos', '📚 Libros', '🎬 Cine', '🍻 Birritas'],
            '💆‍♂️ Cuidados':['💊 Farmacia', '🍌 Nutri', '♿ Psico', '💇‍♂️ Peluqueria'],
            '☢ Excesos': ['🍟 Delivery', '🍫 Boludeces', '🥤 Coquita', '🥐 Panaderia'],
            '👕 Indumentaria': ['👔 Ropa', '👟 Zapatillas', '👓 Accesorios'],
        }

        self.metodos_pago = [
            ['💵 Efectivo', '🐕 Cuenta DNI'],
            ['🏦 BBVA Crédito', '🏦 BBVA Débito'],
            ['📱 Modo/MP', '💸 Transferencia']
        ]

        self.gastos_rapidos = {
            '☕ Café': {
                'descripcion': 'Café Facu', 
                'categoria': '🎈 Lujitos', 
                'subcategoria': '☕ Facultad', # <- NUEVO
                'monto': 1000
            },
            '☢ Coquita 175': {
                'descripcion': 'Coca-cola 175', 
                'categoria': '☢ Excesos', 
                'subcategoria': '🥤 Coquita', # <- NUEVO
                'monto': 2900
            },
            '☢ Coquita 225': {
                'descripcion': 'Coca-cola 225', 
                'categoria': '☢ Excesos', 
                'subcategoria': '🥤 Coquita', # <- NUEVO
                'monto': 4000
            },
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
                    'start_gasto': "💸 EY EY EY, ...ya arrancamos ?",
                    'success_gasto': "✅ Ya guarde el gasto. No nos pasemos de lo que planeamos.",
                    'budget_warning': "⚠️ ¡CUIDADO! Ya gastaste mucho en esta categoría.",
                    'budget_exceeded': "🚨 ¡LÍMITE SUPERADO! Afloja con la tarjeta que no llegamos a Japon.",
                }
            },
            'motivador': {
                'name': '💪 Motivador',
                'messages': {
                    'start_gasto': "💸 ¡Perfecto! Registremos este gasto.",
                    'success_gasto': "✅ ¡Excelente! Para hacer un habito hay que mantenerlo",
                    'budget_warning': "💪 Ojo, pensa cuidadosamente si necesitamos mas de esto.",
                    'budget_exceeded': "🎯 Superaste el límite, enfocate en otra cosa.",
                }
            },
            'comprensivo': {
                'name': '🤗 Comprensivo',
                'messages': {
                    'start_gasto': "💸 Ya fue, para algo trabajamos.",
                    'success_gasto': "✅ Perfecto, si esta registrado lo podemos modificar.",
                    'budget_warning': "🤗 Te aviso que ya gastamos bastante en esta categoría.",
                    'budget_exceeded': "😌 Superaste el presupuesto, a la verga.",
                }
            }
        }

        # Para almacenar chats que quieren recordatorios
        self.chat_recordatorios = set()

    def formatear_pesos(self, monto):
        s = f"{monto:,.0f}"
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"${s}"

    def guardar_gasto(self, descripcion, categoria, subcategoria, monto, metodo_pago):
        fecha = datetime.now().strftime("%d/%m/%Y")
        # El orden debe coincidir con tus columnas en Google Sheets
        self.sheet_gastos.append_row([fecha, descripcion, categoria, subcategoria, monto, metodo_pago])

    def guardar_ingreso(self, descripcion, categoria, monto):
        fecha = datetime.now().strftime("%d/%m/%Y")
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