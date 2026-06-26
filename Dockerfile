FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install fastapi uvicorn psycopg2-binary python-dotenv "passlib[bcrypt]==1.7.4" "bcrypt==4.0.1" python-jose[cryptography] redis
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]