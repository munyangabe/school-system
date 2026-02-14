FROM python:3.10-slim

WORKDIR /app

COPY . .

ENV SMS_HOST=0.0.0.0
ENV SMS_PORT=8000
EXPOSE 8000

CMD ["python3", "app.py"]
