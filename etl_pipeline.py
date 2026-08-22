"""
=============================================================
  ETL Pipeline — Hardware & Gaming Data → PostgreSQL
  Project: Hardware Recommendation Engine
  File:    etl_pipeline.py
=============================================================
  Stages:
    1. EXTRACT  — Read fps_benchmark.csv + gpus.json
    2. TRANSFORM — Clean, normalize, deduplicate
    3. IGDB     — Fetch game metadata via Twitch OAuth
    4. LOAD     — Insert into PostgreSQL via SQLAlchemy
=============================================================
"""

import os
import re
import json
import sys
import logging
import requests
import pandas as pd

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, text,
    Column, Integer, String, Float, BigInteger, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, Session

# ─────────────────────────────────────────────
#  Logging setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("etl")

# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DATASET_DIR = BASE_DIR / "dataset"
FPS_CSV     = DATASET_DIR / "fps_benchmark.csv"
GPU_JSON    = DATASET_DIR / "gpus.json"
ENV_FILE    = BASE_DIR / ".env"

# ─────────────────────────────────────────────
#  Load environment
# ─────────────────────────────────────────────
if not ENV_FILE.exists():
    log.error(".env file not found. Please create one at: %s", ENV_FILE)
    sys.exit(1)

load_dotenv(ENV_FILE)

DB_USER       = os.getenv("DB_USER", "root")
DB_PASS       = os.getenv("DB_PASSWORD", "")
DB_HOST       = os.getenv("DB_HOST", "localhost")
DB_PORT       = os.getenv("DB_PORT", "5432")
DB_NAME       = os.getenv("DB_NAME", "postgres")
CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ─────────────────────────────────────────────
#  SQLAlchemy ORM Models
# ─────────────────────────────────────────────
Base = declarative_base()


class HardwareSpec(Base):
    """Unique CPU+GPU hardware combination with full spec details."""
    __tablename__ = "hardware_specs"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    cpu_name              = Column(String(200), nullable=False)
    cpu_cores             = Column(Integer)
    cpu_threads           = Column(Integer)
    cpu_base_clock_mhz    = Column(Float)
    cpu_turbo_clock_mhz   = Column(Float)
    cpu_tdp_watts         = Column(Float)
    cpu_process_nm        = Column(Float)
    cpu_cache_l3_kb       = Column(Float)
    gpu_name              = Column(String(200), nullable=False)
    gpu_architecture      = Column(String(100))
    gpu_memory_gb         = Column(Float)
    gpu_memory_type       = Column(String(50))
    gpu_base_clock_mhz    = Column(Float)
    gpu_boost_clock_mhz   = Column(Float)
    gpu_memory_bus_bits   = Column(Float)
    gpu_bandwidth_gb_s    = Column(Float)
    gpu_shading_units     = Column(Integer)
    gpu_tmus              = Column(Integer)
    gpu_rops              = Column(Integer)
    gpu_fp32_tflops       = Column(Float)
    gpu_process_nm        = Column(Float)
    gpu_transistors_m     = Column(Float)
    gpu_directx           = Column(String(50))
    gpu_vulkan            = Column(String(50))
    gpu_opengl            = Column(String(50))
    ingested_at           = Column(DateTime, default=datetime.utcnow)


class Game(Base):
    """Unique game entries, optionally enriched with IGDB metadata."""
    __tablename__ = "games"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    game_name_raw           = Column(String(200), nullable=False, unique=True)
    game_name_clean         = Column(String(200))
    igdb_id                 = Column(BigInteger)
    igdb_summary            = Column(Text)
    igdb_genres             = Column(Text)
    igdb_platforms          = Column(Text)
    igdb_first_release_date = Column(String(50))
    min_req_os              = Column(Text)
    min_req_cpu             = Column(Text)
    min_req_gpu             = Column(Text)
    min_req_ram             = Column(Text)
    ingested_at             = Column(DateTime, default=datetime.utcnow)


class FPSBenchmark(Base):
    """Per-row benchmark readings: hardware + game + resolution + setting -> FPS."""
    __tablename__ = "fps_benchmarks"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    hardware_spec_id = Column(Integer, ForeignKey("hardware_specs.id"), nullable=False)
    game_id          = Column(Integer, ForeignKey("games.id"), nullable=False)
    resolution       = Column(String(20))
    setting          = Column(String(50))
    fps              = Column(Float)
    ingested_at      = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

