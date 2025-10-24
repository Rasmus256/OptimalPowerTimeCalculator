FROM python:3.14.0-slim

WORKDIR /app

COPY src/api/requirements.txt .
RUN pip install -r requirements.txt

COPY src/api/ .

CMD ["uvicorn", "rest:app", "--host", "0.0.0.0", "--port", "80"]
