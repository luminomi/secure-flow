# Deliberately simple, unhardened image. Later phases will scan it with Trivy.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

# Bind to 0.0.0.0 so the app is reachable from outside the container.
CMD ["flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5000"]
