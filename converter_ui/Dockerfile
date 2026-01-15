FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn requests python-multipart jinja2

COPY . /app

EXPOSE 3000

# Run the app from the src directory
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3000"]
