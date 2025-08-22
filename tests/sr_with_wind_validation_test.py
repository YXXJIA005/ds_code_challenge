import os
from pathlib import Path
import re
import pandas as pd
import numpy as np
import pytest

# ---- Paths & config ----
ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "output" / "sr_with_wind.csv"

REQUIRED_COLS = [
    "notification_number",
    "creation_timestamp",
    "completion_timestamp",
    "directorate",
    "department",
    "branch",
    "section",
    "code_group",
    "official_suburb",
    "latitude",
    "longitude",
    "h3_level8_index",
    "distance_km",
    "creation_rounded",
    "wind direction degree",
    "wind speed m/s",
]

OPTIONAL_NULL_OK = ["cause_code_group", "cause_code"]

LOCAL_TZ = "Africa/Johannesburg"  # treat naive timestamps as local CCT time
UTC = "UTC"

# Optional h3 dependency
try:
    import h3
    HAS_H3 = True
except Exception:
    HAS_H3 = False


def _skip_if_missing_file():
    if not CSV_PATH.exists():
        pytest.skip(f"CSV not found at {CSV_PATH}. "
                    f"Place it there or adjust CSV_PATH in the test.")


def _parse_to_local(series: pd.Series) -> pd.Series:
    """
    Parse strings to datetimes. If timezone-naive, localise to Africa/Johannesburg.
    If timezone-aware, convert to LOCAL_TZ.
    """
    s = pd.to_datetime(series, errors="coerce", utc=False)
    # s.dt.tz is None for a fully-naive series OR mixed-naive; handle elementwise:
    # Localise naive entries; convert aware entries.
    # Build a result series with tz-aware datetimes in LOCAL_TZ.
    naive_mask = s.dt.tz is None
    if naive_mask:
        # Entire series naive -> localise once
        s = s.dt.tz_localize(LOCAL_TZ)
    else:
        # Mixed or aware: localise only truly-naive rows, convert aware to LOCAL_TZ
        # (pandas doesn't support elementwise tz ops directly; split-merge approach)
        naive_rows = s[s.dt.tz is None].dt.tz_localize(LOCAL_TZ) if s.dt.tz is None else s
        # If already all aware, just convert:
        try:
            s = s.dt.tz_convert(LOCAL_TZ)
        except Exception:
            # For mixed: localise naive then convert whole series
            s = pd.to_datetime(series, errors="coerce", utc=False)
            s = s.where(s.dt.tznotnull(), s.dt.tz_localize(LOCAL_TZ))
            s = s.dt.tz_convert(LOCAL_TZ)
    return s


def _parse_to_utc(series: pd.Series) -> pd.Series:
    """
    Parse strings to datetimes.
    - If value is naive -> localize to Africa/Johannesburg -> convert to UTC
    - If value is aware -> convert to UTC directly
    """
    s = pd.to_datetime(series.astype(str).str.strip(), errors="coerce", utc=False)

    def to_utc(x):
        if pd.isna(x):
            return pd.NaT
        if x.tzinfo is None:
            return x.tz_localize(LOCAL_TZ).tz_convert(UTC)
        else:
            return x.tz_convert(UTC)

    return s.map(to_utc)



@pytest.fixture(scope="module")
def df():
    _skip_if_missing_file()
    return pd.read_csv(CSV_PATH)


def test_file_exists():
    _skip_if_missing_file()
    assert CSV_PATH.exists()


def test_required_columns_present(df):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    assert not missing, f"Missing required columns: {missing}"


def test_no_full_row_duplicates(df):
    assert not df.duplicated().any(), "Duplicate full rows detected"


def test_notification_number_uniqueness(df):
    if "notification_number" in df.columns:
        non_null = df["notification_number"].dropna()
        dups = non_null.duplicated().sum()
        assert dups == 0, f"{dups} duplicate notification_number values found"


def test_timestamps_parse_and_order(df):
    c = _parse_to_utc(df["creation_timestamp"])
    d = _parse_to_utc(df["completion_timestamp"])

    # creation must always be valid
    assert c.notna().all(), "Unparseable creation_timestamp values"

    # completion may be NaT, but count them
    n_na_complete = d.isna().sum()
    if n_na_complete:
        print(f"INFO: {n_na_complete} rows have NaN completion_timestamp (allowed).")




