# 🎮 Hardware Recommendation & Game Intelligence Engine

> A Deep Learning + ETL project that classifies PC hardware components (CPU/GPU), ingests benchmark data into PostgreSQL, and enriches it with live game metadata from the IGDB API.

---

## 📌 Project Overview

This project is a full-stack data pipeline and image classification system built for a **Semester 5 Deep Learning** course. It:

1. **Classifies** hardware component images as either a **CPU or GPU** using a fine-tuned VGG16 CNN model served via Flask.
2. **Extracts, transforms, and loads** FPS benchmark data and GPU specs into a local PostgreSQL database using an automated ETL pipeline.
3. **Enriches** game data with live metadata (genres, release dates, platforms) from the **IGDB API** (powered by Twitch OAuth).
4. **Exports** a clean, joined dataset (`clean_training_data.csv`) ready for downstream machine learning model training.

---

## 🗂️ Project Structure

```
pro/
├── app.py                  ← Flask web server (image upload + CNN inference)
├── model.py                ← VGG16 transfer learning training script
├── etl_pipeline.py         ← Full ETL: Extract → Transform → IGDB → Load → Export
├── requirements.txt        ← Python dependencies (pinned versions)
├── .env.example            ← Credential template (copy to .env and fill in)
├── .gitignore              ← Excludes secrets, large files, and OS junk
│
├── dataset/
│   ├── CPU/                ← CPU training images (11 images)
│   └── GPU/                ← GPU training images (22 images)
│
├── test_samples/           ← Isolated evaluation images (not used in training)
│
├── model/
│   └── product_model.h5   ← [NOT COMMITTED] Trained VGG16 weights (~203 MB)
│                             Run model.py to generate locally.
│
├── templates/
│   └── index.html          ← Upload form UI
│
└── static/
    └── uploads/            ← Runtime image uploads (excluded from git)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Web Framework** | Flask 3.x |
| **Deep Learning** | TensorFlow 2.x / Keras |
| **Pre-trained Model** | VGG16 (ImageNet weights, transfer learning) |
| **Image Processing** | Pillow (PIL) |
| **Data Processing** | Pandas, NumPy |
| **Database ORM** | SQLAlchemy 2.x |
| **Database Driver** | psycopg2-binary |
| **Database** | PostgreSQL (local) |
| **Game Metadata API** | IGDB API (via Twitch OAuth2) |
| **Environment Vars** | python-dotenv |

---

## 🗄️ Database Schema

Three tables in PostgreSQL (`DB_NAME=postgres`):

```
hardware_specs          games               fps_benchmarks
──────────────          ──────────          ──────────────
id (PK)                 id (PK)             id (PK)
cpu_name                game_name_raw       hardware_spec_id (FK)
cpu_cores               game_name_clean     game_id (FK)
cpu_threads             igdb_id             resolution
cpu_base_clock_mhz      igdb_summary        setting
cpu_turbo_clock_mhz     igdb_genres         fps
cpu_tdp_watts           igdb_platforms      ingested_at
cpu_process_nm          igdb_first_release_date
cpu_cache_l3_kb         min_req_cpu / gpu / ram
gpu_name                ingested_at
gpu_architecture
gpu_memory_gb (vram)
gpu_memory_type
gpu_base_clock_mhz
gpu_boost_clock_mhz
gpu_bandwidth_gb_s
gpu_shading_units
gpu_fp32_tflops
... (full spec columns)
ingested_at
```

**Relationships:**
- `fps_benchmarks.hardware_spec_id` → `hardware_specs.id`
- `fps_benchmarks.game_id` → `games.id`

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Koverthanan-git/Game_recomendation.git
cd Game_recomendation
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```ini
DB_USER=root
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres

# Optional — for IGDB game metadata enrichment
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
```

> **Get IGDB credentials** (free): [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps)  
> If you skip IGDB, the pipeline still runs — game metadata columns will be `NULL`.

### 5. Download Datasets (Kaggle)

The large dataset files are not committed. Download them and place them in `dataset/`:

| File | Kaggle Link |
|---|---|
| `fps_benchmark.csv` | [GPU Benchmark Dataset](https://www.kaggle.com/) |
| `gpus.json` | [GPU Specs Dataset](https://www.kaggle.com/) |

```
dataset/
├── fps_benchmark.csv   ← ~8 MB, 24,624 rows
└── gpus.json           ← ~15 MB, 188 GPU entries
```

### 6. Set Up PostgreSQL

Ensure PostgreSQL is running locally:

```bash
# macOS (Homebrew)
brew services start postgresql

