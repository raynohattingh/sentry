# USE THIS BASE for JetPack 6 (Ubuntu 22.04 + CUDA 12.2 + PyTorch)
# It comes with Ultralytics (YOLO) pre-installed and optimized.
# TODO: Pin to exact digest with @sha256:... for reproducible builds
FROM ultralytics/ultralytics:8.3.0-jetson-jetpack6

# 1. Install System Dependencies
# 'usbutils' helps debug USB devices
# 'libgl1' is required for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    usbutils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Set Working Directory
WORKDIR /app

# 3. Install Python Dependencies
# We copy just requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 4. Copy Source Code
COPY src/ /app/src/

# 5. Create runtime directories
RUN mkdir -p /app/state /app/logs

# 5a. Create non-root user and set ownership
RUN useradd -m -s /bin/bash sentry && chown -R sentry:sentry /app
USER sentry

# 6. Env Variables
# Python output buffering off (so you see logs instantly)
ENV PYTHONUNBUFFERED=1

# 7. Default Command
# We run python from the src directory
WORKDIR /app/src
CMD ["python3", "main.py"]
