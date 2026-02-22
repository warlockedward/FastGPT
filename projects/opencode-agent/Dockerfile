FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install .

COPY src/ ./src/

EXPOSE 8080

CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8080"]
