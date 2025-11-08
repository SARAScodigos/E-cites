# 1. Empezamos desde una "caja" oficial que ya tiene Python
FROM python:3.11-slim

# 2. Establecemos un directorio de trabajo dentro de la "caja"
WORKDIR /app

# 3. Copiamos tu archivo de requisitos (requirements.txt)
# Lo hacemos primero por una optimización de caché de Docker
COPY requirements.txt .

# 4. Instalamos todas tus librerías de Python
RUN pip install -r requirements.txt

# 5. Ahora sí, copiamos todo tu código (app.py, logica/, modelos/, etc.)
COPY . .

# 6. Exponemos el puerto 5000 (el que usa tu app) al interior de la "caja"
EXPOSE 5000

# 7. El comando final para arrancar tu aplicación
# (Esto es lo mismo que escribir "python app.py" en la terminal)
CMD ["python", "app.py"]