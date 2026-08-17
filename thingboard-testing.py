#!/usr/bin/env python3

import sqlite3
import requests
import json
import os
import time
import logging
import traceback


# ============================================================
# CONFIGURATION
# ============================================================

THINGSBOARD_URL = "https://data.echengineering.co.uk"

# Change this token after testing.
THINGSBOARD_TOKEN = "jjs6g81cu86ks45c8s0y"

DATABASE_PATH = "/var/www/html/example.db"

# Persistent state file.
# This records how far through each SQLite table we have uploaded.
STATE_PATH = "/var/www/html/thingsboard_upload_state.json"

# How many rows to send to ThingsBoard in one HTTP request.
BATCH_SIZE = 100

# How often the uploader checks for new data.
CHECK_INTERVAL = 5

# HTTP timeout.
HTTP_TIMEOUT = 20

# Don't upload SQLite's internal tables.
IGNORED_TABLES = {
    "sqlite_sequence"
}

# ============================================================
# LOGGING
# ============================================================

LOG_PATH = "/var/www/html/thingsboard-uploader.log"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def log(message):
    print(message)
    logging.info(message)


def log_error(message):
    print(message)
    logging.error(message)


# ============================================================
# THINGSBOARD ENDPOINTS
# ============================================================

TELEMETRY_URL = (
    f"{THINGSBOARD_URL}/api/v1/"
    f"{THINGSBOARD_TOKEN}/telemetry"
)

ATTRIBUTES_URL = (
    f"{THINGSBOARD_URL}/api/v1/"
    f"{THINGSBOARD_TOKEN}/attributes"
)


# ============================================================
# STATE HANDLING
# ============================================================

def load_state():
    """
    Load the upload state.

    Example:

    {
        "data": 1842,
        "university_test": 9321
    }

    The number is the SQLite rowid of the last successfully
    uploaded row for that table.
    """

    if not os.path.exists(STATE_PATH):
        return {}

    try:
        with open(STATE_PATH, "r") as f:
            state = json.load(f)

        if not isinstance(state, dict):
            log_error("Upload state is not a dictionary. Starting empty.")
            return {}

        return state

    except Exception as e:
        log_error(f"Failed to load upload state: {e}")
        return {}


def save_state(state):
    """
    Atomically save the upload state.
    """

    temporary_path = STATE_PATH + ".tmp"

    try:
        with open(temporary_path, "w") as f:
            json.dump(state, f, indent=4)

        os.replace(temporary_path, STATE_PATH)

    except Exception as e:
        log_error(f"Failed to save upload state: {e}")


# ============================================================
# SQLITE
# ============================================================

def get_tables(conn):
    """
    Return all normal SQLite tables.
    """

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )

    tables = []

    for row in cursor.fetchall():
        table_name = row[0]

        if table_name in IGNORED_TABLES:
            continue

        tables.append(table_name)

    return tables


def get_table_columns(conn, table_name):
    """
    Get column names for a table.

    PRAGMA does not accept parameters, so we quote the table
    identifier carefully.
    """

    safe_table_name = table_name.replace('"', '""')

    cursor = conn.cursor()

    cursor.execute(
        f'PRAGMA table_info("{safe_table_name}")'
    )

    columns = []

    for row in cursor.fetchall():
        columns.append(row[1])

    return columns


def get_table_rows(conn, table_name, last_rowid):
    """
    Get the next batch of rows that have not yet been uploaded.

    SQLite rowid is used as the local upload cursor.
    """

    safe_table_name = table_name.replace('"', '""')

    cursor = conn.cursor()

    query = f"""
        SELECT rowid, *
        FROM "{safe_table_name}"
        WHERE rowid > ?
        ORDER BY rowid ASC
        LIMIT ?
    """

    cursor.execute(
        query,
        (last_rowid, BATCH_SIZE)
    )

    return cursor.fetchall()


# ============================================================
# DATA CONVERSION
# ============================================================

def convert_value(value):
    """
    Convert SQLite values into JSON-safe values.

    None remains None.
    """

    if value is None:
        return None

    if isinstance(value, (int, float, str, bool)):
        return value

    return str(value)


def row_to_telemetry(columns, row, session_name):
    """
    Convert one SQLite row into a ThingsBoard telemetry object.

    SQLite:

        TIMESTAMP
        ID
        EN1
        EN2
        T00
        H00
        ...

    becomes:

        {
            "ts": 1234567890000,
            "values": {
                "ID": 0,
                "EN1": 123.4,
                "EN2": 56.7,
                "T00": 21.3,
                "H00": 47.2,
                "session": "university_test"
            }
        }
    """

    rowid = row[0]
    values = row[1:]

    row_data = dict(zip(columns, values))

    timestamp = row_data.get("TIMESTAMP")

    if timestamp is None:
        log_error(
            f"Table {session_name}, rowid {rowid} has no TIMESTAMP"
        )
        return None

    try:
        timestamp = int(timestamp)

    except Exception:
        log_error(
            f"Invalid TIMESTAMP in {session_name}, "
            f"rowid {rowid}: {timestamp}"
        )
        return None

    telemetry_values = {}

    for key, value in row_data.items():

        if key in ("TIMESTAMP", "ID"):
            continue

        converted = convert_value(value)

        if converted is not None:
            telemetry_values[key] = converted

    # Add session identifier.
    telemetry_values["session"] = session_name

    return {
        "ts": timestamp,
        "values": telemetry_values
    }


# ============================================================
# THINGSBOARD
# ============================================================

