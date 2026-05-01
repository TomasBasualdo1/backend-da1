# 1. Usar una imagen oficial y liviana de Python 3.12
FROM python:3.12-slim

# 2. Configurar variables de entorno para evitar prompts interactivos y aceptar términos
ENV DEBIAN_FRONTEND=noninteractive
ENV ACCEPT_EULA=Y

# 3. Instalar herramientas del sistema necesarias para compilar y descargar
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Agregar la clave y el repositorio oficial de Microsoft para Debian 12 (Bookworm)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list

# 5. Instalar el driver ODBC 18 para SQL Server
RUN apt-get update && apt-get install -y msodbcsql18 && rm -rf /var/lib/apt/lists/*

# 6. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 7. Copiar el archivo de dependencias e instalarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 8. Copiar el resto del código del proyecto
COPY . .

# 9. Iniciar FastAPI usando Uvicorn. 
# Render inyecta la variable $PORT dinámicamente, por lo que usamos este formato:
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"