FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir flask pyserial

COPY . .

EXPOSE 5000 

CMD ["python3", "-u", "server.py"]  
