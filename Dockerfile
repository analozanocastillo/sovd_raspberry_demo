FROM python:3.11-slim

WORKDIR /app

COPY server.py .

EXPOSE 5000 #Indica que el servidor escucha en el puerto 5000

CMD ["python3", "server.py"]  # Comando que se ejecuta al arrancar el contenedor