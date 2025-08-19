import pandas as pd
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  
CSV_PATH = ROOT / "data" / "sr.csv"

# --- Expected schema and config ---
EXPECTED_COLUMNS = [
    "Unnamed: 0",
    "notification_number",
    "reference_number",
    "creation_timestamp",
    "completion_timestamp",
    "directorate",
    "department",
    "branch",
    "section",
    "code_group",
    "code",
    "cause_code_group",
    "cause_code",
    "official_suburb",
    "latitude",
    "longitude",
]

ALLOWED_DIRECTORATES = {
    "URBAN MOBILITY", "WATER AND SANITATION", "ENERGY",
    "HUMAN SETTLEMENTS", "URBAN WASTE MANAGEMENT", "FINANCE",
    "COMMUNITY SERVICES AND HEALTH", "SAFETY AND SECURITY",
    "CORPORATE SERVICES", "ECONOMIC GROWTH",
    "OFFICE OF THE CITY MANAGER", "SPATIAL PLANNING AND ENVIRONMENT"
}

MAX_COL_NAN_RATIO = 0.05   
MAX_ROW_NANS = 3           

# --- Fixtures ---
@pytest.fixture(scope="session")
def df():
    df = pd.read_csv(CSV_PATH, low_memory=False)

    for col in ["creation_timestamp", "completion_timestamp"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    for col in ["Unnamed: 0", "notification_number", "reference_number", "latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# --- Tests ---
def test_columns_present(df):
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"


def test_nan_per_column(df):
    nan_ratios = df.isna().sum() / len(df)
    bad = nan_ratios[nan_ratios > MAX_COL_NAN_RATIO]
    assert bad.empty, f"Columns exceeding {MAX_COL_NAN_RATIO*100:.0f}% NaNs: {bad.to_dict()}"


def test_nan_per_row(df):
    nan_per_row = df.isna().sum(axis=1)
    too_many = (nan_per_row > MAX_ROW_NANS).sum()
    assert too_many == 0, f"{too_many} rows have more than {MAX_ROW_NANS} NaNs"


def test_uniqueness(df):
    dup_notif = df["notification_number"].duplicated(keep=False).sum()
    assert dup_notif == 0, f"{dup_notif} duplicate notification_numbers found"

    dup_ref = df["reference_number"].dropna().duplicated(keep=False).sum()
    assert dup_ref == 0, f"{dup_ref} duplicate reference_numbers found"


def test_lat_lon_ranges(df):
    bad_lat = (~df["latitude"].between(-90, 90)).sum()
    bad_lon = (~df["longitude"].between(-180, 180)).sum()
    assert bad_lat == 0 and bad_lon == 0, f"Invalid coords: lat={bad_lat}, lon={bad_lon}"


def test_cross_field_dependency(df):
    bad_dep = (df["completion_timestamp"].notna() & df["creation_timestamp"].isna()).sum()
    assert bad_dep == 0, f"{bad_dep} rows have completion_timestamp but missing creation_timestamp"


def test_directorate_domain(df):
    bad_values = set(df["directorate"].dropna().unique()) - ALLOWED_DIRECTORATES
    assert not bad_values, f"Unexpected directorate values: {bad_values}"


# pytest -q -rA service_request_validation.py