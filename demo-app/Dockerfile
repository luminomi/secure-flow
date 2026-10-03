FROM python:3.12-slim

# FIXED-3 (base image): python:3.12-slim still ships libpcre2-8-0 10.46-1~deb13u2,
# affected by CVE-2026-103111 (HIGH). Upgrade just that package to Debian's fixed
# build (10.46-1~deb13u3). Temporary: remove this step once the upstream
# python:3.12-slim image is rebuilt with the fix.
RUN apt-get update \
 && apt-get install -y --no-install-recommends --only-upgrade libpcre2-8-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

# PAYMENT_API_KEY must be provided at run time, e.g. docker run -e PAYMENT_API_KEY ...
# Bind to 0.0.0.0 so the app is reachable from outside the container.
CMD ["flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5000"]
