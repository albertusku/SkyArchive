from datetime import datetime, timedelta

from Logs.logger import prune_log_file, setup_logger


def log_line(moment, message):
    return f"{moment.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} - INFO - {message}\n"


def test_prune_log_file_keeps_recent_and_unparseable_lines(tmp_path):
    log_file = tmp_path / "Procces.log"
    old_line = log_line(datetime.now() - timedelta(days=8), "old")
    recent_line = log_line(datetime.now() - timedelta(days=2), "recent")
    malformed_line = "this line has no parseable timestamp\n"
    log_file.write_text(old_line + recent_line + malformed_line)

    prune_log_file(str(log_file), retention_days=7)

    assert log_file.read_text() == recent_line + malformed_line


def test_prune_log_file_ignores_missing_file(tmp_path):
    prune_log_file(str(tmp_path / "missing.log"), retention_days=7)


def test_setup_logger_creates_parent_directory(tmp_path):
    log_file = tmp_path / "nested" / "Procces.log"

    logger = setup_logger(f"test_logger_{id(log_file)}", str(log_file))
    logger.info("created")

    assert log_file.exists()
