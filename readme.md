# Bot de Gastos Personales

Bot de Telegram para tracking de gastos personales con integración a Google Sheets.

## Funcionalidades

- ✅ Registro de gastos paso a paso
- ⚡ Gastos rápidos predefinidos
- 📊 Resúmenes mensuales con categorías
- 💳 Tracking de métodos de pago
- 🇦🇷 Formato de pesos argentinos

## Variables de Entorno Requeridas

- `BOT_TOKEN`: Token del bot de Telegram
- `GOOGLE_CREDENTIALS`: Credenciales de Google Service Account (JSON como string)
- `SPREADSHEET_ID`: ID de la Google Sheet

## Deploy en Railway

1. Fork este repo
2. Conectar con Railway
3. Configurar variables de entorno
4. Deploy automático

## Comandos

- `/start` - Iniciar bot
- `/gasto` - Registrar gasto
- `/rapido` - Gastos frecuentes
- `/resumen` - Ver resumen del mes
- `/help` - Ayuda