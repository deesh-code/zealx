# logger.py - Logs API errors for debugging

import datetime

LOG_FILE = "autox_ai_errors.log"

def log_error(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log:
        log.write(f"[{timestamp}] {message}\n")
    print(f"🔥 ERROR LOGGED: {message}")  # Optional: Print to console
