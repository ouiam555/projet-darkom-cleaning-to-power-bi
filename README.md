# Darkom.ma — Real Estate Data Pipeline

End-to-end ETL pipeline that cleans Moroccan property listings from **darkom.ma** and loads them into a PostgreSQL star schema connected to Power BI.

**Stack:** Python · pandas · psycopg2 · SQLAlchemy · PostgreSQL · Power BI

---

## Pipeline

```
data/darkom.csv  →  staging.annonces_raw  →  clean.annonces  →  bi_schema  →  Power BI
     (raw)              (TEXT, no transform)    (typed + enriched)  (star schema)  (4 dashboards)
```

Run everything with:

```bash
python main.py   # calls load_staging.py → clean.py → load_warehouse.py in sequence
```

---

## Project Structure

```
├── main.py                    # Orchestrator — runs 3 stages via os.system()
├── .env                       # DB credentials (you must create this)
├── requirements.txt           # Pinned Python dependencies
├── staging.log                # Auto-generated load log
├── darkom.pbix                # Power BI report (4 dashboards)
│
├── data/
│   └── darkom.csv             # 1,508 listings · 13 columns · Jan 2023–Dec 2024
│
├── scripts/
│   └── clean.py               # Full cleaning + feature engineering → clean.annonces
│
├── loads/
│   ├── load_staging.py        # CSV → staging.annonces_raw (raw load, all TEXT)
│   └── load_warehouse.py      # clean.annonces → bi_schema dims + fact table
│
├── warehouse/
│   └── warehouse.sql          # DDL: DROP/CREATE all bi_schema tables
│
└── docs/
    ├── prix.png               # Price distribution (skew plot)
    ├── surface.png            # Surface area distribution
    ├── nb_chambres.png        # Bedroom count distribution
    └── nb_salles_bain.png     # Bathroom count distribution
```

---

## Dataset — `data/darkom.csv`

| Field | Description | Missing |
|---|---|---|
| `annonce_id` | Unique listing ID (e.g. `ANO000343`) | 0% |
| `date_publication` | Publication date | 5% |
| `titre` | Listing title | 0% |
| `ville` | City — 31 unique values, inconsistent casing | 0% |
| `quartier` | Neighbourhood | **27.5%** |
| `type_bien` | Appartement · Villa · Terrain · Bureau · Duplex | 2.5% |
| `transaction` | Vente (69%) · Location (28%) | 2.5% |
| `prix` | Price in MAD — range: 120 to 80,000,000 | 0% |
| `surface` | Surface area in m² — range: 8 to 3,000 | 0% |
| `nb_chambres` | Number of bedrooms | 8.6% |
| `nb_salles_bain` | Number of bathrooms | 6.9% |
| `etage` | Floor number | **15.4%** |
| `annee_construction` | Year built | **13.5%** |

---

## Setup

### 1. Create `.env`

```env
db_host=localhost
db_port=5432
db_name=darkom_dwh
db_user=your_user
db_password=your_password
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Fix hardcoded paths

`load_staging.py` and `load_warehouse.py` contain absolute Windows paths that must be changed before running on any other machine:

```python
# load_staging.py — change this:
load_csv(conn, r"C:\Users\HP\Desktop\projet darkom\data\darkom.csv")
# to:
load_csv(conn, Path(__file__).resolve().parent.parent / "data" / "darkom.csv")

