# 1. Usar una imagen base oficial y ligera de Python
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar el archivo de dependencias primero
COPY requirements.txt .

# 4. Instalar las dependencias que definimos
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar todo el resto del código del proyecto al contenedor
COPY . .

# 6. Definir el comando que se ejecutará cuando el contenedor inicie
CMD ["python", "main.py"]