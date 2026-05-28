FROM python:3.11-slim

WORKDIR /app

COPY . .

EXPOSE 5000 

CMD ["python3", "-u", "server.py"]  