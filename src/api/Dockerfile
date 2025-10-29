FROM python:3.14.0-slim AS test

COPY ./api ./api

RUN pip install -r ./api/requirements.txt

RUN python -m pytest ./api/tests/ -v --tb=short --disable-warnings

RUN echo "TEST PASSED! HURRAY!"

CMD ["uvicorn", "api.rest:app", "--host", "0.0.0.0", "--port", "80"]
