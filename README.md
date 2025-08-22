# City of Cape Town - Data Engineer Code Challenge

---

## Environment Setup

It is recommended to use a **fresh virtual environment** with Python **3.10 or 3.11** to ensure compatibility.  
If you already have a clean environment, you can install dependencies directly with:

```bash
pip install -r requirements.txt
```

### Create and activate a virtual environment

```bash
# Create environment
python3.10 -m venv .venv

# Activate environment
source .venv/bin/activate     # Linux / Mac
.venv\Scripts\activate        # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## Project Structure
```bash
ds_code_challenge/
│
├── data/                        
│   ├── 1min_bellville.csv
│   ├── anon_sr_data.csv
│   ├── bv_wind_filled.csv
│   ├── bv_wind_processed.csv
│   ├── city-hex-polygons-8-10.geojson   
│   ├── city-hex-polygons-8.geojson      
│   ├── hex8_features.js
│   ├── sr_hex_truncated.csv
│   ├── sr_hex.csv(.gz)                 
│   ├── sr_with_wind.csv
│   └── Wind_direction_and_speed_2020.ods
│
├── notebooks/                 
│   ├── 1.data_extraction.ipynb        
│   ├── 2.data_transform.ipynb         
│   └── 3.further_data_transform.ipynb  
│
├── output/                   
│   ├── 1min_bellville.csv
│   ├── anon_sr_data.csv
│   ├── bv_wind_filled.csv
│   ├── bv_wind_processed.csv
│   └── sr_with_wind.csv
│
├── tests/                     
│   ├── anon_bv_sr_wind_test.py
│   ├── base_service_request_validation_test.py
│   ├── bv_wind_filled_validation_test.py
│   ├── bv_wind_validation_test.py
│   └── sr_with_wind_validation_test.py
│
├── img/                       
│
├── requirements.txt          
├── README.md                 
├── LICENSE                     
└── .gitignore                  
```

---
##  Usage

### Running the notebooks

1. Start Jupyter:
   ```bash
   jupyter notebook
   ```
2. Open and run in sequence:
   - `1.data_extraction.ipynb`
   - `2.data_transform.ipynb`
   - `3.further_data_transform.ipynb`

Please run them them in order, there will be no interaction once you run all in the notebook.

---

## 📖 Notebook Summaries

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
- 
### Outputs (`output/`)
- `1min_bellville.csv` – Subsampled service requests near Bellville South centroid  
- `bv_wind_processed.csv` – Raw AQM site wind data (processed for Bellville South)  
- `bv_wind_filled.csv` – Bellville Wind data with missing values filled  
- `sr_with_wind.csv` – Bellville Service requests joined with wind data  
- `anon_sr_data.csv` – Final anonymised service requests with wind data for Bellville



## Part 1 - Data Extraction

## 📖 Overview

This notebook demonstrates:

- 🔑 **Credential management**  
  Securely loading credentials from a local JSON file or falling back to environment/role configuration.

- ☁️ **AWS S3 integration**  
  Using `boto3` and `S3 Select` to query and retrieve subsets of large datasets efficiently.

- 🌍 **Geospatial & tabular extraction**  
  Handling `GeoJSON`, `JSONL`, and `CSV` data, including decompression of `.gz` files.

- 🛠 **Utility functions**  
  - Safe directory handling (`ensure_dir`, `parent_dir_of`, `resolve_path`)  
  - Human-readable byte formatting (`fmt_bytes`)  
  - CPU/memory usage snapshots (`resource_snapshot`)  
  - Timing instrumentation (`timed` context manager)

- ✅ **Data quality checks**  
  Validation of H3 hexagon geospatial datasets for:
  - Missing values  
  - Resolution consistency  
  - Geometry validity  
  - Centroid plausibility  
  - Duplicate indexes  

---

## 🧪 Running Tests

Data quality tests are provided for reproducibility and validation. Please run it after running all notebooks as the data is mostly produced by notebook 3.

```bash
pytest -q tests/
```

---