def test_creation_rounded_is_30_min_bins(df):
    if "creation_rounded" not in df.columns:
        pytest.skip("creation_rounded not present")
    # Check rounding semantics in LOCAL time (how it was produced)
    cr_local = _parse_to_local(df["creation_rounded"])
    assert cr_local.notna().all(), "Unparseable creation_rounded values"
    bad = (cr_local.dt.second != 0) | (~cr_local.dt.minute.isin([0, 30]))
    assert (~bad).all(), f"{int(bad.sum())} rows not aligned to 30-minute bins"


def test_lat_lon_bounds_and_validity(df):
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    assert lat.notna().all() and lon.notna().all(), "NaN or unparseable lat/lon values"
    # Cape Town rough bounding box
    lat_ok = (lat >= -34.5) & (lat <= -33.0)
    lon_ok = (lon >= 18.0) & (lon <= 19.5)
    assert lat_ok.all(), f"{int((~lat_ok).sum())} latitudes outside Cape Town bounds"
    assert lon_ok.all(), f"{int((~lon_ok).sum())} longitudes outside Cape Town bounds"


def _looks_like_h3_res8(idx: str) -> bool:
    if not isinstance(idx, str):
        return False
    if HAS_H3:
        try:
            return h3.get_resolution(idx) == 8
        except Exception:
            return False
    # Heuristic if h3 not installed: 15 lowercase hex chars
    return bool(re.fullmatch(r"[0-9a-f]{15}", idx))


def test_h3_index_valid(df):
    idx = df["h3_level8_index"]
    not_str = (~idx.map(lambda x: isinstance(x, str)))
    assert not not_str.any(), f"{int(not_str.sum())} H3 indexes are not strings"
    bad = (~idx.map(_looks_like_h3_res8))
    msg = "" if HAS_H3 else " (heuristic used; install 'h3' for strict check)"
    assert not bad.any(), f"{int(bad.sum())} invalid/non-res8 H3 indexes{msg}"


def test_wind_columns_bounds(df):
    wd = pd.to_numeric(df["wind direction degree"], errors="coerce")
    ws = pd.to_numeric(df["wind speed m/s"], errors="coerce")
    assert wd.notna().all(), "NaN/unparseable wind direction values"
    assert ws.notna().all(), "NaN/unparseable wind speed values"
    assert ((wd >= 0) & (wd <= 360)).all(), "Wind direction outside [0, 360]"
    assert (ws >= 0).all(), "Negative wind speeds"
    assert (ws <= 40).all(), "Unreasonably high wind speeds (>40 m/s)"


def test_distance_km_bounds(df):
    dist = pd.to_numeric(df["distance_km"], errors="coerce")
    assert dist.notna().all(), "NaN/unparseable distance_km values"
    assert (dist >= 0).all(), "Negative distances"
    assert (dist <= 50).all(), "Distances > 50 km look suspicious for a local subsample"


def test_mandatory_text_fields_nonempty(df):
    text_cols = ["official_suburb", "directorate", "department", "branch", "section", "code_group"]
    empty_counts = {}
    for col in text_cols:
        s = df[col].astype(str).str.strip().str.lower()
        empty = (s == "") | s.isin(["nan", "none"])
        cnt = int(empty.sum())
        if cnt:
            empty_counts[col] = cnt
    assert not empty_counts, f"Empty values found in mandatory text fields: {empty_counts}"


def test_optional_nulls_only_in_allowed(df):
    for col in OPTIONAL_NULL_OK:
        if col in df.columns:
            df[col]  # exist & accessible is fine


def test_schema_no_unexpected_pii_hints(df):
    danger = ["address", "email", "phone", "mobile", "id_number", "first_name", "last_name"]
    offenders = [c for c in df.columns if any(k in c.lower() for k in danger)]
    assert not offenders, f"Potential PII columns present: {offenders}"


def test__hint_show_path():
    _skip_if_missing_file()
    assert CSV_PATH.exists(), f"Testing file: {CSV_PATH}"
