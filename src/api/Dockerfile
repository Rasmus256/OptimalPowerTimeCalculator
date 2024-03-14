FROM  python:3.13.0a5-slim

COPY api/ ./api
COPY lib/ ./lib

RUN pip install -r ./api/requirements.txt

CMD ["uvicorn", "api.rest:app", "--host", "0.0.0.0", "--port", "80"]
