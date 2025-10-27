import os
from datetime import time
from typing import Optional, Tuple

try:
    # Optional dependency; loaded if available
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # If python-dotenv is not installed, environment loading is skipped
    pass


def _getenv_int(name: str, default: Optional[int]) -> Optional[int]:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _getenv_float(name: str, default: Optional[float]) -> Optional[float]:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _getenv_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _parse_time_hhmm(s: Optional[str], default: time) -> time:
    if not s:
        return default
    try:
        parts = s.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        h = max(0, min(23, h))
        m = max(0, min(59, m))
        return time(h, m)
    except Exception:
        return default


# Audio/recording configuration
SAMPLE_RATE: int = _getenv_int("SAMPLE_RATE", 44100) or 44100
CHANNELS: int = _getenv_int("CHANNELS", 1) or 1
OUTPUT_FOLDER: str = os.getenv("OUTPUT_FOLDER", os.getenv("FOLDER", "recordings"))

# Recording window
WINDOW_START: time = _parse_time_hhmm(os.getenv("WINDOW_START", "20:40"), time(20, 40))
WINDOW_END: time = _parse_time_hhmm(os.getenv("WINDOW_END", "06:00"), time(6, 0))
TOTAL_HOURS: int = _getenv_int("TOTAL_HOURS", 12) or 12
SEGMENT_HOURS: int = _getenv_int("SEGMENT_HOURS", 1) or 1

# Standalone immediate recording duration (in minutes); if set/positive, bypasses window schedule
RUN_FOR_MINUTES: Optional[int] = _getenv_int("RUN_FOR_MINUTES", None)

# Device configuration
INPUT_DEVICE: Optional[int] = _getenv_int("INPUT_DEVICE", None)
OUTPUT_DEVICE: Optional[int] = _getenv_int("OUTPUT_DEVICE", None)
LIST_DEVICES_ON_START: bool = _getenv_bool("LIST_DEVICES_ON_START", False)


# Spectrogram defaults (used by CLI scripts as defaults)
SPEC_MAX_FREQ: int = _getenv_int("SPEC_MAX_FREQ", 10000) or 10000
SPEC_NPERSEG: int = _getenv_int("SPEC_NPERSEG", 1024) or 1024
SPEC_NOVERLAP: int = _getenv_int("SPEC_NOVERLAP", 768) or 768
SPEC_BLOCK_SECONDS: float = _getenv_float("SPEC_BLOCK_SECONDS", 5.0) or 5.0
SPEC_PLOW: float = _getenv_float("SPEC_PLOW", 1.0) or 1.0
SPEC_PHIGH: float = _getenv_float("SPEC_PHIGH", 99.0) or 99.0

# db_range may be empty; keep as Optional[float]
_db_range_raw = os.getenv("SPEC_DB_RANGE", "").strip()
SPEC_DB_RANGE: Optional[float] = None
if _db_range_raw:
    try:
        SPEC_DB_RANGE = float(_db_range_raw)
    except ValueError:
        SPEC_DB_RANGE = None

SPEC_COLORMAP: str = os.getenv("SPEC_COLORMAP", "inferno")


def get_device_tuple() -> Optional[Tuple[Optional[int], Optional[int]]]:
    if INPUT_DEVICE is None and OUTPUT_DEVICE is None:
        return None
    return (INPUT_DEVICE, OUTPUT_DEVICE)
