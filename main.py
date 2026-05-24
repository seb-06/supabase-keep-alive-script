import os
import sys
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

DATABASE_FILE = Path(os.environ.get("DATABASE_FILE", "/app/databases.txt"))
DEFAULT_TARGET_TIME = os.environ.get("TARGET_TIME", "00:00")


def parse_target_time(argv):
    target_time_str = DEFAULT_TARGET_TIME
    if len(argv) > 1:
        provided_time = argv[1]
        if re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", provided_time):
            target_time_str = provided_time
        else:
            print(f"Warning: Invalid time format '{provided_time}'. Defaulting to {DEFAULT_TARGET_TIME}.")
    return target_time_str


def load_database_configs(path=DATABASE_FILE):
    databases = []

    if not path.exists():
        print(f"Database file not found: {path}")
        return databases

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("|", 2)
        if len(parts) != 3:
            print(f"Skipping malformed database entry: {line}")
            continue

        name, url, key = [part.strip() for part in parts]

        if not url.startswith("https://"):
            print(f"Skipping {name}: Invalid URL.")
            continue

        try:
            client = create_client(url, key)
            databases.append({"name": name, "client": client})
            print(f"{name} initialized successfully.")
        except Exception as init_err:
            print(f"Skipping {name}: Initialization error - {init_err}")

    return databases


def query_databases(databases):
    if not databases:
        print(f"[{datetime.now()}] Execution skipped: No active database clients available.")
        return

    for db in databases:
        try:
            response = db["client"].table("people").select("*").execute()
            print(f"[{datetime.now()}] {db['name']} success: {len(response.data)} rows retrieved.")
        except Exception as err:
            print(f"[{datetime.now()}] {db['name']} query error: {err}")


def get_seconds_until_target(target_hour, target_minute):
    now = datetime.now()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

    while target <= now:
        target += timedelta(hours=12)

    return int((target - now).total_seconds())


if __name__ == "__main__":
    target_time_str = parse_target_time(sys.argv)
    target_hour, target_minute = map(int, target_time_str.split(":"))
    print(f"Target runtime configured for: {target_hour:02d}:{target_minute:02d}")
    print(f"Using database file: {DATABASE_FILE}")
    print("Script started in scheduler mode...")

    while True:
        try:
            sleep_duration = get_seconds_until_target(target_hour, target_minute)
            print(f"Sleeping for {sleep_duration} seconds until next run...")
            time.sleep(max(sleep_duration, 1))
            databases = load_database_configs()
            query_databases(databases)
            time.sleep(60)
        except KeyboardInterrupt:
            print("Script manually stopped.")
            break
        except Exception as general_err:
            print(f"Loop error occurred: {general_err}")
            time.sleep(10)
