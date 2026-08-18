"""
Naukri Daily Profile Updater
-----------------------------
Logs into your Naukri account and makes a tiny edit to your Resume Headline
(toggling a trailing period) so your profile registers as "recently updated".
Naukri's recruiter search ranks recently-updated profiles higher, so this
keeps you near the top without you having to log in and click Save every day.

SETUP:
    1. pip install -r requirements.txt
    2. Copy .env.example to .env and fill in your real credentials
    3. Run once manually to make sure it works:  python naukri_updater.py
    4. Schedule it with Windows Task Scheduler (see README.md)

NOTES:
    - This is unofficial browser automation, not an official Naukri feature.
      Keep the frequency reasonable (once a day) to avoid looking bot-like.
    - If Naukri ever asks for an OTP, this script cannot solve it. Run it
      manually that one time and it should go back to normal after.
    - Your credentials stay local, in your own .env file. Never commit .env
      to any public repo.
"""

import os
import sys
import time
import logging
from datetime import datetime

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Setup logging (prints to console AND writes to a log file next to script)
# ---------------------------------------------------------------------------
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_log.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("naukri_updater")

LOGIN_URL = "https://www.naukri.com/nlogin/login"
PROFILE_URL = "https://www.naukri.com/mnjuser/profile"
WAIT_SECONDS = 20


def load_credentials():
    load_dotenv()
    email = os.getenv("NAUKRI_EMAIL")
    password = os.getenv("NAUKRI_PASSWORD")
    if not email or not password:
        log.error("Missing NAUKRI_EMAIL or NAUKRI_PASSWORD. Check your .env file.")
        sys.exit(1)
    return email, password


def build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    # Required for running Chrome as root inside Docker containers
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # Reduces "automated browser" fingerprint slightly
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Inside Docker we install Chrome + a matching chromedriver at fixed
    # paths (see Dockerfile). Locally, webdriver-manager auto-downloads one.
    chrome_bin = os.getenv("CHROME_BIN")
    chromedriver_bin = os.getenv("CHROMEDRIVER_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin

    if chromedriver_bin:
        service = Service(chromedriver_bin)
    else:
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    return driver


def login(driver: webdriver.Chrome, email: str, password: str):
    log.info("Opening login page...")
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, WAIT_SECONDS)

    email_field = wait.until(EC.presence_of_element_located((By.ID, "usernameField")))
    password_field = driver.find_element(By.ID, "passwordField")

    email_field.clear()
    email_field.send_keys(email)
    password_field.clear()
    password_field.send_keys(password)

    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()

    # Wait for redirect away from the login page as a sign of success
    wait.until(EC.url_contains("naukri.com/mnjuser"))
    log.info("Login successful.")


def touch_resume_headline(driver: webdriver.Chrome):
    """
    Opens the Resume Headline edit box on the profile page, toggles a
    trailing character, and saves. This is enough for Naukri to treat the
    profile as freshly updated.
    """
    log.info("Navigating to profile page...")
    driver.get(PROFILE_URL)
    wait = WebDriverWait(driver, WAIT_SECONDS)

    # Naukri's DOM structure changes occasionally. If the edit_icon line
    # below fails, open the profile page, right-click the pencil/edit icon
    # next to "Resume Headline" itself (not the popup that opens after
    # clicking it), choose Inspect, and update this XPATH to match.
    edit_icon = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "(//div[contains(@class,'resumeHeadline')]//span[contains(@class,'icon') and contains(@class,'edit')])[1]")
        )
    )
    edit_icon.click()

    # Confirmed selectors from the live edit drawer HTML
    textarea = wait.until(
        EC.presence_of_element_located((By.ID, "resumeHeadlineTxt"))
    )
    current_text = textarea.get_attribute("value") or textarea.text

    if current_text.strip().endswith("."):
        new_text = current_text.strip()[:-1]
    else:
        new_text = current_text.strip() + "."

    textarea.clear()
    textarea.send_keys(new_text)

    save_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-dark-ot[type='submit']"))
    )
    save_button.click()

    time.sleep(2)  # let the save request complete
    log.info("Resume headline touched and saved.")


def main():
    email, password = load_credentials()
    driver = build_driver(headless=True)
    try:
        login(driver, email, password)
        touch_resume_headline(driver)
        log.info("Daily profile update completed successfully: %s", datetime.now().isoformat())
    except TimeoutException:
        log.error("Timed out waiting for a page element. Naukri's page layout may have "
                   "changed, or login may require an OTP this time. Run with headless=False "
                   "to see what's happening.")
    except NoSuchElementException as e:
        log.error("Could not find an expected element: %s", e)
    except Exception as e:
        log.exception("Unexpected error: %s", e)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
