from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORT_DIR = PROJECT_ROOT / "reports"
STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    report_dir: Path = REPORT_DIR
    static_dir: Path = STATIC_DIR
    business_db_path: Path = DATA_DIR / "business.sqlite3"
    history_db_path: Path = DATA_DIR / "kerf.sqlite3"
    default_model: str = os.getenv("KERF_DEFAULT_MODEL", "gpt-5.6-luna")
    reasoning_effort: str = os.getenv("KERF_REASONING_EFFORT", "low")
    max_output_tokens: int = int(os.getenv("KERF_MAX_OUTPUT_TOKENS", "900"))
    input_price_per_million: float = float(
        os.getenv("KERF_INPUT_PRICE_PER_MILLION", "0.20")
    )
    cached_input_price_per_million: float = float(
        os.getenv("KERF_CACHED_INPUT_PRICE_PER_MILLION", "0.02")
    )
    output_price_per_million: float = float(
        os.getenv("KERF_OUTPUT_PRICE_PER_MILLION", "1.20")
    )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
