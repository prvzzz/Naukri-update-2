# =========================================================================
# Stage 1: builder — install Python dependencies into a venv
# =========================================================================
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# =========================================================================
# Stage 2: runtime — Chrome + matching chromedriver + cron + app code
# =========================================================================
FROM python:3.12-slim AS runtime

# Set your timezone so the cron schedule below means local time, not UTC.
# Change this if you're not in India.
ENV TZ=Asia/Kolkata

RUN apt-get update && apt-get install -y --no-install-recommends \
        wget gnupg unzip curl cron tzdata \
        fonts-liberation libnss3 libatk-bridge2.0-0 libx11-xcb1 \
        libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
        libpangocairo-1.0-0 libgtk-3-0 libxss1 xdg-utils ca-certificates \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    # Install Google Chrome stable
    && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    # Install the matching chromedriver via Chrome for Testing API
    && CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+\.\d+') \
    && DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); v='$CHROME_VERSION'; \
          matches=[x for x in d['versions'] if x['version']==v]; \
          m=matches[0] if matches else d['versions'][-1]; \
          print([b['url'] for b in m['downloads']['chromedriver'] if b['platform']=='linux64'][0])") \
    && wget -q -O /tmp/chromedriver.zip "$DRIVER_URL" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64 \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_BIN=/usr/local/bin/chromedriver

# Bring in the Python deps built in stage 1
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY naukri_updater.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default: run daily at 8:00 AM in the TZ set above (Asia/Kolkata).
# Override at `docker run` time with -e CRON_SCHEDULE="MIN HOUR * * *"
ENV CRON_SCHEDULE="0 8 * * *"

ENTRYPOINT ["/entrypoint.sh"]
