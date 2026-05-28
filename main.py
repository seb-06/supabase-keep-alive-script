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
        for table_name in ("people", "People"):
            try:
                response = db["client"].table(table_name).select("*").execute()
                print(f"[{datetime.now()}] {db['name']} success: {len(response.data)} rows retrieved from {table_name}.")
                break
            except Exception as err:
                code = getattr(err, "code", None)
                message = getattr(err, "message", None)
                details = getattr(err, "details", None)
                hint = getattr(err, "hint", None)

                if not any([code, message, details, hint]) and hasattr(err, "args") and err.args:
                    first = err.args[0]
                    if isinstance(first, dict):
                        code = first.get("code")
                        message = first.get("message")
                        details = first.get("details")
                        hint = first.get("hint")

                combined = " ".join(
                    str(x) for x in (code, message, details, hint, err) if x
                ).lower()

                should_try_fallback = (
                    table_name == "people"
                    and (
                        code in ("42P01", "PGRST205")
                        or "42p01" in combined
                        or "pgrst205" in combined
                        or ("could not find the table" in combined and "public.people" in combined)
                        or ("perhaps you meant" in combined and "public.people" in combined)
                    )
                )

                if should_try_fallback:
                    print(f"[{datetime.now()}] {db['name']} people not found, trying People...")
                    continue

                print(f"[{datetime.now()}] {db['name']} query error on {table_name}: {err}")
                break
        else:
            print(f"[{datetime.now()}] {db['name']} query error: people and People both failed.")


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
