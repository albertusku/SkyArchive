import pandas as pd
from Util import check_data


def test_missing_slots_are_reported_without_inventing_rows(monkeypatch):
    rows = pd.DataFrame([{"Hora": "00:00"}, {"Hora": "00:00"}])
    original = rows.copy(deep=True)
    warnings = []
    monkeypatch.setattr(check_data.logger, "warning", warnings.append)
    assert check_data.check_data_day(rows) is None
    pd.testing.assert_frame_equal(rows, original)
    assert any("Missing data hours" in message for message in warnings)
    assert any("Duplicate data hours" in message for message in warnings)
