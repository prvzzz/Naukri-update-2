#!/bin/bash
set -e

# Cron jobs run in a minimal environment and don't inherit the container's
# env vars by default. Dump them to /etc/environment so the cron job can
# read NAUKRI_EMAIL / NAUKRI_PASSWORD / CHROME_BIN / etc.
printenv | grep -Ev '^(HOME|PWD|SHLVL|_)=' > /etc/environment

# Write the cron job. CRON_SCHEDULE is set as an ENV in the Dockerfile
# (default "0 8 * * *" = 8:00 AM daily) and can be overridden at
# `docker run` time with -e CRON_SCHEDULE="MIN HOUR * * *"
echo "${CRON_SCHEDULE} root . /etc/environment; cd /app && /opt/venv/bin/python /app/naukri_updater.py >> /var/log/cron.log 2>&1" > /etc/cron.d/naukri-cron
chmod 0644 /etc/cron.d/naukri-cron
crontab /etc/cron.d/naukri-cron

touch /var/log/cron.log
echo "Naukri updater container started."
echo "Timezone: $(cat /etc/timezone)"
echo "Cron schedule: ${CRON_SCHEDULE}"
echo "Logs: /var/log/cron.log (also visible via 'docker logs')"

# Start cron in the background, then tail the log so `docker logs` shows
# script output as it runs (this is what keeps the container alive).
cron
tail -f /var/log/cron.log
