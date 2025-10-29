# Stage 1: Dependencies and Build
FROM python:3.14-slim AS builder
WORKDIR /app
# Install and build everything here
COPY /api/requirements.txt .
RUN pip install -r requirements.txt

COPY api/ .

FROM python:3.14.0-slim AS test
# Copy only what's needed for production
WORKDIR /app
COPY --from=builder /app .

RUN python -m pytest ./tests/ -v --tb=short --disable-warnings

RUN echo "TEST PASSED! HURRAY!"

FROM python:3.14.0-slim AS runtime
WORKDIR /app

COPY --from=builder /app .

CMD ["uvicorn", "rest:app", "--host", "0.0.0.0", "--port", "80"]