def _clean_str(val) -> str:
    """Strip b'' wrapper, normalize whitespace, lowercase, remove trailing junk."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    s = re.sub(r"^b'(.*)'$", r"\1", s)
    s = re.sub(r'^b"(.*)"$', r"\1", s)
    s = s.lower().strip()
    s = re.sub(r"[^\w\s\-\.]+$", "", s)
    return s.strip()


def _parse_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _camel_to_title(name: str) -> str:
    """Convert camelCase game slug -> readable Title Case string."""
    s = re.sub(r"([A-Z])", r" \1", name).strip()
    return s.title()


def _parse_gpu_json_value(entry: dict, key: str) -> str:
    node = entry.get(key, {})
    if isinstance(node, dict):
        return str(node.get("Value", "")).strip()
    return str(node).strip() if node else ""


# ═══════════════════════════════════════════════
#  STAGE 1 — EXTRACT
# ═══════════════════════════════════════════════

def extract():
    log.info("STAGE 1: EXTRACT")
    if not FPS_CSV.exists():
        raise FileNotFoundError(f"Missing: {FPS_CSV}")
    if not GPU_JSON.exists():
        raise FileNotFoundError(f"Missing: {GPU_JSON}")

    log.info("  Reading fps_benchmark.csv ...")
    fps_df = pd.read_csv(FPS_CSV)
    log.info("  -> %d rows x %d cols", *fps_df.shape)

    log.info("  Reading gpus.json ...")
    with open(GPU_JSON, "r") as f:
        gpu_data = json.load(f)
    log.info("  -> %d GPU entries", len(gpu_data))

    return fps_df, gpu_data


# ═══════════════════════════════════════════════
#  STAGE 2 — TRANSFORM
# ═══════════════════════════════════════════════

def transform(fps_df, gpu_data):
    log.info("STAGE 2: TRANSFORM")
    df = fps_df.copy()

    # Drop rows missing critical fields
    critical = ["CpuName", "GpuName", "GameName", "FPS"]
    before = len(df)
    df.dropna(subset=critical, inplace=True)
    log.info("  Dropped %d rows with missing critical values", before - len(df))

    # Normalize string columns
    str_cols = ["CpuName", "GpuName", "GameName", "GpuArchitecture",
                "GpuMemoryType", "GpuDirectX", "GpuVulkan", "GpuOpenGL",
                "GameSetting", "GpuBus.interface", "GpuShaderModel"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].apply(_clean_str)

    # Resolution: float 1080.0 -> string "1080p"
    df["GameResolution"] = df["GameResolution"].apply(
        lambda v: f"{int(float(v))}p" if pd.notna(v) and str(v).strip() != "" else None
    )

    # Numeric coercion
    num_cols = [
        "CpuNumberOfCores", "CpuNumberOfThreads", "CpuBaseClock",
        "CpuTurboClock", "CpuTDP", "CpuProcessSize", "CpuCacheL3",
        "GpuBandwidth", "GpuBaseClock", "GpuBoostClock",
        "GpuMemoryBus", "GpuMemorySize", "GpuNumberOfShadingUnits",
        "GpuNumberOfTMUs", "GpuNumberOfROPs", "GpuFP32Performance",
        "GpuProcessSize", "GpuNumberOfTransistors", "FPS"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Deduplicate hardware combinations
    hw_cols = [c for c in df.columns if c not in ["GameName", "GameResolution", "GameSetting", "FPS"]]
    hw_df = df[hw_cols].drop_duplicates(subset=["CpuName", "GpuName"]).reset_index(drop=True)
    hw_df["hw_id"] = hw_df.index + 1
    log.info("  -> %d unique hardware combinations", len(hw_df))

    # Deduplicate games
    game_df = df[["GameName"]].drop_duplicates().reset_index(drop=True)
    game_df["game_id"] = game_df.index + 1
    game_df["game_name_clean"] = game_df["GameName"].apply(_camel_to_title)
    log.info("  -> %d unique games", len(game_df))

    # Parse GPU JSON specs
    log.info("  Parsing GPU JSON specs ...")
    gpu_records = []
    for entry in gpu_data:
        name = str(entry.get("Name", "")).strip()
        if not name:
            continue
        gpu_records.append({
            "gpu_name":         name.lower().strip(),
            "gpu_price":        _parse_gpu_json_value(entry, "Price"),
            "gpu_year":         _parse_gpu_json_value(entry, "Year"),
            "gpu_max_temp":     _parse_gpu_json_value(entry, "Maximum Recorded Temperature"),
            "gpu_psu_watts":    _parse_gpu_json_value(entry, "Recommended Power Supply"),
            "gpu_avg_1080p":    _parse_gpu_json_value(entry, "Average 1080p Performance"),
            "gpu_avg_1440p":    _parse_gpu_json_value(entry, "Average 1440p Performance"),
            "gpu_avg_4k":       _parse_gpu_json_value(entry, "Average 4K Performance"),
            "gpu_vram_gb":      _parse_gpu_json_value(entry, "Memory"),
            "gpu_series":       str(entry.get("Series", "")).strip(),
        })
    gpu_specs_df = pd.DataFrame(gpu_records)
    log.info("  -> %d GPU spec entries parsed", len(gpu_specs_df))

    log.info("  Transform complete")
    return df, hw_df, game_df, gpu_specs_df


# ═══════════════════════════════════════════════
#  STAGE 3 — IGDB ENRICHMENT
# ═══════════════════════════════════════════════

def get_igdb_token():
    if (not CLIENT_ID or not CLIENT_SECRET
            or CLIENT_ID == "your_twitch_client_id_here"):
        log.warning("IGDB credentials not set in .env — skipping IGDB enrichment.")
        return None
    try:
        resp = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type":    "client_credentials",
            },
            timeout=10,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        log.info("IGDB OAuth token acquired")
        return token
    except Exception as e:
        log.warning("IGDB token fetch failed: %s", e)
        return None


def fetch_igdb_game(token: str, game_name: str) -> dict:
    headers = {
        "Client-ID":     CLIENT_ID,
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }
    body = (
        f'search "{game_name}"; '
        f'fields id,name,summary,genres.name,platforms.name,'
        f'first_release_date; limit 1;'
    )
    try:
        resp = requests.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data=body,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return results[0]
    except Exception as e:
        log.warning("  IGDB query failed for '%s': %s", game_name, e)
    return {}


def enrich_games_with_igdb(game_df):
    log.info("STAGE 3: IGDB ENRICHMENT")
    token = get_igdb_token()

    igdb_cols = ["igdb_id", "igdb_summary", "igdb_genres",
                 "igdb_platforms", "igdb_first_release_date"]

    if not token:
        for col in igdb_cols:
            game_df[col] = None
        return game_df

    igdb_rows = []
    for _, row in game_df.iterrows():
        clean_name = row["game_name_clean"]
        log.info("  Querying IGDB: %s", clean_name)
        data = fetch_igdb_game(token, clean_name)
        igdb_rows.append({
            "igdb_id": data.get("id"),
            "igdb_summary": data.get("summary"),
            "igdb_genres": ", ".join(
                g["name"] for g in data.get("genres", []) if isinstance(g, dict)
            ) or None,
            "igdb_platforms": ", ".join(
                p["name"] for p in data.get("platforms", []) if isinstance(p, dict)
            ) or None,
            "igdb_first_release_date": str(
                datetime.utcfromtimestamp(data["first_release_date"]).date()
            ) if data.get("first_release_date") else None,
        })

    igdb_df = pd.DataFrame(igdb_rows)
    game_df = pd.concat([game_df.reset_index(drop=True),
                         igdb_df.reset_index(drop=True)], axis=1)
    log.info("  IGDB enrichment complete")
    return game_df


# ═══════════════════════════════════════════════
#  STAGE 4 — LOAD
# ═══════════════════════════════════════════════

def get_engine():
    log.info("Connecting to PostgreSQL: %s:%s/%s", DB_HOST, DB_PORT, DB_NAME)
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.info("  Database connection OK")
    return engine


def create_schema(engine):
    log.info("Creating schema (DROP + CREATE all tables) ...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    log.info("  Schema created")


def load_hardware_specs(session, hw_df):
    log.info("Loading hardware_specs ...")
    mapping = {}
    objects = []

    for _, row in hw_df.iterrows():
        obj = HardwareSpec(
            cpu_name            = str(row.get("CpuName", "")),
            cpu_cores           = _parse_int(row.get("CpuNumberOfCores")),
            cpu_threads         = _parse_int(row.get("CpuNumberOfThreads")),
            cpu_base_clock_mhz  = _parse_float(row.get("CpuBaseClock")),
            cpu_turbo_clock_mhz = _parse_float(row.get("CpuTurboClock")),
            cpu_tdp_watts       = _parse_float(row.get("CpuTDP")),
            cpu_process_nm      = _parse_float(row.get("CpuProcessSize")),
            cpu_cache_l3_kb     = _parse_float(row.get("CpuCacheL3")),
            gpu_name            = str(row.get("GpuName", "")),
            gpu_architecture    = str(row.get("GpuArchitecture", "")) or None,
            gpu_memory_gb       = _parse_float(row.get("GpuMemorySize")),
            gpu_memory_type     = str(row.get("GpuMemoryType", "")) or None,
            gpu_base_clock_mhz  = _parse_float(row.get("GpuBaseClock")),
            gpu_boost_clock_mhz = _parse_float(row.get("GpuBoostClock")),
            gpu_memory_bus_bits = _parse_float(row.get("GpuMemoryBus")),
            gpu_bandwidth_gb_s  = _parse_float(row.get("GpuBandwidth")),
            gpu_shading_units   = _parse_int(row.get("GpuNumberOfShadingUnits")),
            gpu_tmus            = _parse_int(row.get("GpuNumberOfTMUs")),
            gpu_rops            = _parse_int(row.get("GpuNumberOfROPs")),
            gpu_fp32_tflops     = _parse_float(row.get("GpuFP32Performance")),
            gpu_process_nm      = _parse_float(row.get("GpuProcessSize")),
            gpu_transistors_m   = _parse_float(row.get("GpuNumberOfTransistors")),
            gpu_directx         = str(row.get("GpuDirectX", "")) or None,
            gpu_vulkan          = str(row.get("GpuVulkan", "")) or None,
            gpu_opengl          = str(row.get("GpuOpenGL", "")) or None,
        )
        objects.append(obj)

    session.bulk_save_objects(objects, return_defaults=True)
    session.flush()

    for obj in objects:
        mapping[(obj.cpu_name, obj.gpu_name)] = obj.id

    log.info("  -> %d hardware_specs rows inserted", len(objects))
    return mapping


def load_games(session, game_df):
    log.info("Loading games ...")
    mapping = {}
    objects = []

    for _, row in game_df.iterrows():
        obj = Game(
            game_name_raw           = str(row["GameName"]),
            game_name_clean         = str(row.get("game_name_clean", "")),
            igdb_id                 = _parse_int(row.get("igdb_id")),
            igdb_summary            = row.get("igdb_summary"),
            igdb_genres             = row.get("igdb_genres"),
            igdb_platforms          = row.get("igdb_platforms"),
            igdb_first_release_date = row.get("igdb_first_release_date"),
        )
        objects.append(obj)

    session.bulk_save_objects(objects, return_defaults=True)
    session.flush()

    for obj in objects:
        mapping[obj.game_name_raw] = obj.id

    log.info("  -> %d games rows inserted", len(objects))
    return mapping


def load_fps_benchmarks(session, df, hw_mapping, game_mapping, batch_size=2000):
    log.info("Loading fps_benchmarks ...")
    objects = []
    skipped = 0

    for _, row in df.iterrows():
        hw_key   = (str(row["CpuName"]), str(row["GpuName"]))
        game_key = str(row["GameName"])

        hw_id   = hw_mapping.get(hw_key)
        game_id = game_mapping.get(game_key)

        if not hw_id or not game_id:
            skipped += 1
            continue

        objects.append(FPSBenchmark(
            hardware_spec_id = hw_id,
            game_id          = game_id,
            resolution       = str(row.get("GameResolution", "")) or None,
            setting          = str(row.get("GameSetting", "")) or None,
            fps              = _parse_float(row.get("FPS")),
        ))

        if len(objects) >= batch_size:
            session.bulk_save_objects(objects)
            session.flush()
            log.info("  ... flushed batch of %d", batch_size)
            objects = []

    if objects:
        session.bulk_save_objects(objects)
        session.flush()

    log.info("  -> fps_benchmarks: %d inserted, %d skipped",
             len(df) - skipped, skipped)


def verify_load(engine):
    log.info("VERIFICATION")
    with engine.connect() as conn:
        for table in ["hardware_specs", "games", "fps_benchmarks"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            log.info("  %-22s -> %d rows", table, count)

        log.info("  Top 5 GPU/Game combos by average FPS:")
        result = conn.execute(text("""
            SELECT
                h.gpu_name,
                g.game_name_clean,
                ROUND(AVG(f.fps)::numeric, 1) AS avg_fps
            FROM fps_benchmarks f
            JOIN hardware_specs h ON f.hardware_spec_id = h.id
            JOIN games          g ON f.game_id          = g.id
            GROUP BY h.gpu_name, g.game_name_clean
            ORDER BY avg_fps DESC
            LIMIT 5;
        """))
        for r in result:
            log.info("    %-45s | %-30s | %s FPS", r[0], r[1], r[2])


# ═══════════════════════════════════════════════
#  STAGE 5 — EXPORT TRAINING CSV
# ═══════════════════════════════════════════════

EXPORT_SQL = """
SELECT
    -- Hardware identifiers
    h.cpu_name,
    h.gpu_name,

    -- CPU features
    h.cpu_cores,
    h.cpu_threads,
    h.cpu_base_clock_mhz,
    h.cpu_turbo_clock_mhz,
    h.cpu_tdp_watts,
    h.cpu_process_nm,
    h.cpu_cache_l3_kb,

    -- GPU features
    h.gpu_architecture,
    h.gpu_memory_gb         AS gpu_vram_gb,
    h.gpu_memory_type,
    h.gpu_base_clock_mhz,
    h.gpu_boost_clock_mhz,
    h.gpu_memory_bus_bits,
    h.gpu_bandwidth_gb_s,
    h.gpu_shading_units,
    h.gpu_tmus,
    h.gpu_rops,
    h.gpu_fp32_tflops,
    h.gpu_process_nm,
    h.gpu_transistors_m,

    -- Game info
    g.game_name_clean       AS game_name,
    g.igdb_genres,

    -- Benchmark conditions
    f.resolution,
    f.setting,

    -- Target variable
    f.fps

