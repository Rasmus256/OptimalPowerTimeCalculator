# Stage 1: Dependencies and Build
FROM python:3.14-slim AS builder
WORKDIR /app
# Install and build everything here
COPY /api/requirements.txt .

COPY api/ .
RUN pip install -r requirements.txt

FROM python:3.14.0-slim AS test
WORKDIR /app
COPY --from=builder /app .
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

RUN python -m pytest ./tests/

FROM python:3.14.0-slim AS runtime
WORKDIR /app

COPY --from=test /app .
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

CMD ["uvicorn", "rest:app", "--host", "0.0.0.0", "--port", "80"]
