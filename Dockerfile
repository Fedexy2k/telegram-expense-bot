FROM python:3.11-slim

WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Exponer el puerto (aunque no es necesario para bots de Telegram)
EXPOSE 8080

# Comando para ejecutar la aplicación
CMD ["python", "main.py"]