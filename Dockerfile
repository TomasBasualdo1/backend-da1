# 1. Usar una imagen oficial y liviana de Python 3.12
FROM python:3.12-slim

# 2. Configurar variables de entorno
ENV DEBIAN_FRONTEND=noninteractive

# 3. Instalar herramientas básicas
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 7. Copiar el archivo de dependencias e instalarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 8. Copiar el resto del código del proyecto
COPY . .

# 9. Iniciar FastAPI usando Uvicorn. 
# Render inyecta la variable $PORT dinámicamente, por lo que usamos este formato:
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"