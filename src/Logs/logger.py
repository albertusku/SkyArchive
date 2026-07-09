import logging
import os
from datetime import datetime, timedelta

LOG_RETENTION_DAYS = 7
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S,%f"


def prune_log_file(log_file, retention_days=LOG_RETENTION_DAYS):
    """Keep only log lines from the retention window."""
    if not os.path.exists(log_file):
        return

    cutoff = datetime.now() - timedelta(days=retention_days)
    retained_lines = []

    with open(log_file, "r") as file:
        for line in file:
            try:
                log_date = datetime.strptime(line[:23], LOG_DATE_FORMAT)
            except ValueError:
                retained_lines.append(line)
                continue

            if log_date >= cutoff:
                retained_lines.append(line)

    with open(log_file, "w") as file:
        file.writelines(retained_lines)


def setup_logger(name, log_file, level=logging.DEBUG):
    """ Configura un logger con formato y archivo. """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    prune_log_file(log_file)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
