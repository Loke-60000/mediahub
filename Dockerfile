FROM python:3.10-slim

WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        imagemagick \
        ghostscript \
        curl \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="resource" name="memory" value="256MiB"\/>/<policy domain="resource" name="memory" value="512MiB"\/>/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="resource" name="disk" value="1GiB"\/>/<policy domain="resource" name="disk" value="4GiB"\/>/' /etc/ImageMagick-6/policy.xml
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p ${TEMP_DIR:-/tmp/youtube-dl} && \
    chmod 777 ${TEMP_DIR:-/tmp/youtube-dl}

ENV PORT=8000 \
    HOST=0.0.0.0 \
    TEMP_DIR=/tmp/youtube-dl \
    MAX_CONCURRENT_DOWNLOADS=3 \
    QUEUE_MAX_SIZE=100 \
    MAX_FILE_SIZE_MB=1000 \
    DOWNLOAD_TIMEOUT=3600 \
    REQUIRE_API_KEY=false \
    ENABLE_RATE_LIMITING=true \
    RATE_LIMIT_REQUESTS=30 \
    CORS_ORIGINS="*" \
    ENABLE_CONVERSION=true \
    MAX_CONVERSION_SIZE_MB=500 \
    CONVERSION_TIMEOUT=600 \
    DEFAULT_IMAGE_QUALITY=90

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/ || exit 1

CMD ["python", "-m", "app.main"]