# load_warehouse.py — change this:
with open(r"C:\Users\HP\Desktop\projet darkom\warehouse\warehouse.sql", "r") as f:
# to:
with open(Path(__file__).resolve().parent.parent / "warehouse" / "warehouse.sql") as f:
```

---

## Stage 1 — Staging (`loads/load_staging.py`)

- Connects to PostgreSQL via `psycopg2`
- **Drops and recreates** `staging.annonces_raw` on every run
- Loads the CSV row-by-row using `csv.DictReader` with parameterised inserts
- All 13 business columns stored as `TEXT` — no transformations
- Adds a `loaded_at TIMESTAMP DEFAULT NOW()` column automatically
- Validates row count after insert and logs result to `staging.log`

---

## Stage 2 — Cleaning (`scripts/clean.py`)

Reads from `staging.annonces_raw`, applies all transformations, writes to `clean.annonces`.

### Transformations in order

**1. Deduplication**
- Drops exact duplicate rows
- Drops rows where `transaction` or `type_bien` is empty string

**2. Type casting**
| Column | Cast |
|---|---|
| `date_publication` | `datetime` (errors → NaT) |
| `prix`, `surface` | `float` |
| `nb_chambres`, `nb_salles_bain`, `etage`, `annee_construction` | `Int64` (nullable) |

**3. Missing value imputation**
| Column | Strategy |
|---|---|
| `quartier` | `"Inconnu"` |
| `etage` | `0` |
| `annee_construction`, `nb_chambres`, `nb_salles_bain` | median |
| `date_publication`, `transaction` | drop row |

**4. Outlier handling**
- Computes skewness and plots histograms for `prix`, `surface`, `nb_chambres`, `nb_salles_bain` (saved to `docs/`)
- Prints IQR outlier counts per column (diagnostic only — not removed)
- Drops rows where `prix ≤ 0` or `surface ≤ 0`

**5. Feature engineering**
| New column | Logic |
|---|---|
| `prix_m2` | `prix / surface` |
| `age_bien` | `2024 − annee_construction` |
| `categorie_prix` | `< 500K` → Économique · `500K–1.5M` → Moyen · `1.5M–5M` → Haut standing · `> 5M` → Luxe |
| `categorie_surface` | `< 80m²` → Petit · `80–150m²` → Moyen · `> 150m²` → Grand |
| `annee_pub` | year from `date_publication` |
| `mois_pub` | month from `date_publication` |
| `trimestre_pub` | quarter from `date_publication` |

**6. Text standardisation**
- `.str.strip().str.title()` applied to `ville`, `type_bien`, `transaction`, `quartier`
- City alias mapping: `Casa` / `Csa` → `Casablanca`, plus casing fixes (`MARRAKECH` → `Marrakech`, `fès` → `Fès`)

---

## Stage 3 — Warehouse (`loads/load_warehouse.py`)

1. Executes `warehouse.sql` to drop and recreate all `bi_schema` tables
2. Reads full `clean.annonces` into a DataFrame
3. Builds each dimension by calling `.drop_duplicates()` on the relevant columns, then appends to the DB
4. Re-reads each dimension table to retrieve auto-generated surrogate keys (`SERIAL PRIMARY KEY`)
5. Merges surrogate keys back onto the main DataFrame
6. Inserts `fact_annonces` with all FK references resolved

---

## Star Schema (`bi_schema`)

```
         dim_temps              dim_localisation
         ─────────              ────────────────
         date_id (PK)           localisation_id (PK)
         date_publication       ville
         annee_pub              quartier
         mois_pub
         trimestre_pub
               │                       │
               └──────────┬────────────┘
                           │
                    fact_annonces
                    ─────────────────────
                    annonce_id (PK)
                    date_id (FK)
                    localisation_id (FK)
                    bien_id (FK)
                    transaction_id (FK)
                    categorie_prix_id (FK)
                    prix · surface · prix_m2 · age_bien
                           │
               ┌───────────┼───────────┐
               │           │           │
          dim_bien   dim_transaction  dim_categorie_prix
          ────────   ───────────────  ──────────────────
          bien_id    transaction_id   categorie_prix_id
          type_bien  transaction      categorie_prix
          categorie_surface
          nb_chambres
          nb_salles_bain
          etage
```

---

## Power BI Dashboards (`darkom.pbix`)

| Dashboard | Contents |
|---|---|
| **Vue globale** | Total listings KPI, Vente vs Location split, distribution by city, monthly volume trend |
| **Analyse des prix** | Avg price & price/m² KPIs, price by `type_bien`, market segment breakdown |
| **Analyse géographique** | Price heatmap by city & quartier, city rankings, dynamic slicers |
| **Analyse des tendances** | Monthly/quarterly time series, YoY comparison, price category evolution |

---

## Dependencies

| Package | Version | Role |
|---|---|---|
| `pandas` | 3.0.3 | Data manipulation |
| `numpy` | 2.4.6 | Numerical ops |
| `psycopg2-binary` | 2.9.12 | PostgreSQL driver |
| `SQLAlchemy` | 2.0.49 | DB engine / ORM |
| `python-dotenv` | 1.2.2 | `.env` config loading |
| `matplotlib` | 3.10.9 | EDA plots |
| `seaborn` | 0.13.2 | EDA plots |
| `pillow` | 12.2.0 | Image backend for matplotlib |

---

## Known Issues

- **Hardcoded paths** — absolute Windows paths in `load_staging.py` and `load_warehouse.py` (see Setup)
- **Full refresh only** — every run drops and recreates all tables; no incremental load
- **`age_bien` hardcoded to 2024** — should use `datetime.now().year`
- **IQR outliers not removed** — detection is printed/plotted but rows are kept
- **Row-by-row inserts in `clean.py`** — slow for large datasets; `execute_batch` or `COPY` would be faster
