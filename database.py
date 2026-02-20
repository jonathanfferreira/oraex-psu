"""
ORAEX PSU Manager — Database Models & Queries (SQLite)
"""
import sqlite3
import os
from config import DATABASE_PATH
from werkzeug.security import generate_password_hash, check_password_hash


def get_connection():
    """Get a SQLite connection with row_factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── Servers (from "GetNet - Oracle Databases" sheet) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            environment TEXT,
            primary_hostname TEXT,
            standby_hostname TEXT,
            psu_version TEXT,
            email_sent TEXT,
            alignment TEXT,
            ggs_version TEXT,
            primary_contact TEXT,
            responsible_team TEXT,
            system_product TEXT,
            application_day TEXT,
            start_time TEXT,
            end_time TEXT,
            observation TEXT,
            total_servers INTEGER DEFAULT 1,
            has_standby INTEGER DEFAULT 0,
            has_ggs INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── CMDB Databases (from "GetNet CMDB - Databases" sheet) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cmdb_databases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            environment TEXT,
            name TEXT,
            contingency_name TEXT,
            db_type TEXT,
            db_version TEXT,
            db_version_detail TEXT,
            status TEXT,
            application_day TEXT,
            week_month TEXT,
            start_time TEXT,
            end_time TEXT,
            system TEXT,
            system_product TEXT,
            type TEXT,
            os TEXT,
            primary_contact TEXT,
            function TEXT,
            description TEXT,
            os_type TEXT,
            responsible_team TEXT,
            manager TEXT,
            team_email TEXT,
            validation_contact TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Monthly GMUDs (from month sheets like "FEVEREIRO-26") ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gmuds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            month INTEGER,
            client TEXT,
            db_type TEXT,
            environment TEXT,
            status TEXT,
            day_of_week TEXT,
            start_date TEXT,
            end_date TEXT,
            change_number TEXT,
            title TEXT,
            assigned_to TEXT,
            observation TEXT,
            vulnerability TEXT,
            opened_by TEXT,
            vulnerability_before TEXT,
            vulnerability_after TEXT,
            closing_code TEXT,
            needs_replan TEXT,
            new_start_date TEXT,
            new_end_date TEXT,
            new_gmud TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Planning (from "Planejamento oracle" sheet) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS planning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT,
            contingency_name TEXT,
            application_day TEXT,
            week_month TEXT,
            start_time TEXT,
            end_time TEXT,
            primary_contact TEXT,
            db_version TEXT,
            bank_version TEXT,
            system TEXT,
            system_product TEXT,
            os TEXT,
            function TEXT,
            description TEXT,
            responsible_team TEXT,
            validation_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── PagoNxt Databases (from "PagoNxt - Databases" sheet) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagonxt_databases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            environment TEXT,
            name TEXT,
            contingent TEXT,
            psu_version TEXT,
            contact TEXT,
            zone TEXT,
            product TEXT,
            description TEXT,
            channel TEXT,
            service TEXT,
            observation TEXT,
            ip TEXT,
            instance TEXT,
            status TEXT,
            os TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Import log ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file TEXT,
            sheets_imported TEXT,
            total_records INTEGER,
            status TEXT,
            message TEXT
        )
    """)

    # ── CMDB Full (from "CMDB Full GetBR" spreadsheet — only DB servers) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cmdb_full (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT,
            hostname TEXT,
            contingency TEXT,
            db_type TEXT,
            db_version TEXT,
            status TEXT,
            server_type TEXT,
            environment TEXT,
            os TEXT,
            responsible_team TEXT,
            manager TEXT,
            primary_contact TEXT,
            system_product TEXT,
            function TEXT,
            description TEXT,
            validation_contact TEXT,
            team_email TEXT,
            shutdown_procedure TEXT,
            affinity TEXT,
            week_month TEXT,
            application_day TEXT,
            start_time TEXT,
            end_time TEXT,
            importance_level TEXT,
            criticality TEXT,
            scope_pci TEXT,
            scope_sox TEXT,
            scope_pagonxt TEXT,
            ip_service TEXT,
            ip_backup TEXT,
            ip_branca TEXT,
            zone TEXT,
            country TEXT,
            source_sheet TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Qualys Vulnerability Definitions ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qualys_vulnerabilities (
            qid INTEGER PRIMARY KEY,
            title TEXT,
            severity TEXT,
            threat TEXT,
            solution TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Qualys Detections on Servers ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qualys_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qid INTEGER,
            asset_name TEXT,
            asset_ip TEXT,
            environment TEXT,
            os TEXT,
            os_version TEXT,
            status TEXT,
            first_detected TEXT,
            last_detected TEXT,
            detection_age INTEGER,
            results TEXT,
            overdue TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (qid) REFERENCES qualys_vulnerabilities(qid)
        )
    """)

    # ── Users (Authentication) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role TEXT DEFAULT 'viewer',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")

    # ── Indexes for common queries ──
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_env ON servers(environment)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_psu ON servers(psu_version)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gmuds_status ON gmuds(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gmuds_month ON gmuds(year, month)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gmuds_assigned ON gmuds(assigned_to)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmdb_env ON cmdb_databases(environment)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmdb_type ON cmdb_databases(db_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmdb_full_client ON cmdb_full(client)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmdb_full_db ON cmdb_full(db_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmdb_full_status ON cmdb_full(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmdb_full_env ON cmdb_full(environment)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmdb_full_host ON cmdb_full(hostname)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qualys_det_qid ON qualys_detections(qid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qualys_det_asset ON qualys_detections(asset_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qualys_det_source ON qualys_detections(source)")

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully!")


# ══════════════════════════════════════════════════════════
#  QUERY FUNCTIONS
# ══════════════════════════════════════════════════════════

def get_dashboard_stats():
    """Get KPI numbers for the dashboard."""
    conn = get_connection()
    c = conn.cursor()

    stats = {}

    # Total Oracle servers (counting standby as separate servers)
    c.execute("SELECT COALESCE(SUM(total_servers), 0) FROM servers")
    stats["total_servers"] = c.fetchone()[0]

    # Total rows (pairs)
    c.execute("SELECT COUNT(*) FROM servers")
    stats["total_rows"] = c.fetchone()[0]

    # Servers with GGS
    c.execute("SELECT COUNT(*) FROM servers WHERE has_ggs = 1")
    stats["total_ggs"] = c.fetchone()[0]

    # Standalone vs with standby
    c.execute("SELECT COUNT(*) FROM servers WHERE has_standby = 1")
    stats["with_standby"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM servers WHERE has_standby = 0")
    stats["standalone"] = c.fetchone()[0]

    # By environment (using SUM for real server count)
    c.execute("""
        SELECT environment, SUM(total_servers) as cnt
        FROM servers
        GROUP BY environment
        ORDER BY cnt DESC
    """)
    stats["servers_by_env"] = [dict(r) for r in c.fetchall()]

    # By PSU version (using SUM for real server count)
    c.execute("""
        SELECT psu_version, SUM(total_servers) as cnt
        FROM servers
        WHERE psu_version IS NOT NULL AND psu_version != ''
        GROUP BY psu_version
        ORDER BY psu_version
    """)
    stats["servers_by_psu"] = [dict(r) for r in c.fetchall()]

    # Total CMDB databases
    c.execute("SELECT COUNT(*) FROM cmdb_databases")
    stats["total_cmdb"] = c.fetchone()[0]

    # Total CMDB Full (added for Phase 0 consistency)
    c.execute("SELECT COUNT(*) FROM cmdb_full")
    stats["total_cmdb_full"] = c.fetchone()[0]

    # CMDB by type
    c.execute("""
        SELECT db_type, COUNT(*) as cnt
        FROM cmdb_databases
        WHERE db_type IS NOT NULL AND db_type != ''
        GROUP BY db_type
        ORDER BY cnt DESC
    """)
    stats["cmdb_by_type"] = [dict(r) for r in c.fetchall()]

    # GMUDs stats
    c.execute("SELECT COUNT(*) FROM gmuds")
    stats["total_gmuds"] = c.fetchone()[0]

    c.execute("""
        SELECT status, COUNT(*) as cnt
        FROM gmuds
        WHERE status IS NOT NULL AND status != ''
        GROUP BY status
        ORDER BY cnt DESC
    """)
    stats["gmuds_by_status"] = [dict(r) for r in c.fetchall()]

    # GMUDs by month
    c.execute("""
        SELECT year, month, COUNT(*) as cnt
        FROM gmuds
        GROUP BY year, month
        ORDER BY year, month
    """)
    stats["gmuds_by_month"] = [dict(r) for r in c.fetchall()]

    # GMUDs by assigned person
    c.execute("""
        SELECT assigned_to, COUNT(*) as cnt
        FROM gmuds
        WHERE assigned_to IS NOT NULL AND assigned_to != ''
        GROUP BY assigned_to
        ORDER BY cnt DESC
    """)
    stats["gmuds_by_person"] = [dict(r) for r in c.fetchall()]

    # CMDB by environment
    c.execute("""
        SELECT environment, COUNT(*) as cnt
        FROM cmdb_databases
        WHERE environment IS NOT NULL AND environment != ''
        GROUP BY environment
        ORDER BY cnt DESC
    """)
    stats["cmdb_by_env"] = [dict(r) for r in c.fetchall()]

    # CMDB by status
    c.execute("""
        SELECT status, COUNT(*) as cnt
        FROM cmdb_databases
        WHERE status IS NOT NULL AND status != ''
        GROUP BY status
        ORDER BY cnt DESC
    """)
    stats["cmdb_by_status"] = [dict(r) for r in c.fetchall()]

    # Latest import
    c.execute("SELECT * FROM import_log ORDER BY imported_at DESC LIMIT 1")
    row = c.fetchone()
    stats["last_import"] = dict(row) if row else None

    conn.close()
    return stats


def get_servers(environment=None, psu_version=None, search=None, page=1, per_page=50):
    """Get servers with optional filters and pagination."""
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM servers WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM servers WHERE 1=1"
    params = []

    if environment:
        query += " AND environment = ?"
        count_query += " AND environment = ?"
        params.append(environment)
    if psu_version:
        query += " AND psu_version = ?"
        count_query += " AND psu_version = ?"
        params.append(psu_version)
    if search:
        query += " AND (primary_hostname LIKE ? OR standby_hostname LIKE ? OR system_product LIKE ? OR responsible_team LIKE ?)"
        count_query += " AND (primary_hostname LIKE ? OR standby_hostname LIKE ? OR system_product LIKE ? OR responsible_team LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param] * 4)

    c.execute(count_query, params)
    total = c.fetchone()[0]

    query += " ORDER BY environment, primary_hostname"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

    c.execute(query, params)
    servers = [dict(r) for r in c.fetchall()]

    conn.close()
    return {"servers": servers, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


def get_gmuds(year=None, month=None, status=None, assigned_to=None, search=None, page=1, per_page=50):
    """Get GMUDs with optional filters and pagination."""
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM gmuds WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM gmuds WHERE 1=1"
    params = []

    if year:
        query += " AND year = ?"
        count_query += " AND year = ?"
        params.append(year)
    if month:
        query += " AND month = ?"
        count_query += " AND month = ?"
        params.append(month)
    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status)
    if assigned_to:
        query += " AND assigned_to = ?"
        count_query += " AND assigned_to = ?"
        params.append(assigned_to)
    if search:
        query += " AND (change_number LIKE ? OR title LIKE ? OR assigned_to LIKE ?)"
        count_query += " AND (change_number LIKE ? OR title LIKE ? OR assigned_to LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param] * 3)

    c.execute(count_query, params)
    total = c.fetchone()[0]

    query += " ORDER BY start_date DESC"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

    c.execute(query, params)
    gmuds = [dict(r) for r in c.fetchall()]

    conn.close()
    return {"gmuds": gmuds, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


def get_cmdb_databases(environment=None, db_type=None, status=None, search=None, page=1, per_page=50):
    """Get CMDB databases with optional filters."""
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM cmdb_databases WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM cmdb_databases WHERE 1=1"
    params = []

    if environment:
        query += " AND environment = ?"
        count_query += " AND environment = ?"
        params.append(environment)
    if db_type:
        query += " AND db_type = ?"
        count_query += " AND db_type = ?"
        params.append(db_type)
    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (name LIKE ? OR contingency_name LIKE ? OR system_product LIKE ? OR responsible_team LIKE ?)"
        count_query += " AND (name LIKE ? OR contingency_name LIKE ? OR system_product LIKE ? OR responsible_team LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param] * 4)

    c.execute(count_query, params)
    total = c.fetchone()[0]

    query += " ORDER BY environment, name"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

    c.execute(query, params)
    databases = [dict(r) for r in c.fetchall()]

    conn.close()
    return {"databases": databases, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


def get_filter_options():
    """Get unique values for filter dropdowns."""
    conn = get_connection()
    c = conn.cursor()

    options = {}

    c.execute("SELECT DISTINCT environment FROM servers WHERE environment IS NOT NULL AND environment != '' ORDER BY environment")
    options["server_environments"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT psu_version FROM servers WHERE psu_version IS NOT NULL AND psu_version != '' ORDER BY psu_version")
    options["psu_versions"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT status FROM gmuds WHERE status IS NOT NULL AND status != '' ORDER BY status")
    options["gmud_statuses"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT assigned_to FROM gmuds WHERE assigned_to IS NOT NULL AND assigned_to != '' ORDER BY assigned_to")
    options["gmud_assignees"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT year FROM gmuds ORDER BY year")
    options["gmud_years"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT environment FROM cmdb_databases WHERE environment IS NOT NULL AND environment != '' ORDER BY environment")
    options["cmdb_environments"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT db_type FROM cmdb_databases WHERE db_type IS NOT NULL AND db_type != '' ORDER BY db_type")
    options["cmdb_db_types"] = [r[0] for r in c.fetchall()]

    conn.close()
    return options


def get_planning_data():
    """Get all planning entries."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM planning ORDER BY hostname")
    data = [dict(r) for r in c.fetchall()]
    conn.close()
    return data


