# Naukri Daily Profile Updater

Automatically "touches" your Naukri profile once a day (toggles a trailing
period on your Resume Headline and saves) so it shows up as recently updated
in recruiter searches — without you having to log in manually every morning.

This is unofficial browser automation (via Selenium), not a feature provided
by Naukri. Keep it to once a day so your account doesn't look bot-like.

## 1. Install Python

If you don't already have it: download Python 3.10+ from
https://www.python.org/downloads/windows/ and check "Add Python to PATH"
during install.

You'll also need **Google Chrome** installed (the script drives Chrome
directly — no separate ChromeDriver download needed, `webdriver-manager`
handles that automatically).

## 2. Install dependencies

Open Command Prompt or PowerShell in this folder and run:

```
pip install -r requirements.txt
```

## 3. Add your credentials

1. Copy `.env.example` to a new file named `.env` in the same folder
2. Open `.env` and fill in your real Naukri email and password
3. Keep this file private — don't share it or upload it anywhere

## 4. Test it manually first

```
python naukri_updater.py
```

Check `update_log.txt` in this folder — it should say "Daily profile update
completed successfully". If it fails, see Troubleshooting below.

## 5. Schedule it with Windows Task Scheduler

1. Open **Task Scheduler** (search for it in the Start menu)
2. Click **Create Basic Task** (right panel)
3. Name it something like "Naukri Daily Update", click Next
4. Trigger: choose **Daily**, pick a time (e.g. 8:00 AM), click Next
5. Action: choose **Start a program**, click Next
6. Program/script: browse to your Python executable, e.g.
   `C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe`
   (run `where python` in Command Prompt if unsure)
7. Add arguments: `naukri_updater.py`
8. Start in: the full path to this folder, e.g.
   `C:\Users\<you>\naukri-auto-update`
9. Finish, then find the task in the list, right-click → Properties →
   check **"Run whether user is logged on or not"** if you want it to run
   even when you're not logged in (it'll ask for your Windows password once)

Your profile will now update automatically every day at the time you chose.

## Running it in Docker on EC2

This turns the script into a self-contained container that runs itself daily
via an internal cron job — no host-level scheduling needed.

### 1. Launch an EC2 instance

- Ubuntu 22.04 or Amazon Linux 2023, t3.small or larger (Chrome needs ~1-2GB
  RAM comfortably; t3.micro can work but may be tight)
- Open only SSH (port 22) in the security group — this container makes
  outbound connections only, it doesn't need any inbound ports open

### 2. Install Docker on the instance

```bash
sudo apt update && sudo apt install -y docker.io   # Ubuntu
sudo systemctl enable --now docker
sudo usermod -aG docker $USER                       # log out/in after this
```

(Amazon Linux: `sudo dnf install -y docker && sudo systemctl enable --now docker`)

### 3. Copy the project to the instance

From your Mac:
```bash
scp -i your-key.pem -r naukri-auto-update ubuntu@<EC2_PUBLIC_IP>:~/
```

Make sure your real `.env` (with actual credentials) is included in that
folder before copying — it's used at container runtime, not baked into the
image.

### 4. Build the image

On the EC2 instance:
```bash
cd naukri-auto-update
docker build -t naukri-updater .
```

This takes a few minutes the first time (downloading Chrome + chromedriver).

### 5. Run the container

```bash
docker run -d \
  --name naukri-updater \
  --env-file .env \
  --restart unless-stopped \
  naukri-updater
```

- `-d` runs it in the background
- `--restart unless-stopped` means it survives EC2 reboots and auto-restarts
  if it crashes
- The container stays alive because cron runs inside it continuously,
  triggering the script once a day at the scheduled time

### 6. Check it's working

```bash
docker logs -f naukri-updater
```

You should see the startup message showing the timezone and cron schedule,
then once a day, the same log lines you saw when testing locally
("Login successful", "Resume headline touched and saved", etc.).

## Where to set the daily update time

The time is controlled by the `CRON_SCHEDULE` environment variable, in
standard cron syntax: `MINUTE HOUR * * *` (24-hour format). It's interpreted
in the timezone set by `TZ` in the Dockerfile (defaults to `Asia/Kolkata`,
i.e. IST).

**Default:** `0 8 * * *` → runs daily at 8:00 AM IST.

**To use a different time**, pass it when you start the container:
```bash
docker run -d \
  --name naukri-updater \
  --env-file .env \
  --restart unless-stopped \
  -e CRON_SCHEDULE="30 9 * * *" \
  naukri-updater
```
That example runs at 9:30 AM IST instead. A few more examples:
- `0 7 * * *` → 7:00 AM
- `0 20 * * *` → 8:00 PM
- `*/30 * * * *` → every 30 minutes (only for testing — don't leave this on)

**To change the time on a container that's already running**, either:
- Stop and re-run it with a new `-e CRON_SCHEDULE=...` value (`docker rm -f
  naukri-updater` then re-run the `docker run` command above), or
- Exec into the running container and edit the crontab directly:
  ```bash
  docker exec -it naukri-updater bash
  crontab -e   # edit the schedule line, save, exit
  ```
  This takes effect immediately, no restart needed, but won't survive if the
  container is ever recreated (the Dockerfile default takes over again).

**If you're not in India**, change `ENV TZ=Asia/Kolkata` in the Dockerfile
to your zone (e.g. `America/New_York`) before building, so the cron time
matches your local clock.

## Troubleshooting

- **Script times out on login**: Naukri sometimes shows an OTP prompt for
  logins from a new location/device. Run the script manually once
  (`python naukri_updater.py` after temporarily setting `headless=False` in
  `build_driver()` in the code) to clear it, then automation should resume
  working.
- **"Could not find element" errors**: Naukri occasionally changes their
  page layout, which breaks the CSS/XPath selectors in the script. Open your
  profile page in Chrome, right-click the Resume Headline edit (pencil) icon
  → Inspect, and update the selectors in `touch_resume_headline()` in
  `naukri_updater.py` to match.
- **Nothing happens / Chrome flashes and closes**: set `headless=False` in
  `build_driver(headless=True)` temporarily so you can watch the browser and
  see where it's getting stuck.

## A note on frequency and account safety

Running this once a day mimics normal user behavior and is how most people
use this kind of script. Running it many times a day, or scraping/automating
other actions beyond this small edit, increases the chance Naukri's systems
flag the account for unusual activity.
