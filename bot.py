# bot.py - Versión con Caching
import logging
import gspread
import os
import json
import base64
import pandas as pd
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
import asyncio

# (El resto de las constantes de estados se mantienen igual)

class ExpenseBot:
    def __init__(self):
        # ... (La configuración de credenciales de Google se mantiene igual) ...
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
        self.sheet_presupuesto = spreadsheet.worksheet('Presupuesto')

        ### NUEVO: Atributos para el caché ###
        self.df_gastos = None
        self.df_topes = None
        # Un 'lock' para evitar que se carguen los datos varias veces al mismo tiempo
        self._lock = asyncio.Lock()


        # ... (Toda la configuración de categorías, métodos de pago, etc., se mantiene igual) ...
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
        # (El resto de diccionarios como gastos_rapidos, ingresos_rapidos, user_modes, etc., se mantienen igual)
        self.gastos_rapidos = {
            '☕ Café': {'descripcion': 'Café Facu', 'categoria': '🎈 Lujitos', 'subcategoria': '☕ Facultad', 'monto': 1000},
            '☢ Coquita 175': {'descripcion': 'Coca-cola 175', 'categoria': '☢ Excesos', 'subcategoria': '🥤 Coquita', 'monto': 2900},
            '☢ Coquita 225': {'descripcion': 'Coca-cola 225', 'categoria': '☢ Excesos', 'subcategoria': '🥤 Coquita', 'monto': 4000},
        }
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
        self.chat_recordatorios = set()

    ### NUEVO: Método central para cargar y cachear los datos ###
    async def _cargar_datos(self, forzar_recarga: bool = False):
        async with self._lock:
            if forzar_recarga or self.df_gastos is None:
                logging.info("Recargando datos de Gastos desde Google Sheets...")
                list_of_lists = self.sheet_gastos.get_all_values()
                if len(list_of_lists) > 1:
                    headers = list_of_lists.pop(0)
                    self.df_gastos = pd.DataFrame(list_of_lists, columns=headers)
                    # Convertir tipos de datos para cálculos correctos
                    self.df_gastos['Monto'] = self.df_gastos['Monto'].str.replace(',', '.', regex=False)
                    self.df_gastos['Monto'] = pd.to_numeric(self.df_gastos['Monto'], errors='coerce')
                    self.df_gastos['Fecha'] = pd.to_datetime(self.df_gastos['Fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
                else:
                    self.df_gastos = pd.DataFrame() # DataFrame vacío si no hay datos

            if forzar_recarga or self.df_topes is None:
                logging.info("Recargando datos de Topes desde Google Sheets...")
                records = self.sheet_topes.get_all_records()
                self.df_topes = pd.DataFrame(records)


    def formatear_pesos(self, monto):
        s = f"{monto:,.0f}"
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"${s}"

    ### MODIFICADO: Ahora fuerza una recarga del caché después de guardar ###
    async def guardar_gasto(self, descripcion, categoria, subcategoria, monto, metodo_pago):
        fecha = datetime.now().strftime("%d/%m/%Y")
        self.sheet_gastos.append_row([fecha, descripcion, categoria, subcategoria, monto, metodo_pago])
        await self._cargar_datos(forzar_recarga=True) # Forzamos la recarga

    ### MODIFICADO: Ahora fuerza una recarga del caché después de guardar ###
    async def guardar_ingreso(self, descripcion, categoria, monto):
        fecha = datetime.now().strftime("%d/%m/%Y")
        self.sheet_ingresos.append_row([fecha, descripcion, categoria, monto])
        # Podríamos implementar caché para ingresos también si fuera necesario en el futuro

    async def actualizar_presupuesto(self, monto_ingreso):
        # ... (Esta función se mantiene igual) ...
        try:
            presupuesto_actual_str = self.sheet_presupuesto.cell(2, 2).value or "0"
            presupuesto_actual = float(presupuesto_actual_str.replace('.', '').replace(',', '.'))
            nuevo_presupuesto = presupuesto_actual + monto_ingreso
            self.sheet_presupuesto.update_cell(2, 2, nuevo_presupuesto)
        except Exception as e:
            print(f"Error actualizando presupuesto: {e}")

    ### MODIFICADO: Ahora usa el DataFrame de caché ###
    async def obtener_presupuesto_categoria(self, categoria: str) -> float:
        await self._cargar_datos() # Asegura que los datos estén cargados
        if self.df_topes is None or self.df_topes.empty:
            return 0.0

        presupuesto = self.df_topes[self.df_topes['Categoría'] == categoria]
        if not presupuesto.empty:
            return float(presupuesto['Presupuesto'].iloc[0])
        return 0.0

    ### MODIFICADO: Ahora usa el DataFrame de caché ###
    async def obtener_gastos_categoria_mes(self, categoria: str) -> float:
        await self._cargar_datos() # Asegura que los datos estén cargados
        if self.df_gastos is None or self.df_gastos.empty:
            return 0.0

        mes_actual = datetime.now().month
        año_actual = datetime.now().year
        
        # Filtramos el DataFrame por mes, año y categoría
        df_mes_actual = self.df_gastos[
            (self.df_gastos['Fecha'].dt.month == mes_actual) &
            (self.df_gastos['Fecha'].dt.year == año_actual)
        ]
        
        gastos_categoria = df_mes_actual[df_mes_actual['Categoría'] == categoria]
        return gastos_categoria['Monto'].sum()

    ### MODIFICADO: Ahora usa las funciones asíncronas ###
    async def verificar_presupuesto(self, categoria, user_id):
        presupuesto = await self.obtener_presupuesto_categoria(categoria)
        if presupuesto == 0:
            return None
        
        gastado = await self.obtener_gastos_categoria_mes(categoria)
        porcentaje = (gastado / presupuesto) * 100
        
        if porcentaje >= 100:
            return self.get_message(user_id, 'budget_exceeded')
        elif porcentaje >= 80:
            return self.get_message(user_id, 'budget_warning')
        
        return None

    # (El resto de funciones como agregar_chat_recordatorio, get_user_mode, etc., se mantienen igual)
    def agregar_chat_recordatorio(self, chat_id):
        self.chat_recordatorios.add(chat_id)
    def remover_chat_recordatorio(self, chat_id):
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
