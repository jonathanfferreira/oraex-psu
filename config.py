"""
ORAEX PSU Manager — Configuration
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database — in Cloud Run, DATABASE_PATH points to mounted GCS volume
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "oraex.db"))

# Excel sources (fallback for local usage; in prod, files come via upload)
EXCEL_PATH = os.environ.get("EXCEL_PATH",
    os.path.join(BASE_DIR, "ORAEX - Consolidação GetTech 2025 (7).xlsm"))
GMUD_PATH = EXCEL_PATH
CMDB_FULL_PATH = os.environ.get("CMDB_FULL_PATH",
    os.path.join(BASE_DIR, "CMDB Full GetBR (4).xlsx"))

# Qualys sources (fallback for local usage)
QUALYS_PAGONXT_PATH = os.environ.get("QUALYS_PAGONXT_PATH",
    os.path.join(BASE_DIR, "scan-vulnerabilidades", "20260219 - SCAN FULL QUALYS - PAGONXT.xlsx"))
QUALYS_GETNET_PATH = os.environ.get("QUALYS_GETNET_PATH",
    os.path.join(BASE_DIR, "scan-vulnerabilidades", "20260219 - SCAN FULL QUALYS.xlsm"))

# Flask
SECRET_KEY = os.environ.get("ORAEX_SECRET_KEY", "oraex-psu-manager-2025-local-only")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

# Max upload size (50MB)
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))

# Month sheets mapping (sheet name -> (year, month))
MONTH_SHEETS = {
    "FEVEREIRO-25": (2025, 2),
    "MARÇO-25": (2025, 3),
    "ABRIL-25": (2025, 4),
    "MAIO-25": (2025, 5),
    "JUNHO-25": (2025, 6),
    "JULHO-25": (2025, 7),
    "AGOSTO-25": (2025, 8),
    "SETEMBRO-25": (2025, 9),
    "OUTUBRO-25": (2025, 10),
    "NOVEMBRO-25": (2025, 11),
    "DEZEMBRO-25": (2025, 12),
    "JANEIRO-26": (2026, 1),
    "FEVEREIRO-26": (2026, 2),
}
