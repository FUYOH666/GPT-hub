FROM python:3.12-slim-bookworm
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
