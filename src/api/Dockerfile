FROM  python:3.13.2-slim

COPY api/ ./api

RUN pip install -r ./api/requirements.txt

CMD ["uvicorn", "api.rest:app", "--host", "0.0.0.0", "--port", "80"]
