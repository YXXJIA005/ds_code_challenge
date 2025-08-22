# City of Cape Town - Data Engineer Code Challenge

## Environment Setup

It is recommended to use a **fresh virtual environment** with Python **3.10 or 3.11** to ensure compatibility.

### 1. Create and activate a virtual environment

```bash
# Create environment
python3.10 -m venv .venv
# or
python3.11 -m venv .venv

# Activate environment
source .venv/bin/activate     # Linux / Mac
.venv\Scripts\activate        # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## Project Structure

```
ds_code_challenge/
├── data/                        
├── notebooks/                 
│   ├── 1.data_extraction.ipynb        
│   ├── 2.data_transform.ipynb         
│   └── 3.further_data_transform.ipynb  
├── output/                   
├── tests/                     
│   ├── anon_bv_sr_wind_test.py
│   ├── base_service_request_validation_test.py
│   ├── bv_wind_filled_validation_test.py
│   ├── bv_wind_validation_test.py
│   └── sr_with_wind_validation_test.py
├── img/                       
├── requirements.txt          
├── README.md                 
├── LICENSE                     
└── .gitignore                  
```

## Quick Start

```bash
git clone https://github.com/YXXJIA005/ds_code_challenge.git
cd ds_code_challenge
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute notebooks/1.data_extraction.ipynb
jupyter nbconvert --to notebook --execute notebooks/2.data_transform.ipynb
jupyter nbconvert --to notebook --execute notebooks/3.further_data_transform.ipynb
pytest -v
```

## Dependencies

Key packages include:
- pandas, numpy - data wrangling
- geopandas, shapely, h3 - geospatial processing
- boto3 - AWS s3 access
- pytest, ipytest - testing



## Usage

### Running all notebooks automatically

From the project root, you can execute all notebooks in sequence without opening Jupyter manually:

```bash
jupyter nbconvert --to notebook --execute notebooks/1.data_extraction.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/2.data_transform.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/3.further_data_transform.ipynb --inplace
```
### Running them manually

1. Start Jupyter:
   ```bash
   jupyter notebook
   ```
2. Open and run in sequence:
   - `1.data_extraction.ipynb`
   - `2.data_transform.ipynb`
   - `3.further_data_transform.ipynb`

Please run them them in order, there will be no interaction once you use the run all function in each notebook.

---

## Notebook Summaries

### Part 1 – Data Extraction (`1.data_extraction.ipynb`)
- Retrieves **H3 level-8 geospatial data** directly from the **H3 level-10 GeoJSON** file on S3 using **AWS S3 Select** for efficient querying.  
- Compares and validates the extracted dataset against the official reference file **`city-hex-polygons-8.geojson`** to ensure consistency and completeness.  
- Finally unit tests are done on the functions in the notebook.


---

### Part 2 – Data Transformation (`2.data_transform.ipynb`)
- Assigns H3 indexes to each service request based on its geographic location.
- Compares and validates the enriched dataset against the official reference file **`sr_hex.csv`** to ensure consistency and completeness.
- Finally unit tests are done on the functions in the notebook


---

### Part 3 – Further Transformation (`3.further_data_transform.ipynb`)
- Subsamples **service requests** near the centroid of **Bellville South**.  
- Augments data with **2020 wind speed and direction** from the Bellville South AQM site.  
- Produces an **anonymised dataset**, preserving ~500m spatial accuracy and 6-hour temporal accuracy, while removing personally identifiable fields.  

### Outputs (`output/`)
- `1min_bellville.csv` – Subsampled service requests near Bellville South centroid  
- `bv_wind_processed.csv` – Raw AQM site wind data (processed for Bellville South)  
- `bv_wind_filled.csv` – Bellville Wind data with missing values filled  
- `sr_with_wind.csv` – Bellville Service requests joined with wind data  
- `anon_sr_data.csv` – Final anonymised service requests with wind data for Bellville



## Part 1 - Data Extraction

## Overview

This notebook demonstrates:

- **Credential management**  
  Securely loading credentials from a local JSON file that is downloaded from s3 using requests since I don't have credentials yet or falling back to environment/role configuration.

- **AWS S3 integration**  
  Using `boto3` and `S3 Select` to query and retrieve subsets of large datasets efficiently.
  Also downloads and extracts the rest of the files from s3 for this exercise for verification.

- **Geospatial & tabular extraction**  
  The S3 select then downloads the resolution 8 GeoJSON data for the relevant H3 indexes.
  This is then compared to the official reference file **`city-hex-polygons-8.geojson`** to ensure consistency and completeness.

- **Utility functions**  
  - Safe directory handling (`ensure_dir`, `parent_dir_of`, `resolve_path`)  
  - Human-readable byte formatting (`fmt_bytes`)  
  - CPU/memory usage snapshots (`resource_snapshot`)  
  - Timing instrumentation (`timed` context manager)

- **Data quality checks**  
  Validation of H3 hexagon geospatial datasets for:
  - Missing values  
  - Resolution consistency  
  - Geometry validity  
  - Centroid plausibility  
  - Duplicate indexes  

---

## Part 2 - Data Transformation

## Overview

This notebook focuses on **cleaning, standardising, and enriching** the extracted service request data.  

- **Data cleaning**
  - Handling missing/null values for latitude and longitude data in the service request  

- **H3 resolution level 8 polygon assignment**  
  - Generating H3 resolution-8 indexes from latitude/longitude pairs for the service request

- **Outputs comparison**  
  - Validates the geospatial enrichment output against a pre-enriched service request dataset (with H3 level-8 data) to confirm that the resolution level 8 polygon is correct.

---

# Part 3 — Further Data Transformations

**Objective:** Enrich service requests near Bellville South with local wind conditions and produce a privacy-preserving dataset suitable for analysis.

## Workflow summary

1. **Wind data acquisition (2020, Cape Town)**
   - Fetch hourly wind **speed (m/s)** and **direction (°)**.
   - Keep only Bellville-site columns; normalize names to:
     - `Bellville_South_AQM_Site_m/s`
     - `Bellville_South_AQM_Site_Deg`
   - Export intermediate: `bv_wind_processed.csv`.

2. **Bellville South geometry & centroid**
   - Download the Bellville South polygon from the City of Cape Town Map Viewer.
   - Compute the centroid (WGS84).
   - Define a **radius of 1 minute of latitude = 1 nautical mile ≈ 1.852 km** around the centroid for spatial filtering.

3. **Spatial subsample of service requests**
   - Compute vectorized Haversine distance from the centroid to every service request (using lat/lon from `sr.csv`).
   - Filter to requests where **distance ≤ 1.852 km**.
   - Save subset as `1min_bellville.csv`.

4. **Wind data gap handling**
   - Forward-fill and backward-fill the hourly wind series to bridge short gaps.
   - Export filled series as `bv_wind_filled.csv`.

5. **Time normalization on service requests**
   - Parse timestamps; strip timezone info from `creation_time` and `completion_time`.
   - Create `creation_rounded` by rounding `creation_time` to the nearest **30 minutes**.

6. **Temporal join: service requests ↔ wind**
   - Wind readings are hourly; create a 30-min grid by combining:
     - `:00` (original hourly values), and
     - `:30` (midpoints).
   - For `:30` wind **direction**, use **circular (vector) interpolation** (handles wrap-around at 360°); for **speed**, use the resultant vector magnitude. For other numeric columns, use arithmetic midpoints.
   - Join wind fields to the Bellville South subset on `creation_rounded`.

7. **Anonymization & utility-preserving generalization**
   - **Spatial:** retain only the **H3 index at resolution 8** (avg edge ≈ 461 m; farthest point from centroid ≈ 533 m). This comfortably supports ~500 m location privacy while preserving neighborhood-scale analysis.
   - **Temporal:** reduce precision to **6-hour windows**.
   - **Identifiers removed:**  
     `notification_number`, `reference_number`, `distance_km`, `creation_rounded`, `latitude`, `longitude`, `code`, `cause_code`.  
     *Rationale:* `distance_km` was an intermediate feature used only for the 1.852 km filter; `code`/`cause_code` are highly granular and can make entries uniquely identifiable; raw coordinates and exact rounded times increase re-identification risk.
   - Result is a de-identified dataset with retained analytical value for spatial/temporal patterns.

## Key outputs

- `1min_bellville.csv` — Service requests within **1.852 km** of the Bellville South centroid.  
- `bv_wind_processed.csv` — Bellville wind (selected & renamed columns).  
- `bv_wind_filled.csv` — Bellville wind after forward/backward fill.  
- `bellville_sr_with_wind.parquet/csv` — Joined and anonymized service requests (H3-R8 spatial, 6-hour temporal).

## Notes & implementation details

- **Distance threshold**: “1 minute of latitude” is exactly **1 nautical mile ≈ 1.852 km**; applied as a great-circle radius via Haversine.
- **Circular interpolation**: Wind direction at `:30` uses vector averaging of hour `t` and `t+1` to avoid 360° wrap errors (e.g., 350° and 10° → 0°, not 180°).
- **Why H3 R8?** City-scale analyses (queues, hotspots, trend mapping) work well at R8; it is “borderline” for guaranteed ≤500 m but acceptable for this exercise and materially reduces re-identification risk while keeping spatial signal.  
- **Timezone handling**: Timestamps are made timezone-naïve prior to rounding and joins to ensure consistent matching.

---

## Running Data Quality Tests

Data quality tests are provided for **reproducibility** and **validation**.  
Please run them **after executing all notebooks**, since most outputs are generated by Notebook 3.

The tests check:

- **Base service requests** (`base_service_request_validation_test.py`):  
  Ensures the raw service request dataset has valid schema, timestamps, and no duplicate full rows.
  This one is expected to fail as it the base data set and has many missing columns, duplicate reference numbers and missing latitude and longitude data.

- **Wind data (processed)** (`bv_wind_validation_test.py`):  
  Validates that the Bellville South wind subset has the correct columns, renamed fields, and no unexpected nulls.
  This is expected to fail as there is missing wind direction and speed data.

- **Wind data (filled)** (`bv_wind_filled_validation_test.py`):  
  Confirms forward/backward fill was applied correctly and that missing values were minimized.
  This is expected to pass as the filling strategy should effectively handle missing data.

- **Service requests with wind joined** (`sr_with_wind_validation_test.py`):  
  Verifies correct temporal joins between service requests and wind data, checks for unmatched rows, and validates 30-minute alignment.
  This is expected to pass all but one test, where it fails for having too many missing data in some fields.

- **Anonymized service requests** (`anon_bv_sr_wind_test.py`):  
  Ensures dropped columns are not present, temporal generalization is applied (6-hour rounding), and spatial data is kept only at H3 resolution 8.
  This is expected to pass all but one test, where it fails for having too many missing data in some fields.

### How to run the tests

From the project root:

```bash
pytest -v

```

To run them one by one:

```bash
pytest -v tests/base_service_request_validation_test.py
pytest -v tests/bv_wind_validation_test.py
pytest -v tests/bv_wind_filled_validation_test.py
pytest -v tests/sr_with_wind_validation_test.py
pytest -v tests/anon_bv_sr_wind_test.py

```