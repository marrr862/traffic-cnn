# Online demo for Hugging Face Spaces (Docker SDK, free CPU hardware).
# Installs the project from GitHub, downloads the released models and demo videos,
# and adds precomputed results (examples/) so the demo videos can be shown instantly.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1
WORKDIR /home/user/app

ARG REVISION=main
RUN git clone --depth 1 --branch ${REVISION} https://github.com/marrr862/traffic-cnn.git .
RUN pip install --no-cache-dir --user torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --user .
RUN python scripts/download_assets.py

COPY --chown=user examples/ outputs/

EXPOSE 7860
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port", "7860", "--server.address", "0.0.0.0", \
     "--server.maxUploadSize", "200", "--server.enableXsrfProtection", "false", "--server.enableCORS", "false", \
     "--browser.gatherUsageStats", "false"]
