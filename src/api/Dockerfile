FROM  python:3.11-slim-buster

COPY api/ ./api
COPY lib/ ./lib

RUN pip install -r ./api/requirements.txt

CMD ["uvicorn", "api.rest:app", "--host", "0.0.0.0", "--port", "80"]
