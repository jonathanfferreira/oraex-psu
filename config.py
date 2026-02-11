"""
ORAEX PSU Manager — Configuration
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database
DATABASE_PATH = os.path.join(BASE_DIR, "oraex.db")

# Excel sources
EXCEL_PATH = os.path.join(BASE_DIR, "ORAEX - Consolidação GetTech 2025 (6).xlsm")
GMUD_PATH = EXCEL_PATH
CMDB_FULL_PATH = os.path.join(BASE_DIR, "CMDB Full GetBR (3).xlsx")

# Flask
SECRET_KEY = os.environ.get("ORAEX_SECRET_KEY", "oraex-psu-manager-2025-local-only")
DEBUG = True
HOST = "127.0.0.1"
PORT = 5000

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
