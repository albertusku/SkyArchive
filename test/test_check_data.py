import pandas as pd
import pytest

from Util import check_data
from Util.check_data import check_data_day, find_error


def full_day_rows():
    return [
        {"Year": 2026, "Mes": "June", "Dia": 12, "Hora": f"{hour:02d}:{minute:02d}", "temp (C)": hour}
        for hour in range(24)
        for minute in (0, 30)
    ]


def test_check_data_day_returns_none_with_48_records():
    assert check_data_day(pd.DataFrame(full_day_rows())) is None


def test_find_error_fills_missing_half_hours_from_previous_record_and_sorts():
    rows = full_day_rows()
    rows = [row for row in rows if row["Hora"] not in {"01:00", "13:30"}]
    df = pd.DataFrame(rows)

    fixed = find_error(df)

    assert len(fixed) == 48
    assert fixed["Hora"].tolist() == sorted(fixed["Hora"].tolist())
    filled_0100 = fixed[fixed["Hora"] == "01:00"].iloc[0]
    assert filled_0100["temp (C)"] == 0
    filled_1330 = fixed[fixed["Hora"] == "13:30"].iloc[0]
    assert filled_1330["temp (C)"] == 13


def test_find_error_logs_fixed_hour_ranges(monkeypatch):
    rows = full_day_rows()
    rows = [row for row in rows if row["Hora"] not in {"01:00", "01:30", "13:30"}]
    warnings = []
    monkeypatch.setattr(check_data.logger, "warning", warnings.append)

    find_error(pd.DataFrame(rows))

    assert warnings == ["Fixed missing data hours: 01:00, 01:30, 13:30"]


def test_find_error_missing_first_hour_currently_raises_index_error():
    rows = [row for row in full_day_rows() if row["Hora"] != "00:00"]

    with pytest.raises(IndexError):
        find_error(pd.DataFrame(rows))
