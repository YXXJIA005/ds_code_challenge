import pandas as pd
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  
CSV_PATH = ROOT / "output" / "bv_wind_processed.csv"

@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CSV_PATH)

def test_required_columns(df):
    required = {"wind direction degree", "wind speed m/s", "DateTime"}
    assert required.issubset(df.columns), f"Missing columns: {required - set(df.columns)}"

def test_no_extra_columns(df):
    allowed = {"wind direction degree", "wind speed m/s", "DateTime"}
    extras = set(df.columns) - allowed
    assert not extras, f"Unexpected columns: {extras}"

def test_wind_direction_bounds(df):
    wd = pd.to_numeric(df["wind direction degree"], errors="coerce")
    assert wd.notna().all(), "Wind direction contains NaN/unparseable"
    assert (wd >= 0).all() and (wd <= 360).all(), "Wind direction outside [0, 360]"

def test_wind_speed_bounds(df):
    ws = pd.to_numeric(df["wind speed m/s"], errors="coerce")
    assert ws.notna().all(), "Wind speed contains NaN/unparseable"
    assert (ws >= 0).all(), "Negative wind speeds"
    assert (ws <= 40).all(), "Wind speed unreasonably high (>40 m/s)"


def test_no_duplicates(df):
    assert not df.duplicated().any(), "Duplicate rows found"
