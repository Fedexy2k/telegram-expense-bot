# bot.py
import logging
import gspread
import os
import json
import base64  # <--- IMPORTANTE
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

# Estados de la conversación
DESCRIPCION, CATEGORIA, MONTO, METODO_PAGO, GASTO_RAPIDO, METODO_PAGO_RAPIDO, CAMBIAR_MODO = range(7)

class ExpenseBot:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        if os.getenv('GOOGLE_CREDENTIALS'):
            # Decodifica la credencial desde Base64
            b64_creds = os.getenv('GOOGLE_CREDENTIALS')
            decoded_creds_json = base64.b64decode(b64_creds).decode('utf-8')
            creds_info = json.loads(decoded_creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            # Lógica para correr localmente
            SERVICE_ACCOUNT_FILE = 'credenciales.json'
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        self.SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
        self.gc = gspread.authorize(creds)
        spreadsheet = self.gc.open_by_key(self.SPREADSHEET_ID)
        self.sheet_gastos = spreadsheet.worksheet('Gastos')
        self.sheet_ingresos = spreadsheet.worksheet('Ingresos')
        self.sheet_topes = spreadsheet.worksheet('Topes')

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

        self.user_modes = {}
        self.personality_modes = {
            'estricto': {
                'name': '😤 Estricto',
                'messages': {
                    'start_gasto': "💸 ¿Otra vez gastando? ¡Necesitas controlar tus finanzas!",
                    'success_gasto': "✅ Gasto registrado. Espero que haya sido necesario.",
                }
            },
            'motivador': {
                'name': '💪 Motivador',
                'messages': {
                    'start_gasto': "💸 ¡Perfecto! Registremos este gasto.",
                    'success_gasto': "✅ ¡Excelente! ¡Sigue así!",
                }
            },
            'comprensivo': {
                'name': '🤗 Comprensivo',
                'messages': {
                    'start_gasto': "💸 Entiendo que a veces necesitamos gastar.",
                    'success_gasto': "✅ Perfecto, lo importante es que lo estés registrando.",
                }
            }
        }

    def formatear_pesos(self, monto):
        # Esta función ahora formatea los números al estilo argentino ($1.234,56)
        # 1. Formatea el número con separador de miles (,) y decimal (.)
        s = f"{monto:,.0f}"
        # 2. Intercambia los puntos por comas y viceversa
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"${s}"

    def guardar_gasto(self, descripcion, categoria, monto, metodo_pago):
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.sheet_gastos.append_row([fecha, descripcion, categoria, monto, metodo_pago])

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
