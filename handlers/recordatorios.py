# handlers/recordatorios.py
import asyncio
from datetime import datetime, time
from telegram import Update
from telegram.ext import ContextTypes
import pytz

class RecordatorioManager:
    def __init__(self, application):
        self.application = application
        self.timezone = pytz.timezone('America/Argentina/Buenos_Aires')
        self.recordatorios_activos = {}
        
    
    async def loop_recordatorios(self):
        """Loop principal para enviar recordatorios"""
        while True:
            await asyncio.sleep(60)  # Revisar cada minuto
            
            ahora = datetime.now(self.timezone)
            hora_actual = ahora.time()
            
            # Recordatorio de las 13:00
            if hora_actual.hour == 13 and hora_actual.minute == 0:
                await self.enviar_recordatorio_almuerzo()
            
            # Recordatorio de las 22:00
            if hora_actual.hour == 22 and hora_actual.minute == 0:
                await self.enviar_recordatorio_noche()
    
    async def enviar_recordatorio_almuerzo(self):
        """Envía recordatorio del mediodía"""
        bot = self.application.bot_data.get('bot')
        if not bot:
            return
            
        mensaje = (
            "🍽️ *Recordatorio del mediodía*\n\n"
            "¿Ya almorzaste? No olvides registrar tus gastos de la mañana.\n\n"
            "Usa: /gasto, /rapido, /ingreso"
        )
        
        for chat_id in bot.chat_recordatorios:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=mensaje,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error enviando recordatorio a {chat_id}: {e}")
    
    async def enviar_recordatorio_noche(self):
        """Envía recordatorio de la noche"""
        bot = self.application.bot_data.get('bot')
        if not bot:
            return
            
        mensaje = (
            "🌙 *Recordatorio nocturno*\n\n"
            "Antes de dormir, ¿registraste todos los gastos del día?\n\n"
            "Usa: /gasto, /rapido, /resumen"
        )
        
        for chat_id in bot.chat_recordatorios:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=mensaje,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error enviando recordatorio a {chat_id}: {e}")

# handlers/configuracion.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

async def toggle_recordatorios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa/desactiva recordatorios para el usuario"""
    bot = context.bot_data['bot']
    chat_id = update.effective_chat.id
    
    if chat_id in bot.chat_recordatorios:
        bot.remover_chat_recordatorio(chat_id)
        await update.message.reply_text(
            "🔕 Recordatorios desactivados.\n\n"
            "Para reactivarlos, usa /recordatorios"
        )
    else:
        bot.agregar_chat_recordatorio(chat_id)
        await update.message.reply_text(
            "🔔 ¡Recordatorios activados!\n\n"
            "Te recordaré registrar tus gastos a las 13:00 y 22:00.\n\n"
            "Para desactivarlos, usa /recordatorios nuevamente"
        )

async def configurar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra información sobre cómo configurar presupuestos"""
    mensaje = (
        "💰 *Configuración de Presupuestos*\n\n"
        "Para configurar alertas de presupuesto:\n\n"
        "1. Ve a tu Google Sheets\n"
        "2. En la hoja 'Topes', agrega:\n"
        "   • Categoría (ej: 🍖 Comida)\n"
        "   • Presupuesto (ej: 50000)\n\n"
        "3. El bot te alertará cuando gastes:\n"
        "   • 80% del presupuesto (advertencia)\n"
        "   • 100% del presupuesto (límite superado)\n\n"
        "Las alertas se personalizan según tu modo de personalidad."
    )
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')