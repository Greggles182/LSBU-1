#!/usr/bin/env python3
"""
ThingsBoard SQLite Uploader Module

Uploads sensor data from SQLite database to ThingsBoard cloud platform.
Can be imported and run as a background thread in Flask applications.
"""

import sqlite3
import requests
import json
import os
import time
import logging
import traceback
from threading import Thread


# ============================================================
# Logging
# ============================================================

LOG_FILE = "/var/www/html/tb.log"

logger = logging.getLogger("thingsboard_uploader")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


class ThingsboardUploader:
    """Handles uploading SQLite data to ThingsBoard."""

    def __init__(self, config):
        """
        Initialize ThingsBoard uploader.

        Args:
            config: Dictionary with keys:
                - thingsboard_url: ThingsBoard server URL
                - thingsboard_token: Device authentication token
                - database_path: Path to SQLite database
                - state_path: Path to state file
                - batch_size: Rows per HTTP request (default 100)
                - check_interval: Seconds between checks (default 5)
                - http_timeout: HTTP request timeout (default 20)
        """

        self.config = config
        self.running = False

        self.thingsboard_url = config.get(
            "thingsboard_url",
            ""
        )

        self.thingsboard_token = config.get(
            "thingsboard_token",
            ""
        )

        self.database_path = config.get(
            "database_path",
            ""
        )

        self.state_path = config.get(
            "state_path",
            ""
        )

        self.batch_size = config.get(
            "batch_size",
            100
        )

        self.check_interval = config.get(
            "check_interval",
            5
        )

        self.http_timeout = config.get(
            "http_timeout",
            20
        )

        self.heartbeat_interval = 60

        self.ignored_tables = {
            "sqlite_sequence"
        }

        self.telemetry_url = (
            f"{self.thingsboard_url.rstrip('/')}/api/v1/"
            f"{self.thingsboard_token}/telemetry"
        )

        self.attributes_url = (
            f"{self.thingsboard_url.rstrip('/')}/api/v1/"
            f"{self.thingsboard_token}/attributes"
        )

    def is_enabled(self):
        """Check if ThingsBoard is properly configured."""

        return bool(
            self.thingsboard_url
            and self.thingsboard_token
            and self.database_path
            and self.state_path
        )

    def load_state(self):
        """Load the upload state from file."""

        if not os.path.exists(self.state_path):
            logger.info(
                "Upload state file does not exist. "
                "Starting with empty state."
            )
            return {}

        try:
            with open(self.state_path, "r") as f:
                state = json.load(f)

            if not isinstance(state, dict):
                logger.error(
                    "Upload state is not a dictionary. "
                    "Starting empty."
                )
                return {}

            return state

        except Exception:
            logger.exception(
                "Failed to load upload state"
            )
            return {}

    def save_state(self, state):
        """Atomically save the upload state."""

        temporary_path = self.state_path + ".tmp"

        try:
            with open(temporary_path, "w") as f:
                json.dump(
                    state,
                    f,
                    indent=4
                )

            os.replace(
                temporary_path,
                self.state_path
            )

        except Exception:
            logger.exception(
                "Failed to save upload state"
            )

    def get_tables(self, conn):
        """Return all normal SQLite tables."""

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

            if table_name in self.ignored_tables:
                continue

            tables.append(table_name)

        return tables

    def get_table_columns(self, conn, table_name):
        """Get column names for a table."""

        safe_table_name = table_name.replace(
            '"',
            '""'
        )

        cursor = conn.cursor()

        cursor.execute(
            f'PRAGMA table_info("{safe_table_name}")'
        )

        columns = []

        for row in cursor.fetchall():
            columns.append(row[1])

        return columns

    def get_table_rows(
        self,
        conn,
        table_name,
        last_rowid
    ):
        """Get the next batch of rows."""

        safe_table_name = table_name.replace(
            '"',
            '""'
        )

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
            (
                last_rowid,
                self.batch_size
            )
        )

        return cursor.fetchall()

    def convert_value(self, value):
        """Convert SQLite values into JSON-safe values."""

        if value is None:
            return None

        if isinstance(
            value,
            (
                int,
                float,
                str,
                bool
            )
        ):
            return value

        return str(value)

    def row_to_telemetry(
        self,
        columns,
        row,
        session_name
    ):
        """Convert one SQLite row into ThingsBoard telemetry."""

        rowid = row[0]
        values = row[1:]

        row_data = dict(
            zip(
                columns,
                values
            )
        )

        timestamp = row_data.get(
            "TIMESTAMP"
        )

        if timestamp is None:

            logger.error(
                "Table %s, rowid %s has no TIMESTAMP",
                session_name,
                rowid
            )

            return None

        try:
            timestamp = int(timestamp)

        except Exception:

            logger.error(
                "Invalid TIMESTAMP in %s, rowid %s: %s",
                session_name,
                rowid,
                timestamp
            )

            return None

        telemetry_values = {}

        for key, value in row_data.items():

            if key in (
                "TIMESTAMP",
                "ID"
            ):
                continue

            converted = self.convert_value(
                value
            )

            if converted is not None:
                telemetry_values[key] = converted

        telemetry_values["session"] = session_name

        return {
            "ts": timestamp,
            "values": telemetry_values
        }

    def send_telemetry(self, payload):
        """Send a telemetry batch to ThingsBoard."""

        try:

            response = requests.post(
                self.telemetry_url,
                json=payload,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=self.http_timeout
            )

            if response.status_code == 200:
                return True

            logger.error(
                "ThingsBoard telemetry upload failed: "
                "HTTP %s: %s",
                response.status_code,
                response.text
            )

            return False

        except requests.RequestException:

            logger.exception(
                "ThingsBoard telemetry connection failed"
            )

            return False

        except Exception:

            logger.exception(
                "Unexpected error sending telemetry"
            )

            return False

    def update_current_session(
        self,
        session_name
    ):
        """Update ThingsBoard current session attribute."""

        payload = {
            "current_session": session_name
        }

        try:

            response = requests.post(
                self.attributes_url,
                json=payload,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=self.http_timeout
            )

            if response.status_code == 200:

                logger.info(
                    "ThingsBoard current_session = %s",
                    session_name
                )

                return True

            logger.error(
                "Failed to update current_session: "
                "HTTP %s: %s",
                response.status_code,
                response.text
            )

            return False

        except requests.RequestException:

            logger.exception(
                "ThingsBoard attribute connection failed"
            )

            return False

        except Exception:

            logger.exception(
                "Unexpected error updating current_session"
            )

            return False

    def update_last_updated(self):
        """Update ThingsBoard attribute with current timestamp."""

        timestamp = int(
            time.time() * 1000
        )

        payload = {
            "last_updated": timestamp
        }

        logger.info(
            "Sending ThingsBoard last_updated = %s",
            timestamp
        )

        try:

            response = requests.post(
                self.attributes_url,
                json=payload,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=self.http_timeout
            )

            if response.status_code == 200:

                logger.info(
                    "ThingsBoard last_updated sent successfully"
                )

                return True

            logger.error(
                "Failed to update last_updated: "
                "HTTP %s: %s",
                response.status_code,
                response.text
            )

            return False

        except requests.RequestException:

            logger.exception(
                "ThingsBoard last_updated connection failed"
            )

            return False

        except Exception:

            logger.exception(
                "Unexpected error updating last_updated"
            )

            return False

    def heartbeat_loop(self):
        """Send ThingsBoard heartbeat every 60 seconds."""

        logger.info(
            "ThingsBoard heartbeat thread started "
            "(interval: %s seconds)",
            self.heartbeat_interval
        )

        # Send immediately when the uploader starts.
        self.update_last_updated()

        while self.running:

            for _ in range(
                self.heartbeat_interval
            ):

                if not self.running:
                    break

                time.sleep(1)

            if self.running:
                self.update_last_updated()

        logger.info(
            "ThingsBoard heartbeat thread stopped"
        )

    def upload_table(
        self,
        conn,
        table_name,
        state
    ):
        """Upload new rows from one SQLite table."""

        logger.info(
            "Checking session/table: %s",
            table_name
        )

        columns = self.get_table_columns(
            conn,
            table_name
        )

        if "TIMESTAMP" not in columns:

            logger.warning(
                "Skipping %s: no TIMESTAMP column",
                table_name
            )

            return True

        last_rowid = state.get(
            table_name,
            0
        )

        try:
            last_rowid = int(
                last_rowid
            )

        except Exception:
            last_rowid = 0

        rows = self.get_table_rows(
            conn,
            table_name,
            last_rowid
        )

        if not rows:
            return True

        logger.info(
            "%s: found %s new row(s) after rowid %s",
            table_name,
            len(rows),
            last_rowid
        )

        payload = []
        highest_rowid = last_rowid

        for row in rows:

            rowid = row[0]

            telemetry = self.row_to_telemetry(
                columns,
                row,
                table_name
            )

            if telemetry is None:

                logger.error(
                    "%s: failed to convert rowid %s",
                    table_name,
                    rowid
                )

                return False

            payload.append(
                telemetry
            )

            if rowid > highest_rowid:
                highest_rowid = rowid

        if not self.send_telemetry(
            payload
        ):

            logger.error(
                "%s: upload failed; "
                "will retry next cycle",
                table_name
            )

            return False

        state[table_name] = highest_rowid

        self.save_state(
            state
        )

        logger.info(
            "%s: successfully uploaded %s row(s), "
            "last rowid = %s",
            table_name,
            len(payload),
            highest_rowid
        )

        return True

    def upload_pass(self):
        """Scan complete SQLite database and upload new data."""

        if not os.path.exists(
            self.database_path
        ):

            logger.error(
                "Database does not exist: %s",
                self.database_path
            )

            return

        state = self.load_state()

        conn = None

        try:

            conn = sqlite3.connect(
                self.database_path
            )

            tables = self.get_tables(
                conn
            )

            if not tables:

                logger.info(
                    "No SQLite tables found."
                )

                return

            logger.info(
                "Found %s table(s): %s",
                len(tables),
                ", ".join(tables)
            )

            for table_name in tables:

                try:

                    self.upload_table(
                        conn,
                        table_name,
                        state
                    )

                except Exception:

                    logger.exception(
                        "Unhandled error processing table %s",
                        table_name
                    )

        except sqlite3.Error:

            logger.exception(
                "SQLite error"
            )

        except Exception:

            logger.exception(
                "Unexpected uploader error"
            )

        finally:

            if conn is not None:
                conn.close()

    def run(self):
        """Main uploader loop."""

        if not self.is_enabled():

            logger.error(
                "ThingsBoard uploader not configured. "
                "Please set thingsboard_url, "
                "thingsboard_token, database_path "
                "and state_path."
            )

            return

        self.running = True

        logger.info(
            "================================================"
        )

        logger.info(
            "ThingsBoard SQLite uploader starting"
        )

        logger.info(
            "ThingsBoard: %s",
            self.thingsboard_url
        )

        logger.info(
            "Database: %s",
            self.database_path
        )

        logger.info(
            "State: %s",
            self.state_path
        )

        logger.info(
            "Log file: %s",
            LOG_FILE
        )

        logger.info(
            "================================================"
        )

        heartbeat_thread = Thread(
            target=self.heartbeat_loop,
            daemon=True,
            name="ThingsBoardHeartbeat"
        )

        heartbeat_thread.start()

        while self.running:

            try:

                self.upload_pass()

            except KeyboardInterrupt:

                logger.info(
                    "Uploader stopped."
                )

                break

            except Exception:

                logger.exception(
                    "Fatal error in upload loop"
                )

            time.sleep(
                self.check_interval
            )

        self.running = False

        logger.info(
            "ThingsBoard SQLite uploader stopped"
        )

    def stop(self):
        """Stop the uploader."""

        logger.info(
            "ThingsBoard uploader stopping..."
        )

        self.running = False


def start_thingsboard_uploader(config):
    """
    Start ThingsBoard uploader in a background thread.

    Args:
        config: Configuration dictionary.

    Returns:
        ThingsboardUploader instance or None if not enabled.
    """

    uploader = ThingsboardUploader(
        config
    )

    if not uploader.is_enabled():

        logger.error(
            "ThingsBoard uploader is not enabled "
            "(missing configuration)"
        )

        return None

    thread = Thread(
        target=uploader.run,
        daemon=True,
        name="ThingsBoardUploader"
    )

    thread.start()

    return uploader