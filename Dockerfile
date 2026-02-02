FROM public.ecr.aws/lambda/python:3.13

# Install system dependencies for Playwright
# These are required for Chromium to run in a headless environment on Amazon Linux 2023
RUN dnf install -y \
    mesa-libgbm \
    libX11 \
    libXcomposite \
    libXdamage \
    libXext \
    libXfixes \
    libXrandr \
    libXrender \
    libXtst \
    alsa-lib \
    at-spi2-atk \
    at-spi2-core \
    cups-libs \
    dbus-libs \
    expat \
    libdrm \
    libXkbcommon \
    libxshmfence \
    nspr \
    nss \
    nss-util \
    pango \
    && dnf clean all

# Set Playwright to install browsers in a specific location that will be included in the image
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# Set environment to production to avoid loading .env.local
ENV ENV=production

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser binaries
RUN playwright install chromium

# Copy application code
COPY app/ ./app/

# The CMD will be overridden by the Lambda configuration for each function.
# Here we provide one as a default.
CMD ["app.handlers.populate_runners.lambda_handler"]
