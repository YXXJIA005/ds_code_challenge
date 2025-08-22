
import re
import pandas as pd
import pytest
from pathlib import Path

# ---- Config ----
ROOT = Path(__file__).resolve().parents[1]  
CSV_PATH = ROOT / "data" / "anon_sr_data.csv"

REQUIRED_COLS = [
    "creation_timestamp",
    "completion_timestamp",
    "directorate",
    "department",
    "branch",
    "section",
    "code_group",
    "cause_code_group",  # allowed to be null
    "official_suburb",
    "h3_level8_index",
    "wind direction degree",
    "wind speed m/s",
]

# Columns that must NOT appear in anonymised output
PROHIBITED_COLS = [
    "notification_number",
    "reference_number",
    "latitude",
    "longitude",
    "code",
    "cause_code",
    "address",
    "email",
    "phone",
    "mobile",
    "id_number",
]

LOCAL_TZ = "Africa/Johannesburg"
UTC = "UTC"

# Optional: use h3 if available for strict res check
try:
    import h3
    HAS_H3 = True
except Exception:
    HAS_H3 = False


def _skip_if_missing_file():
    if not CSV_PATH.exists():
        pytest.skip(f"CSV not found at {CSV_PATH.resolve()}")


@pytest.fixture(scope="module")
def df():
    _skip_if_missing_file()
    return pd.read_csv(CSV_PATH)


def _parse_to_local(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, errors="coerce", utc=False)
    # Treat naive as local; if already tz-aware, convert to LOCAL_TZ
    if s.dt.tz is None:
        return s.dt.tz_localize(LOCAL_TZ)
    else:
        return s.dt.tz_convert(LOCAL_TZ)


def _parse_to_utc(series: pd.Series) -> pd.Series:
    return _parse_to_local(series).dt.tz_convert(UTC)


def test_required_columns_present(df):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    assert not missing, f"Missing required columns: {missing}"


def test_prohibited_columns_absent(df):
    present = [c for c in PROHIBITED_COLS if c in df.columns]
    assert not present, f"Prohibited columns present in anonymised data: {present}"


def test_timestamps_parse_and_order(df):
    c = _parse_to_utc(df["creation_timestamp"])
    d = _parse_to_utc(df["completion_timestamp"])

    # creation must always be valid
    assert c.notna().all(), "Unparseable creation_timestamp values"

    # completion may be NaT, but count them
    n_na_complete = d.isna().sum()
    if n_na_complete:
        print(f"INFO: {n_na_complete} rows have NaN completion_timestamp (allowed).")

    # only check order where completion exists
    mask = d.notna()
    non_positive = (d[mask] <= c[mask])
    assert (~non_positive).all(), f"{int(non_positive.sum())} rows have completion <= creation"




def test_creation_timestamp_is_6h_bins(df):
    # Anonymisation spec: temporal accuracy ~ 6 hours
    c_local = _parse_to_local(df["creation_timestamp"])
    good_hours = {0, 6, 12, 18}
    bad = (c_local.dt.minute != 0) | (c_local.dt.second != 0) | (~c_local.dt.hour.isin(good_hours))
    assert (~bad).all(), f"{int(bad.sum())} rows not rounded to 6-hour bins (expected hours {sorted(good_hours)})"


def test_columns_not_null_where_required(df):
    mandatory = ["creation_timestamp", "completion_timestamp", "directorate", "department",
                 "branch", "section", "code_group", "official_suburb", "h3_level8_index"]
    offenders = {c: int(df[c].isna().sum()) for c in mandatory if c in df.columns and df[c].isna().sum() > 0}
    assert not offenders, f"Nulls in mandatory columns: {offenders}"


def _looks_like_h3_res8(idx: str) -> bool:
    if not isinstance(idx, str):
        return False
    if HAS_H3:
        try:
            return h3.get_resolution(idx) == 8
        except Exception:
            return False
    # Heuristic if h3 not installed: 15 lowercase hex characters
    return bool(re.fullmatch(r"[0-9a-f]{15}", idx))


def test_h3_index_valid_res8(df):
    idx = df["h3_level8_index"]
    not_str = (~idx.map(lambda x: isinstance(x, str))).sum()
    assert not_str == 0, f"{not_str} H3 indexes are not strings"
    bad = (~idx.map(_looks_like_h3_res8)).sum()
    msg = "" if HAS_H3 else " (heuristic used; install 'h3' for strict check)"
    assert bad == 0, f"{bad} invalid/non-res8 H3 indexes{msg}"


def test_wind_columns_bounds(df):
    wd = pd.to_numeric(df["wind direction degree"], errors="coerce")
    ws = pd.to_numeric(df["wind speed m/s"], errors="coerce")
    assert wd.notna().all(), "NaN/unparseable wind direction values"
    assert ws.notna().all(), "NaN/unparseable wind speed values"
    assert ((wd >= 0) & (wd <= 360)).all(), "Wind direction outside [0, 360]"
    assert (ws >= 0).all(), "Negative wind speeds"
    assert (ws <= 40).all(), "Unreasonably high wind speeds (>40 m/s)"


def test_text_columns_nonempty(df):
    text_cols = ["official_suburb", "directorate", "department", "branch", "section", "code_group"]
    issues = {}
    for col in text_cols:
        s = df[col].astype(str).str.strip().str.lower()
        empty = (s == "") | s.isin(["nan", "none"])
        cnt = int(empty.sum())
        if cnt:
            issues[col] = cnt
    assert not issues, f"Empty values in text columns: {issues}"


def test_creation_year_2020(df):
    c = _parse_to_local(df["creation_timestamp"])
    not_2020 = (~(c.dt.year == 2020)).sum()
    assert not_2020 == 0, f"{int(not_2020)} rows have creation year != 2020"