# Check connection
pg_isready -h localhost -p 5432
```

---

## 🚀 Running the Project

### A) Train the CNN Model

> Only needed if `model/product_model.h5` doesn't exist.

```bash
python3 model.py
```

This will:
- Load images from `dataset/CPU/` and `dataset/GPU/`
- Fine-tune VGG16 on 2 classes for 10 epochs
- Save the model to `model/product_model.h5`

### B) Run the Flask Web App (Image Classifier)

```bash
python3 app.py
```

Open [http://localhost:5000](http://localhost:5000) and upload a CPU or GPU image to get a prediction.

### C) Run the ETL Pipeline

```bash
python3 etl_pipeline.py
```

This will:
1. **Extract** — Read `fps_benchmark.csv` + `gpus.json`
2. **Transform** — Normalize strings, coerce numerics, deduplicate hardware combos & games
3. **IGDB Enrich** — Fetch genres, release dates, platforms for all 24 games via API
4. **Load** — Insert into 3 PostgreSQL tables (`hardware_specs`, `games`, `fps_benchmarks`)
5. **Export** — Run a SQL JOIN and save `clean_training_data.csv` to the project root

Expected output:
```
hardware_specs   → 513 rows
games            → 24 rows
fps_benchmarks   → 24,624 rows
clean_training_data.csv → 24,624 rows × 27 columns
```

---

## 📊 ETL Pipeline — Data Flow

```
fps_benchmark.csv (24,624 rows)
        │
        ├── deduplicate (cpu_name + gpu_name) ──→ hardware_specs  (513 rows)
        ├── deduplicate game_name             ──→ games            (24 rows)
        │                                              │
        │                                         IGDB API ──→ genres, platforms,
        │                                                        release dates
        └── all benchmark rows with FK refs   ──→ fps_benchmarks  (24,624 rows)

gpus.json (188 GPU entries)
        └── parsed for GPU spec enrichment in hardware_specs

PostgreSQL JOIN (hardware_specs + games + fps_benchmarks)
        └── clean_training_data.csv (27 features + fps target)
```

---

## 📁 Output: `clean_training_data.csv`

The exported CSV contains these **27 columns** ready for ML training:

| Group | Columns |
|---|---|
| **CPU Features** | `cpu_name`, `cpu_cores`, `cpu_threads`, `cpu_base_clock_mhz`, `cpu_turbo_clock_mhz`, `cpu_tdp_watts`, `cpu_process_nm`, `cpu_cache_l3_kb` |
| **GPU Features** | `gpu_name`, `gpu_architecture`, `gpu_vram_gb`, `gpu_memory_type`, `gpu_base_clock_mhz`, `gpu_boost_clock_mhz`, `gpu_memory_bus_bits`, `gpu_bandwidth_gb_s`, `gpu_shading_units`, `gpu_tmus`, `gpu_rops`, `gpu_fp32_tflops`, `gpu_process_nm`, `gpu_transistors_m` |
| **Game Info** | `game_name`, `igdb_genres` |
| **Test Conditions** | `resolution`, `setting` |
| **🎯 Target** | **`fps`** |

---

## 🔒 Security Notes

- **`.env` is in `.gitignore`** — credentials are never committed.
- Use `.env.example` as a safe template (no real values).
- `model/product_model.h5` is excluded (203 MB — too large for GitHub).
- `dataset/*.csv` and `dataset/*.json` are excluded (8–15 MB each).
- `clean_training_data.csv` is excluded (reproducible via `etl_pipeline.py`).

---

## 📈 Results

| Metric | Value |
|---|---|
| Model Classes | GPU vs CPU |
| Training Images | 33 (11 CPU + 22 GPU) |
| Model Backbone | VGG16 (ImageNet pretrained) |
| Training Epochs | 10 |
| Database Records | 25,161 total (across 3 tables) |
| Games Covered | 24 titles |
| Hardware Combos | 513 unique CPU+GPU pairs |

---

## 🧾 License

This project is developed for academic purposes as part of **Semester 5 — Deep Learning** coursework.

---

## 👨‍💻 Author

**Koverthanan M**  
GitHub: [@Koverthanan-git](https://github.com/Koverthanan-git)
