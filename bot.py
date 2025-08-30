# bot.py - Versión Final Fase 1 (con config.json)
import logging
import gspread
import os
import json # <--- Importante: agregamos la librería json
import base64
import pandas as pd
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
import asyncio

class ExpenseBot:
    def __init__(self):
        # --- Carga la configuración desde config.json ---
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logging.error("¡ERROR! No se encontró el archivo config.json.")
            self.config = {} # Usar config vacía para evitar que el bot crashee
        except json.JSONDecodeError:
            logging.error("¡ERROR! El archivo config.json tiene un formato incorrecto.")
            self.config = {}

        # --- Configuración de Credenciales de Google ---
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        if os.getenv('GOOGLE_CREDENTIALS'):
            b64_creds = os.getenv('GOOGLE_CREDENTIALS')
            decoded_creds_json = base64.b64decode(b64_creds).decode('utf-8')
            creds_info = json.loads(decoded_creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            SERVICE_ACCOUNT_FILE = 'credenciales.json'
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        # --- Conexión con Google Sheets ---
        self.SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
        self.gc = gspread.authorize(creds)
        spreadsheet = self.gc.open_by_key(self.SPREADSHEET_ID)
        self.sheet_gastos = spreadsheet.worksheet('Gastos')
        self.sheet_ingresos = spreadsheet.worksheet('Ingresos')
        self.sheet_presupuesto_bot = spreadsheet.worksheet('PresupuestoBot')

        # --- Atributos para el Caché ---
        self.df_gastos = None
        self.df_presupuesto = None
        self._lock = asyncio.Lock()

        # --- Definiciones del Bot (cargadas desde config.json) ---
        self.categorias = self.config.get('categorias', {})
        self.metodos_pago = self.config.get('metodos_pago', [])
        self.gastos_rapidos = self.config.get('gastos_rapidos', {})
        self.ingresos_rapidos = self.config.get('ingresos_rapidos', {})
        self.personality_modes = self.config.get('personality_modes', {})
        
        self.user_modes = {}
        self.chat_recordatorios = set()

    # --- El resto del código permanece exactamente igual ---

    async def _cargar_datos(self, forzar_recarga: bool = False):
        async with self._lock:
            if forzar_recarga or self.df_gastos is None:
                logging.info("Recargando datos de Gastos desde Google Sheets...")
                list_of_lists = self.sheet_gastos.get_all_values()
                if len(list_of_lists) > 1:
                    headers = list_of_lists.pop(0)
                    self.df_gastos = pd.DataFrame(list_of_lists, columns=headers)
                    self.df_gastos['Monto'] = self.df_gastos['Monto'].str.replace(',', '.', regex=False)
                    self.df_gastos['Monto'] = pd.to_numeric(self.df_gastos['Monto'], errors='coerce')
                    self.df_gastos['Fecha'] = pd.to_datetime(self.df_gastos['Fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
                else:
                    self.df_gastos = pd.DataFrame(columns=['Fecha', 'Descripcion', 'Categoría', 'Subcategoría', 'Monto', 'Metodo_Pago'])

            if forzar_recarga or self.df_presupuesto is None:
                logging.info("Recargando datos de PresupuestoBot desde Google Sheets...")
                records = self.sheet_presupuesto_bot.get_all_records()
                self.df_presupuesto = pd.DataFrame(records)

    def formatear_pesos(self, monto):
        s = f"{monto:,.0f}"
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"${s}"

    async def guardar_gasto(self, descripcion, categoria, subcategoria, monto, metodo_pago):
        fecha = datetime.now().strftime("%d/%m/%Y")
        self.sheet_gastos.append_row([fecha, descripcion, categoria, subcategoria, monto, metodo_pago])
        await self._cargar_datos(forzar_recarga=True)

    async def guardar_ingreso(self, descripcion, categoria, monto):
        fecha = datetime.now().strftime("%d/%m/%Y")
        self.sheet_ingresos.append_row([fecha, descripcion, categoria, monto])

    async def obtener_presupuesto_categoria(self, categoria_o_subcategoria: str) -> float:
        await self._cargar_datos()
        if self.df_presupuesto is None or self.df_presupuesto.empty or not categoria_o_subcategoria:
            return 0.0

        presupuesto_fila = self.df_presupuesto[self.df_presupuesto['Categoria'] == categoria_o_subcategoria]
        
        if not presupuesto_fila.empty:
            return float(presupuesto_fila['Presupuesto'].iloc[0])
        return 0.0

    async def verificar_presupuesto(self, categoria, subcategoria, user_id):
        presupuesto = await self.obtener_presupuesto_categoria(subcategoria)
        categoria_a_verificar = subcategoria

        if not presupuesto and categoria:
            presupuesto = await self.obtener_presupuesto_categoria(categoria)
            categoria_a_verificar = categoria
        
        if not presupuesto:
            return None

        gastado = 0
        await self._cargar_datos()
        if self.df_gastos is not None and not self.df_gastos.empty:
            mes_actual = datetime.now().month
            año_actual = datetime.now().year
            df_mes_actual = self.df_gastos[
                (self.df_gastos['Fecha'].dt.month == mes_actual) &
                (self.df_gastos['Fecha'].dt.year == año_actual)
            ]
            
            if categoria_a_verificar == subcategoria:
                gastos_filtrados = df_mes_actual[df_mes_actual['Subcategoría'] == subcategoria]
                gastado = gastos_filtrados['Monto'].sum()
            else:
                gastos_filtrados = df_mes_actual[df_mes_actual['Categoría'] == categoria]
                gastado = gastos_filtrados['Monto'].sum()

        if presupuesto > 0:
            porcentaje = (gastado / presupuesto) * 100
        else:
            porcentaje = 0
        
        mensaje_alerta = ""
        if porcentaje >= 100:
            mensaje_alerta = self.get_message(user_id, 'budget_exceeded')
        elif porcentaje >= 80:
            mensaje_alerta = self.get_message(user_id, 'budget_warning')
        
        if mensaje_alerta:
            return f"*{categoria_a_verificar}:* {mensaje_alerta}"

        return None
    
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