def send_telemetry(payload):
    """
    Send a telemetry batch to ThingsBoard.
    """

    try:

        response = requests.post(
            TELEMETRY_URL,
            json=payload,
            headers={
                "Content-Type": "application/json"
            },
            timeout=HTTP_TIMEOUT
        )

        if response.status_code == 200:
            return True

        log_error(
            "ThingsBoard telemetry upload failed: "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

        return False

    except requests.RequestException as e:

        log_error(
            f"ThingsBoard telemetry connection failed: {e}"
        )

        return False


def update_current_session(session_name):
    """
    Update the ThingsBoard client-side attribute showing which
    logging session is currently active.

    This is separate from historical telemetry.
    """

    payload = {
        "current_session": session_name
    }

    try:

        response = requests.post(
            ATTRIBUTES_URL,
            json=payload,
            headers={
                "Content-Type": "application/json"
            },
            timeout=HTTP_TIMEOUT
        )

        if response.status_code == 200:
            log(
                f"ThingsBoard current_session = {session_name}"
            )
            return True

        log_error(
            "Failed to update current_session: "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

        return False

    except requests.RequestException as e:

        log_error(
            f"ThingsBoard attribute connection failed: {e}"
        )

        return False


# ============================================================
# TABLE UPLOADER
# ============================================================

def upload_table(conn, table_name, state):
    """
    Upload new rows from one SQLite table.

    Returns:

        True  = successful
        False = upload failure
    """

    log(
        f"Checking session/table: {table_name}"
    )

    columns = get_table_columns(
        conn,
        table_name
    )

    if "TIMESTAMP" not in columns:

        log_error(
            f"Skipping {table_name}: "
            "no TIMESTAMP column"
        )

        return True

    last_rowid = state.get(
        table_name,
        0
    )

    try:
        last_rowid = int(last_rowid)

    except Exception:
        last_rowid = 0

    rows = get_table_rows(
        conn,
        table_name,
        last_rowid
    )

    if not rows:
        return True

    log(
        f"{table_name}: "
        f"found {len(rows)} new row(s) "
        f"after rowid {last_rowid}"
    )

    payload = []

    highest_rowid = last_rowid

    for row in rows:

        rowid = row[0]

        telemetry = row_to_telemetry(
            columns,
            row,
            table_name
        )

        if telemetry is None:
            # Don't advance past a malformed row.
            return False

        payload.append(telemetry)

        if rowid > highest_rowid:
            highest_rowid = rowid

    # --------------------------------------------------------
    # Upload entire batch.
    #
    # Only advance the SQLite cursor AFTER ThingsBoard
    # confirms success.
    # --------------------------------------------------------

    if not send_telemetry(payload):
        log_error(
            f"{table_name}: upload failed; "
            "will retry next cycle"
        )

        return False

    state[table_name] = highest_rowid
    save_state(state)

    log(
        f"{table_name}: successfully uploaded "
        f"{len(payload)} row(s), "
        f"last rowid = {highest_rowid}"
    )

    return True


# ============================================================
# DETERMINE CURRENT SESSION
# ============================================================

def get_current_session():
    """
    Determine the session currently configured by the logger.

    The existing logger stores this in data.json as:

        {
            "dbTable": "whatever"
        }

    """

    config_path = "/var/www/html/data.json"

    if not os.path.exists(config_path):
        return None

    try:

        with open(config_path, "r") as f:
            config = json.load(f)

        session = config.get("dbTable")

        if isinstance(session, str) and session:
            return session

    except Exception as e:

        log_error(
            f"Failed to read logger configuration: {e}"
        )

    return None


# ============================================================
# ONE COMPLETE UPLOAD PASS
# ============================================================

def upload_pass():
    """
    Scan the complete SQLite database and upload anything
    that hasn't already been uploaded.
    """

    if not os.path.exists(DATABASE_PATH):

        log_error(
            f"Database does not exist: {DATABASE_PATH}"
        )

        return

    state = load_state()

    try:

        conn = sqlite3.connect(
            DATABASE_PATH
        )

        tables = get_tables(conn)

        if not tables:

            log(
                "No SQLite tables found."
            )

            conn.close()
            return

        log(
            f"Found {len(tables)} table(s): "
            f"{', '.join(tables)}"
        )

        # ----------------------------------------------------
        # Update current session attribute.
        # ----------------------------------------------------

        current_session = get_current_session()

        if current_session:

            if current_session in tables:

                update_current_session(
                    current_session
                )

        # ----------------------------------------------------
        # Upload each session.
        # ----------------------------------------------------

        for table_name in tables:

            try:

                upload_table(
                    conn,
                    table_name,
                    state
                )

            except Exception as e:

                log_error(
                    f"Unhandled error processing "
                    f"{table_name}: {e}"
                )

                logging.error(
                    traceback.format_exc()
                )

        conn.close()

    except sqlite3.Error as e:

        log_error(
            f"SQLite error: {e}"
        )

    except Exception as e:

        log_error(
            f"Unexpected uploader error: {e}"
        )

        logging.error(
            traceback.format_exc()
        )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    log(
        "================================================"
    )

    log(
        "ThingsBoard SQLite uploader starting"
    )

    log(
        f"ThingsBoard: {THINGSBOARD_URL}"
    )

    log(
        f"Database: {DATABASE_PATH}"
    )

    log(
        f"State: {STATE_PATH}"
    )

    log(
        "================================================"
    )

    while True:

        try:

            upload_pass()

        except KeyboardInterrupt:

            log(
                "Uploader stopped."
            )

            break

        except Exception as e:

            log_error(
                f"Fatal error in upload loop: {e}"
            )

            logging.error(
                traceback.format_exc()
            )

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
