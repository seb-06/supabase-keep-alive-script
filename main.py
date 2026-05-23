import os
import sys
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path="/home/Seb06/.env")

target_time_str = "18:10"
if len(sys.argv) > 1:
    provided_time = sys.argv[1]
    if re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", provided_time):
        target_time_str = provided_time
    else:
        print(f"Warning: Invalid time format '{provided_time}'. Defaulting to 18:10.")

TARGET_HOUR, TARGET_MINUTE = map(int, target_time_str.split(":"))
print(f"Target runtime configured for: {TARGET_HOUR:02d}:{TARGET_MINUTE:02d}")

def load_database_configs():
    raw_names = os.environ.get("SUPABASE_DATABASES", "")
    names = [name.strip() for name in raw_names.split(",") if name.strip()]

    databases = []
    for name in names:
        env_prefix = name.upper().replace("-", "_")
        url = os.environ.get(f"{env_prefix}_URL")
        key = os.environ.get(f"{env_prefix}_KEY")

        if not url or not key:
            print(f"Skipping {name}: Missing {env_prefix}_URL or {env_prefix}_KEY.")
            continue

        if not url.startswith("https://"):
            print(f"Skipping {name}: Invalid URL.")
            continue

        try:
            client = create_client(url, key)
            databases.append({
                "name": name,
                "url": url,
                "key": key,
                "client": client,
            })
            print(f"{name} initialized successfully.")
        except Exception as init_err:
            print(f"Skipping {name}: Initialization error - {init_err}")

    return databases

DATABASES = load_database_configs()

def query_databases():
    if not DATABASES:
        print(f"[{datetime.now()}] Execution skipped: No active database clients available.")
        return

    for db in DATABASES:
        try:
            response = db["client"].table("people").select("*").execute()
            print(f"[{datetime.now()}] {db['name']} success: {len(response.data)} rows retrieved.")
        except Exception as e:
            print(f"[{datetime.now()}] {db['name']} query error: {e}")

def get_seconds_until_target():
    now = datetime.now()
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return int((target - now).total_seconds())

if __name__ == "__main__":
    print("Script started in safety-check mode...")
    while True:
        try:
            sleep_duration = get_seconds_until_target() / 2
            print(f"Sleeping for {sleep_duration} seconds until {TARGET_HOUR:02d}:{TARGET_MINUTE:02d}...")
            time.sleep(sleep_duration)

            query_databases()
            time.sleep(60)
        except KeyboardInterrupt:
            print("Script manually stopped.")
            break
        except Exception as general_err:
            print(f"Loop error occurred: {general_err}")
            time.sleep(10)