def get_pagonxt_databases(search=None, page=1, per_page=50):
    """Get PagoNxt databases with optional search and pagination."""
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM pagonxt_databases WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM pagonxt_databases WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR product LIKE ? OR description LIKE ? OR ip LIKE ?)"
        count_query += " AND (name LIKE ? OR product LIKE ? OR description LIKE ? OR ip LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param] * 4)

    c.execute(count_query, params)
    total = c.fetchone()[0]

    query += " ORDER BY environment, name"
    query += " LIMIT ? OFFSET ?"

    c.execute(query, params + [per_page, (page - 1) * per_page])
    databases = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        "databases": databases,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


def get_cmdb_full(client=None, db_type=None, status=None, environment=None,
                  search=None, page=1, per_page=50):
    """Get CMDB Full database servers with filters and pagination.
       Enriched with Oracle Inventory data (servers table) where matches found.
    """
    conn = get_connection()
    c = conn.cursor()

    where = []
    params = []

    # Base query now includes LEFT JOIN to servers
    # We match on hostname and environment to ensure correct mapping
    base_query = """
        FROM cmdb_full c
        LEFT JOIN servers s ON (
            lower(c.hostname) = lower(s.primary_hostname) 
            AND c.environment = s.environment
        )
    """

    if client:
        where.append("c.client = ?")
        params.append(client)
    if db_type:
        where.append("c.db_type = ?")
        params.append(db_type)
    if status:
        where.append("c.status = ?")
        params.append(status)
    if environment:
        where.append("c.environment = ?")
        params.append(environment)
    if search:
        where.append("(c.hostname LIKE ? OR c.contingency LIKE ? OR c.system_product LIKE ? OR c.description LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s, s])

    where_clause = " WHERE " + " AND ".join(where) if where else ""

    # Count total
    c.execute(f"SELECT COUNT(*) {base_query} {where_clause}", params)
    total = c.fetchone()[0]

    # Select fields - mixing CMDB columns with Oracle specific ones
    # We prefer Oracle PSU version if available, otherwise CMDB DB version
    select_sql = f"""
        SELECT 
            c.*,
            s.psu_version as oracle_psu,
            s.start_time as oracle_start,
            s.end_time as oracle_end,
            s.observation as oracle_observation,
            s.primary_contact as oracle_contact
        {base_query}
        {where_clause}
        ORDER BY c.client, c.environment, c.hostname
        LIMIT ? OFFSET ?
    """

    c.execute(select_sql, params + [per_page, (page - 1) * per_page])
    rows = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        "data": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


def get_cmdb_full_stats(client=None):
    """Get statistics for the CMDB Full viewer page."""
    conn = get_connection()
    c = conn.cursor()

    stats = {}
    client_filter = ""
    params = []
    if client:
        client_filter = " WHERE client = ?"
        params = [client]

    # Total DB servers
    c.execute(f"SELECT COUNT(*) FROM cmdb_full{client_filter}", params)
    stats["total"] = c.fetchone()[0]

    # Active count
    active_filter = f"{client_filter} {'AND' if client else 'WHERE'} status IN ('Ativo', 'Running')"
    c.execute(f"SELECT COUNT(*) FROM cmdb_full{active_filter}", params)
    stats["active"] = c.fetchone()[0]

    # By client
    c.execute("""
        SELECT client, COUNT(*) as cnt
        FROM cmdb_full
        GROUP BY client
        ORDER BY cnt DESC
    """)
    stats["by_client"] = [dict(r) for r in c.fetchall()]

    # By DB type
    db_type_sql = """
        SELECT db_type, COUNT(*) as cnt
        FROM cmdb_full
        WHERE db_type IS NOT NULL AND db_type != ''
    """
    if client:
        db_type_sql += " AND client = ?"
    db_type_sql += " GROUP BY db_type ORDER BY cnt DESC"
    c.execute(db_type_sql, params)
    stats["by_db_type"] = [dict(r) for r in c.fetchall()]

    # By environment
    c.execute(f"""
        SELECT environment, COUNT(*) as cnt
        FROM cmdb_full{client_filter}
        GROUP BY environment
        ORDER BY cnt DESC
    """, params)
    stats["by_environment"] = [dict(r) for r in c.fetchall()]

    # By status
    c.execute(f"""
        SELECT status, COUNT(*) as cnt
        FROM cmdb_full{client_filter}
        GROUP BY status
        ORDER BY cnt DESC
    """, params)
    stats["by_status"] = [dict(r) for r in c.fetchall()]

    # By DB type per environment (for heatmap)
    c.execute(f"""
        SELECT db_type, environment, COUNT(*) as cnt
        FROM cmdb_full{client_filter}
        GROUP BY db_type, environment
        ORDER BY db_type, environment
    """, params)
    stats["db_by_env"] = [dict(r) for r in c.fetchall()]

    # By client + DB type (cross-tab)
    c.execute("""
        SELECT client, db_type, COUNT(*) as cnt
        FROM cmdb_full
        GROUP BY client, db_type
        ORDER BY client, cnt DESC
    """)
    stats["client_db_type"] = [dict(r) for r in c.fetchall()]

    conn.close()
    return stats


def get_cmdb_full_filters():
    """Get unique filter values for CMDB Full page."""
    conn = get_connection()
    c = conn.cursor()
    options = {}

    c.execute("SELECT DISTINCT client FROM cmdb_full WHERE client IS NOT NULL ORDER BY client")
    options["clients"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT db_type FROM cmdb_full WHERE db_type IS NOT NULL AND db_type != '' ORDER BY db_type")
    options["db_types"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT status FROM cmdb_full WHERE status IS NOT NULL AND status != '' ORDER BY status")
    options["statuses"] = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT environment FROM cmdb_full WHERE environment IS NOT NULL AND environment != '' ORDER BY environment")
    options["environments"] = [r[0] for r in c.fetchall()]

    conn.close()
    return options


def get_user_by_id(user_id):
    """Get user by ID for Flask-Login."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username):
    """Get user by username."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username, password, display_name=None, role='viewer'):
    """Create a new user with hashed password."""
    conn = get_connection()
    c = conn.cursor()
    pw_hash = generate_password_hash(password)
    c.execute("""
        INSERT INTO users (username, password_hash, display_name, role)
        VALUES (?, ?, ?, ?)
    """, (username, pw_hash, display_name or username, role))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id


def verify_user(username, password):
    """Verify username and password. Returns user dict or None."""
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None


def ensure_admin_exists():
    """Create default admin user if no users exist."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        create_user('admin', 'oraex2025', 'Administrador', 'admin')
        print("  Default admin user created (admin / oraex2025)")


def get_gmud_by_id(gmud_id):
    """Get a single GMUD by ID."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM gmuds WHERE id = ?", (gmud_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_gmud(gmud_id, data):
    """Update an existing GMUD."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE gmuds SET
            client=?, db_type=?, environment=?, status=?,
            start_date=?, end_date=?, change_number=?, title=?,
            assigned_to=?, observation=?, vulnerability=?, opened_by=?
        WHERE id = ?
    """, (
        data.get('client'), data.get('db_type'), data.get('environment'),
        data.get('status'), data.get('start_date'), data.get('end_date'),
        data.get('change_number'), data.get('title'), data.get('assigned_to'),
        data.get('observation'), data.get('vulnerability'), data.get('opened_by'),
        gmud_id
    ))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0


def delete_gmud(gmud_id):
    """Delete a GMUD by ID."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM gmuds WHERE id = ?", (gmud_id,))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0


def search_hostnames(query, limit=15):
    """Search hostnames across servers, cmdb_full, and cmdb_databases tables."""
    conn = get_connection()
    c = conn.cursor()
    search_param = f"%{query}%"

    c.execute("""
        SELECT DISTINCT hostname, source FROM (
            SELECT primary_hostname AS hostname, 'servers' AS source
            FROM servers WHERE primary_hostname LIKE ?
            UNION
            SELECT standby_hostname AS hostname, 'servers' AS source
            FROM servers WHERE standby_hostname LIKE ? AND standby_hostname IS NOT NULL AND standby_hostname != ''
            UNION
            SELECT hostname, 'cmdb_full' AS source
            FROM cmdb_full WHERE hostname LIKE ?
            UNION
            SELECT contingency AS hostname, 'cmdb_full' AS source
            FROM cmdb_full WHERE contingency LIKE ? AND contingency IS NOT NULL AND contingency != ''
            UNION
            SELECT name AS hostname, 'cmdb' AS source
            FROM cmdb_databases WHERE name LIKE ?
            UNION
            SELECT contingency_name AS hostname, 'cmdb' AS source
            FROM cmdb_databases WHERE contingency_name LIKE ? AND contingency_name IS NOT NULL AND contingency_name != ''
        )
        WHERE hostname IS NOT NULL AND hostname != ''
        ORDER BY hostname
        LIMIT ?
    """, (search_param, search_param, search_param, search_param, search_param, search_param, limit))

    results = [{"hostname": r["hostname"], "source": r["source"]} for r in c.fetchall()]
    conn.close()
    return results


if __name__ == "__main__":
    init_db()

def get_server_details(hostname):
    """Get detailed info for a specific server (CMDB + Inventory + GMUDs)."""
    conn = get_connection()
    c = conn.cursor()

    # 1. Fetch Server Metadata (Union of CMDB Full and Inventory)
    # We use a similar LEFT JOIN as get_cmdb_full to get the best of both worlds
    query = """
        SELECT 
            c.*,
            s.psu_version as oracle_psu,
            s.start_time as oracle_start,
            s.end_time as oracle_end,
            s.observation as oracle_observation,
            s.primary_contact as oracle_contact,
            s.responsible_team as oracle_team,
            s.standby_hostname as oracle_standby
        FROM cmdb_full c
        LEFT JOIN servers s ON (
            lower(c.hostname) = lower(s.primary_hostname) 
            AND c.environment = s.environment
        )
        WHERE lower(c.hostname) = lower(?)
    """
    c.execute(query, (hostname,))
    row = c.fetchone()
    
    # If not found in CMDB Full, try searching just in Servers (Legacy Inventory)
    # This handles case where a server might only exist in the old inventory sheet
    if not row:
        c.execute("SELECT * FROM servers WHERE lower(primary_hostname) = lower(?)", (hostname,))
        server_row = c.fetchone()
        if server_row:
            # Normalize to match the CMDB structure partly
            server_data = dict(server_row)
            server_details = {
                "hostname": server_data['primary_hostname'],
                "environment": server_data['environment'],
                "db_type": "Oracle", # Assumed
                "status": "In Inventory Only",
                "oracle_psu": server_data['psu_version'],
                "oracle_start": server_data['start_time'],
                "oracle_end": server_data['end_time'],
                "oracle_observation": server_data['observation'],
                "primary_contact": server_data['primary_contact'],
                "responsible_team": server_data['responsible_team'],
                "system_product": server_data['system_product'],
                "source": "Inventory Only"
            }
        else:
            conn.close()
            return None
    else:
        server_details = dict(row)
        server_details["source"] = "CMDB Full"

    # 2. Fetch GMUD History
    # Search for hostname in GMUD title or observation
    # Also match environment/client if possible to reduce false positives, 
    # but hostname is usually unique enough.
    gmud_query = """
        SELECT * FROM gmuds 
        WHERE (title LIKE ? OR observation LIKE ?)
        ORDER BY start_date DESC
    """
    search_term = f"%{hostname}%"
    c.execute(gmud_query, (search_term, search_term))
    gmuds = [dict(r) for r in c.fetchall()]

    conn.close()
    
    return {
        "server": server_details,
        "gmuds": gmuds
    }
