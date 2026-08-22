FROM python:3.14-bookworm

# Install system dependencies
RUN apt-get update && \
    apt-get install -y imagemagick ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Longgarkan policy ImageMagick untuk MoviePy TextClip
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@\*"/g' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["python", "app.py"]