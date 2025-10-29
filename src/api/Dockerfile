FROM python:3.14.0-slim AS test

COPY main.py .
COPY ./api/tests ./api/tests
COPY requirements.txt .

RUN pip install -r ./requirements.txt

RUN python -m pytest ./api/tests/ -v

RUN echo "TEST PASSED! HURRAY!"


FROM python:3.14.0-slim AS prod

COPY api/ ./api

RUN pip install -r ./api/requirements.txt

CMD ["uvicorn", "api.rest:app", "--host", "0.0.0.0", "--port", "80"]