FROM fps_benchmarks f
JOIN hardware_specs h ON f.hardware_spec_id = h.id
JOIN games          g ON f.game_id          = g.id
WHERE f.fps IS NOT NULL
ORDER BY g.game_name_clean, h.gpu_name, h.cpu_name, f.resolution, f.setting;
"""


def export_training_csv(engine):
    """Run the JOIN query and save clean_training_data.csv to the project root."""
    log.info("STAGE 5: EXPORT TRAINING CSV")
    out_path = BASE_DIR / "clean_training_data.csv"

    log.info("  Running JOIN across all 3 tables ...")
    training_df = pd.read_sql(text(EXPORT_SQL), engine.connect())
    rows, cols = training_df.shape
    log.info("  -> %d rows x %d columns joined", rows, cols)

    # Final safety pass: drop any rows where fps is null/zero
    before = len(training_df)
    training_df = training_df[training_df["fps"] > 0].copy()
    log.info("  -> Dropped %d rows with fps <= 0", before - len(training_df))

    # Round floats to 4 decimal places for clean CSV
    float_cols = training_df.select_dtypes(include=["float64"]).columns
    training_df[float_cols] = training_df[float_cols].round(4)

    training_df.to_csv(out_path, index=False)
    log.info("  Saved -> %s", out_path)
    log.info("  Columns: %s", list(training_df.columns))
    log.info("  Sample row:")
    log.info("    %s", training_df.iloc[0].to_dict())
    return training_df


# ═══════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════

def main():
    log.info("=" * 50)
    log.info("  Hardware ETL Pipeline — Starting")
    log.info("=" * 50)

    fps_df, gpu_data = extract()
    df, hw_df, game_df, gpu_specs_df = transform(fps_df, gpu_data)
    game_df = enrich_games_with_igdb(game_df)

    engine = get_engine()
    create_schema(engine)

    with Session(engine) as session:
        try:
            hw_mapping   = load_hardware_specs(session, hw_df)
            game_mapping = load_games(session, game_df)
            load_fps_benchmarks(session, df, hw_mapping, game_mapping)
            session.commit()
            log.info("All data committed successfully")
        except Exception as e:
            session.rollback()
            log.error("Load FAILED — rolled back transaction: %s", e)
            raise

    verify_load(engine)
    export_training_csv(engine)

    log.info("=" * 50)
    log.info("  ETL Pipeline Complete")
    log.info("  Output: clean_training_data.csv")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
