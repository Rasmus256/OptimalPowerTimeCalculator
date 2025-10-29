# Stage 1: Dependencies and Build
FROM python:3.14-slim AS builder
WORKDIR /app
# Install and build everything here
COPY /api/requirements.txt .

COPY api/ .
CMD ["pip" "install" "-r" "requirements.txt"]

FROM python:3.14.0-slim AS test
WORKDIR /app
COPY --from=builder /app .

CMD ["python", "-m", "pytest", "./tests/"]

FROM python:3.14.0-slim AS runtime
WORKDIR /app

COPY --from=builder /app .

CMD ["uvicorn", "rest:app", "--host", "0.0.0.0", "--port", "80"]
