FROM python:3.14.0-slim AS test

COPY ./api ./api
COPY requirements.txt .

RUN pip install -r ./requirements.txt

RUN python -m pytest ./api/tests/ -v

RUN echo "TEST PASSED! HURRAY!"

CMD ["uvicorn", "api.rest:app", "--host", "0.0.0.0", "--port", "80"]
