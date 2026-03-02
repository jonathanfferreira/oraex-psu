"""
ORAEX PSU Manager — Database Models & Queries (PostgreSQL)
"""
import psycopg2
import psycopg2.extras
import os
from config import DATABASE_URL
from werkzeug.security import generate_password_hash, check_password_hash


def get_connection():
    """Get a PostgreSQL connection via psycopg2."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ── Servers (from "GetNet - Oracle Databases" sheet) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role TEXT DEFAULT 'viewer',
            client_restriction TEXT DEFAULT 'none',
            squad TEXT DEFAULT 'dba',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Squads ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS squads (
            id SERIAL PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT DEFAULT '#6366f1',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Insert default squads (ignore if already exists)
    default_squads = [
        ('dba', 'DBA / Banco de Dados', 'Oracle, SQL Server, MySQL, PostgreSQL', '#6df5e3'),
        ('patch', 'Patch Manager', 'OS patches, Windows/Linux KB updates', '#f59e0b'),
        ('middleware', 'Middleware / DevOps', 'WebLogic, Tomcat, Apache, JBoss', '#8b5cf6'),
        ('cloud', 'Cloud', 'AWS, Azure, GCP infrastructure', '#3b82f6'),
    ]
    for slug, name, desc, color in default_squads:
        cursor.execute(
            "INSERT INTO squads (slug, name, description, color) VALUES (%s, %s, %s, %s) ON CONFLICT (slug) DO NOTHING",
            (slug, name, desc, color)
        )
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

    # Migrations: add columns that may be missing from older databases
    # PostgreSQL supports ADD COLUMN IF NOT EXISTS (9.6+) — safe to run repeatedly
    migrations = [
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS needs_replan TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS new_start_date TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS new_end_date TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS new_gmud TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS vulnerability TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS opened_by TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS vulnerability_before TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS vulnerability_after TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS closing_code TEXT",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "ALTER TABLE gmuds ADD COLUMN IF NOT EXISTS squad TEXT DEFAULT 'dba'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS client_restriction TEXT DEFAULT 'none'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS squad TEXT DEFAULT 'dba'",
    ]
    for migration in migrations:
        try:
            cursor.execute(migration)
            conn.commit()
        except Exception:
            conn.rollback()  # Reset transaction state before next migration

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully!")


# ══════════════════════════════════════════════════════════
#  QUERY FUNCTIONS
# ══════════════════════════════════════════════════════════

def get_dashboard_stats(client=None):
    """Get KPI numbers for the dashboard."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    stats = {}

    # Prepara restrições de cliente com base no sistema que o usuário preencheu ou solicitou
    gmuds_client_filter = " AND client = %s" if client and client != 'none' else ""
    cmdb_client_filter = " WHERE client = %s" if client and client != 'none' else ""
    client_param = [client] if client and client != 'none' else []

    # Total Oracle servers (servers is mostly GetNet)
    if client == 'PagoNxt':
        stats["total_servers"] = 0
        stats["total_rows"] = 0
    else:
        c.execute("SELECT COALESCE(SUM(total_servers), 0) AS total FROM servers")
        stats["total_servers"] = c.fetchone()['total']
        c.execute("SELECT COUNT(*) AS cnt FROM servers")
        stats["total_rows"] = c.fetchone()['cnt']

    # Servers with GGS
    c.execute("SELECT COUNT(*) AS cnt FROM servers WHERE has_ggs = 1")
    stats["total_ggs"] = c.fetchone()['cnt']

    # Standalone vs with standby
    c.execute("SELECT COUNT(*) AS cnt FROM servers WHERE has_standby = 1")
    stats["with_standby"] = c.fetchone()['cnt']
    c.execute("SELECT COUNT(*) AS cnt FROM servers WHERE has_standby = 0")
    stats["standalone"] = c.fetchone()['cnt']

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
    c.execute("SELECT COUNT(*) AS cnt FROM cmdb_databases")
    stats["total_cmdb"] = c.fetchone()['cnt']

    # Total CMDB Full
    c.execute(f"SELECT COUNT(*) AS cnt FROM cmdb_full{cmdb_client_filter}", client_param)
    stats["total_cmdb_full"] = c.fetchone()['cnt']

    # CMDB by type (using cmdb_full is better if we have client filters)
    c.execute(f"""
        SELECT db_type, COUNT(*) as cnt
        FROM cmdb_full
        WHERE db_type IS NOT NULL AND db_type != ''
        {cmdb_client_filter.replace('WHERE', 'AND')}
        GROUP BY db_type
        ORDER BY cnt DESC
    """, client_param)
    stats["cmdb_by_type"] = [dict(r) for r in c.fetchall()]

    # GMUDs stats
    c.execute(f"SELECT COUNT(*) AS cnt FROM gmuds WHERE 1=1 {gmuds_client_filter}", client_param)
    stats["total_gmuds"] = c.fetchone()['cnt']

    c.execute(f"""
        SELECT status, COUNT(*) as cnt
        FROM gmuds
        WHERE status IS NOT NULL AND status != '' {gmuds_client_filter}
        GROUP BY status
        ORDER BY cnt DESC
    """, client_param)
    stats["gmuds_by_status"] = [dict(r) for r in c.fetchall()]

    # GMUDs by month
    c.execute(f"""
        SELECT year, month, COUNT(*) as cnt
        FROM gmuds
        WHERE 1=1 {gmuds_client_filter}
        GROUP BY year, month
        ORDER BY year, month
    """, client_param)
    stats["gmuds_by_month"] = [dict(r) for r in c.fetchall()]

    # GMUDs by assigned person
    c.execute(f"""
        SELECT assigned_to, COUNT(*) as cnt
        FROM gmuds
        WHERE assigned_to IS NOT NULL AND assigned_to != '' {gmuds_client_filter}
        GROUP BY assigned_to
        ORDER BY cnt DESC
    """, client_param)
    stats["gmuds_by_person"] = [dict(r) for r in c.fetchall()]

    # CMDB by environment (using cmdb_full)
    c.execute(f"""
        SELECT environment, COUNT(*) as cnt
        FROM cmdb_full
        WHERE environment IS NOT NULL AND environment != ''
        {cmdb_client_filter.replace('WHERE', 'AND')}
        GROUP BY environment
        ORDER BY cnt DESC
    """, client_param)
    stats["cmdb_by_env"] = [dict(r) for r in c.fetchall()]

    # CMDB by status (using cmdb_full)
    c.execute(f"""
        SELECT status, COUNT(*) as cnt
        FROM cmdb_full
        WHERE status IS NOT NULL AND status != ''
        {cmdb_client_filter.replace('WHERE', 'AND')}
        GROUP BY status
        ORDER BY cnt DESC
    """, client_param)
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
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT * FROM servers WHERE 1=1"
    count_query = "SELECT COUNT(*) AS cnt FROM servers WHERE 1=1"
    params = []

    if environment:
        query += " AND environment = %s"
        count_query += " AND environment = %s"
        params.append(environment)
    if psu_version:
        query += " AND psu_version = %s"
        count_query += " AND psu_version = %s"
        params.append(psu_version)
    if search:
        query += " AND (primary_hostname LIKE %s OR standby_hostname LIKE %s OR system_product LIKE %s OR responsible_team LIKE %s)"
        count_query += " AND (primary_hostname LIKE %s OR standby_hostname LIKE %s OR system_product LIKE %s OR responsible_team LIKE %s)"
        search_param = f"%{search}%"
        params.extend([search_param] * 4)

    c.execute(count_query, params)
    total = c.fetchone()['cnt']

    query += " ORDER BY environment, primary_hostname"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

    c.execute(query, params)
    servers = [dict(r) for r in c.fetchall()]

    conn.close()
    return {"servers": servers, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


def get_gmuds(client=None, year=None, month=None, status=None, assigned_to=None, search=None, squad=None, page=1, per_page=50):
    """Get GMUDs with optional filters and pagination."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT * FROM gmuds WHERE 1=1"
    count_query = "SELECT COUNT(*) AS cnt FROM gmuds WHERE 1=1"
    params = []

    if client and client != 'none' and client != 'Todos':
        query += " AND client = %s"
        count_query += " AND client = %s"
        params.append(client)
    if squad and squad != 'all':
        query += " AND squad = %s"
        count_query += " AND squad = %s"
        params.append(squad)
    if year:
        query += " AND year = %s"
        count_query += " AND year = %s"
        params.append(year)
    if month:
        query += " AND month = %s"
        count_query += " AND month = %s"
        params.append(month)
    if status:
        query += " AND status = %s"
        count_query += " AND status = %s"
        params.append(status)
    if assigned_to:
        query += " AND assigned_to = %s"
        count_query += " AND assigned_to = %s"
        params.append(assigned_to)
    if search:
        query += " AND (change_number LIKE %s OR title LIKE %s OR assigned_to LIKE %s)"
        count_query += " AND (change_number LIKE %s OR title LIKE %s OR assigned_to LIKE %s)"
        search_param = f"%{search}%"
        params.extend([search_param] * 3)

    c.execute(count_query, params)
    total = c.fetchone()['cnt']

    query += " ORDER BY start_date DESC"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

    c.execute(query, params)
    gmuds = [dict(r) for r in c.fetchall()]

    conn.close()
    return {"gmuds": gmuds, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


def get_cmdb_databases(environment=None, db_type=None, status=None, search=None, page=1, per_page=50):
    """Get CMDB databases with optional filters."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT * FROM cmdb_databases WHERE 1=1"
    count_query = "SELECT COUNT(*) AS cnt FROM cmdb_databases WHERE 1=1"
    params = []

    if environment:
        query += " AND environment = %s"
        count_query += " AND environment = %s"
        params.append(environment)
    if db_type:
        query += " AND db_type = %s"
        count_query += " AND db_type = %s"
        params.append(db_type)
    if status:
        query += " AND status = %s"
        count_query += " AND status = %s"
        params.append(status)
    if search:
        query += " AND (name LIKE %s OR contingency_name LIKE %s OR system_product LIKE %s OR responsible_team LIKE %s)"
        count_query += " AND (name LIKE %s OR contingency_name LIKE %s OR system_product LIKE %s OR responsible_team LIKE %s)"
        search_param = f"%{search}%"
        params.extend([search_param] * 4)

    c.execute(count_query, params)
    total = c.fetchone()['cnt']

    query += " ORDER BY environment, name"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

    c.execute(query, params)
    databases = [dict(r) for r in c.fetchall()]

    conn.close()
    return {"databases": databases, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


def get_filter_options():
    """Get unique values for filter dropdowns."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    options = {}

    c.execute("SELECT DISTINCT environment FROM servers WHERE environment IS NOT NULL AND environment != '' ORDER BY environment")
    options["server_environments"] = [r['environment'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT psu_version FROM servers WHERE psu_version IS NOT NULL AND psu_version != '' ORDER BY psu_version")
    options["psu_versions"] = [r['psu_version'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT status FROM gmuds WHERE status IS NOT NULL AND status != '' ORDER BY status")
    options["gmud_statuses"] = [r['status'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT assigned_to FROM gmuds WHERE assigned_to IS NOT NULL AND assigned_to != '' ORDER BY assigned_to")
    options["gmud_assignees"] = [r['assigned_to'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT year FROM gmuds ORDER BY year")
    options["gmud_years"] = [r['year'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT environment FROM cmdb_databases WHERE environment IS NOT NULL AND environment != '' ORDER BY environment")
    options["cmdb_environments"] = [r['environment'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT db_type FROM cmdb_databases WHERE db_type IS NOT NULL AND db_type != '' ORDER BY db_type")
    options["cmdb_db_types"] = [r['db_type'] for r in c.fetchall()]

    conn.close()
    return options


def get_planning_data():
    """Get all planning entries."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM planning ORDER BY hostname")
    data = [dict(r) for r in c.fetchall()]
    conn.close()
    return data


def get_pagonxt_databases(search=None, page=1, per_page=50):
    """Get PagoNxt databases with optional search and pagination."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT * FROM pagonxt_databases WHERE 1=1"
    count_query = "SELECT COUNT(*) AS cnt FROM pagonxt_databases WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE %s OR product LIKE %s OR description LIKE %s OR ip LIKE %s)"
        count_query += " AND (name LIKE %s OR product LIKE %s OR description LIKE %s OR ip LIKE %s)"
        search_param = f"%{search}%"
        params.extend([search_param] * 4)

    c.execute(count_query, params)
    total = c.fetchone()['cnt']

    query += " ORDER BY environment, name"
    query += " LIMIT %s OFFSET %s"

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
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
        where.append("c.client = %s")
        params.append(client)
    if db_type:
        where.append("c.db_type = %s")
        params.append(db_type)
    if status:
        where.append("c.status = %s")
        params.append(status)
    if environment:
        where.append("c.environment = %s")
        params.append(environment)
    if search:
        where.append("(c.hostname LIKE %s OR c.contingency LIKE %s OR c.system_product LIKE %s OR c.description LIKE %s)")
        s = f"%{search}%"
        params.extend([s, s, s, s])

    where_clause = " WHERE " + " AND ".join(where) if where else ""

    # Count total
    c.execute(f"SELECT COUNT(*) AS cnt {base_query} {where_clause}", params)
    total = c.fetchone()['cnt']

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
        LIMIT %s OFFSET %s
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
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    stats = {}
    client_filter = ""
    params = []
    if client:
        client_filter = " WHERE client = %s"
        params = [client]

    # Total DB servers
    c.execute(f"SELECT COUNT(*) AS cnt FROM cmdb_full{client_filter}", params)
    stats["total"] = c.fetchone()['cnt']

    # Active count
    active_filter = f"{client_filter} {'AND' if client else 'WHERE'} status IN ('Ativo', 'Running')"
    c.execute(f"SELECT COUNT(*) AS cnt FROM cmdb_full{active_filter}", params)
    stats["active"] = c.fetchone()['cnt']

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
        db_type_sql += " AND client = %s"
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
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    options = {}

    c.execute("SELECT DISTINCT client FROM cmdb_full WHERE client IS NOT NULL ORDER BY client")
    options["clients"] = [r['client'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT db_type FROM cmdb_full WHERE db_type IS NOT NULL AND db_type != '' ORDER BY db_type")
    options["db_types"] = [r['db_type'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT status FROM cmdb_full WHERE status IS NOT NULL AND status != '' ORDER BY status")
    options["statuses"] = [r['status'] for r in c.fetchall()]

    c.execute("SELECT DISTINCT environment FROM cmdb_full WHERE environment IS NOT NULL AND environment != '' ORDER BY environment")
    options["environments"] = [r['environment'] for r in c.fetchall()]

    conn.close()
    return options


def get_user_by_id(user_id):
    """Get user by ID for Flask-Login. Returns None if DB unavailable."""
    try:
        conn = get_connection()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except psycopg2.OperationalError:
        return None


def get_user_by_username(username):
    """Get user by username."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM users WHERE username = %s", (username,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username, password, display_name=None, role='viewer', client_restriction='none', squad='dba'):
    """Create a new user with hashed password."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    pw_hash = generate_password_hash(password)
    c.execute("""
        INSERT INTO users (username, password_hash, display_name, role, client_restriction, squad)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (username, pw_hash, display_name or username, role, client_restriction, squad))
    conn.commit()
    user_id = c.fetchone()['id']
    conn.close()
    return user_id


def get_all_squads():
    """Get all active squads."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM squads WHERE is_active = 1 ORDER BY id")
    squads = [dict(r) for r in c.fetchall()]
    conn.close()
    return squads


def verify_user(username, password):
    """Verify username and password. Returns user dict or None."""
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None


def get_all_users():
    """Get all users."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT id, username, display_name, role, client_restriction, squad, is_active, created_at FROM users ORDER BY id")
    users = [dict(r) for r in c.fetchall()]
    conn.close()
    return users


def update_user_status(user_id, is_active):
    """Enable or disable a user."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("UPDATE users SET is_active = %s WHERE id = %s", (1 if is_active else 0, user_id))
    conn.commit()
    conn.close()


def reset_user_password(user_id, new_password):
    """Reset a user's password."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    pw_hash = generate_password_hash(new_password)
    c.execute("UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, user_id))
    conn.commit()
    conn.close()


def ensure_admin_exists():
    """Create default admin user if no users exist."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT COUNT(*) AS cnt FROM users")
    count = c.fetchone()['cnt']
    conn.close()
    if count == 0:
        create_user('admin', 'oraex2025', 'Administrador', 'admin', 'none')
        print("  Default admin user created (admin / oraex2025)")


def get_gmud_by_id(gmud_id):
    """Get a single GMUD by ID."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM gmuds WHERE id = %s", (gmud_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_gmud(gmud_id, data):
    """Update an existing GMUD."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("""
        UPDATE gmuds SET
            client=%s, db_type=%s, environment=%s, status=%s,
            start_date=%s, end_date=%s, change_number=%s, title=%s,
            assigned_to=%s, observation=%s, vulnerability=%s, opened_by=%s,
            squad=%s
        WHERE id = %s
    """, (
        data.get('client'), data.get('db_type'), data.get('environment'),
        data.get('status'), data.get('start_date'), data.get('end_date'),
        data.get('change_number'), data.get('title'), data.get('assigned_to'),
        data.get('observation'), data.get('vulnerability'), data.get('opened_by'),
        data.get('squad', 'dba'),
        gmud_id
    ))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0


def delete_gmud(gmud_id):
    """Delete a GMUD by ID."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("DELETE FROM gmuds WHERE id = %s", (gmud_id,))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0


def search_hostnames(query, limit=15):
    """Search hostnames across servers, cmdb_full, and cmdb_databases tables."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    search_param = f"%{query}%"

    c.execute("""
        SELECT DISTINCT hostname, source FROM (
            SELECT primary_hostname AS hostname, 'servers' AS source
            FROM servers WHERE primary_hostname LIKE %s
            UNION
            SELECT standby_hostname AS hostname, 'servers' AS source
            FROM servers WHERE standby_hostname LIKE %s AND standby_hostname IS NOT NULL AND standby_hostname != ''
            UNION
            SELECT hostname, 'cmdb_full' AS source
            FROM cmdb_full WHERE hostname LIKE %s
            UNION
            SELECT contingency AS hostname, 'cmdb_full' AS source
            FROM cmdb_full WHERE contingency LIKE %s AND contingency IS NOT NULL AND contingency != ''
            UNION
            SELECT name AS hostname, 'cmdb' AS source
            FROM cmdb_databases WHERE name LIKE %s
            UNION
            SELECT contingency_name AS hostname, 'cmdb' AS source
            FROM cmdb_databases WHERE contingency_name LIKE %s AND contingency_name IS NOT NULL AND contingency_name != ''
        ) AS hostnames
        WHERE hostname IS NOT NULL AND hostname != ''
        ORDER BY hostname
        LIMIT %s
    """, (search_param, search_param, search_param, search_param, search_param, search_param, limit))

    results = [{"hostname": r["hostname"], "source": r["source"]} for r in c.fetchall()]
    conn.close()
    return results


if __name__ == "__main__":
    init_db()

def get_server_details(hostname):
    """Get detailed info for a specific server (CMDB + Inventory + GMUDs)."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
        WHERE lower(c.hostname) = lower(%s)
    """
    c.execute(query, (hostname,))
    row = c.fetchone()

    # If not found in CMDB Full, try searching just in Servers (Legacy Inventory)
    # This handles case where a server might only exist in the old inventory sheet
    if not row:
        c.execute("SELECT * FROM servers WHERE lower(primary_hostname) = lower(%s)", (hostname,))
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
        WHERE (title LIKE %s OR observation LIKE %s)
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


# ══════════════════════════════════════════════════════════
#  MANAGEMENT FEATURES
# ══════════════════════════════════════════════════════════

def get_overdue_gmuds(client=None):
    """Return GMUDs whose end_date has passed but are not closed/cancelled."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = """
        SELECT id, change_number, title, status, end_date, client,
               assigned_to, environment, db_type,
               EXTRACT(DAY FROM (NOW() - end_date::timestamp))::INTEGER AS days_overdue
        FROM gmuds
        WHERE end_date IS NOT NULL AND end_date != ''
          AND end_date < CURRENT_DATE
          AND upper(status) NOT IN ('ENCERRADA', 'CANCELADA', 'ENCERRADO', 'CANCELADO')
    """
    params = []
    if client and client != 'Todos':
        query += " AND client = %s"
        params.append(client)
    query += " ORDER BY end_date ASC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"count": len(rows), "gmuds": rows}


def get_gmuds_calendar(year, month, client=None):
    """Return GMUDs for a given year/month grouped by start_date (YYYY-MM-DD)."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = """
        SELECT id, change_number, title, status, environment, db_type,
               client, assigned_to, start_date, end_date, observation
        FROM gmuds
        WHERE year = %s AND month = %s
    """
    params = [year, month]
    if client and client != 'Todos':
        query += " AND client = %s"
        params.append(client)
    query += " ORDER BY start_date ASC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    # Group by date (YYYY-MM-DD part of start_date)
    from collections import defaultdict
    days = defaultdict(list)
    for g in rows:
        date_key = (g.get('start_date') or '')[:10]
        if date_key:
            days[date_key].append(g)
    return {"year": year, "month": month, "total": len(rows), "days": dict(days)}


def get_sla_metrics(client=None):
    """Calculate SLA and management metrics for GMUDs."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    where = "WHERE 1=1"
    params = []
    if client and client != 'Todos':
        where += " AND client = %s"
        params.append(client)

    # Overall counts
    c.execute(f"SELECT COUNT(*) AS cnt FROM gmuds {where}", params)
    total = c.fetchone()['cnt'] or 0

    c.execute(f"SELECT COUNT(*) AS cnt FROM gmuds {where} AND upper(status) IN ('ENCERRADA','ENCERRADO')", params)
    closed = c.fetchone()['cnt'] or 0

    c.execute(f"SELECT COUNT(*) AS cnt FROM gmuds {where} AND upper(status) IN ('CANCELADA','CANCELADO')", params)
    cancelled = c.fetchone()['cnt'] or 0

    c.execute(f"SELECT COUNT(*) AS cnt FROM gmuds {where} AND upper(needs_replan) = 'Y'", params)
    replanned = c.fetchone()['cnt'] or 0

    # On-time: closed GMUDs where end_date was not overdue
    c.execute(f"""
        SELECT COUNT(*) AS cnt FROM gmuds
        {where}
        AND upper(status) IN ('ENCERRADA','ENCERRADO')
        AND end_date IS NOT NULL AND end_date != ''
        AND start_date IS NOT NULL AND start_date != ''
        AND end_date >= start_date
    """, params)
    on_time = c.fetchone()['cnt'] or 0

    # Average duration (days)
    c.execute(f"""
        SELECT AVG(EXTRACT(DAY FROM (end_date::timestamp - start_date::timestamp))) AS avg_days
        FROM gmuds {where}
        AND end_date IS NOT NULL AND end_date != ''
        AND start_date IS NOT NULL AND start_date != ''
        AND end_date > start_date
    """, params)
    avg_row = c.fetchone()
    avg_duration = round(avg_row['avg_days'], 1) if avg_row and avg_row['avg_days'] else 0

    # By month (last 6 months relative to current data)
    c.execute(f"""
        SELECT year, month,
               COUNT(*) AS total,
               SUM(CASE WHEN upper(status) IN ('ENCERRADA','ENCERRADO') THEN 1 ELSE 0 END) AS closed
        FROM gmuds {where}
        GROUP BY year, month
        ORDER BY year DESC, month DESC
        LIMIT 6
    """, params)
    by_month_raw = [dict(r) for r in c.fetchall()]
    by_month = list(reversed(by_month_raw))

    # By client breakdown
    c.execute(f"""
        SELECT client,
               COUNT(*) AS total,
               SUM(CASE WHEN upper(status) IN ('ENCERRADA','ENCERRADO') THEN 1 ELSE 0 END) AS closed
        FROM gmuds {where}
        GROUP BY client ORDER BY total DESC
    """, params)
    by_client = [dict(r) for r in c.fetchall()]

    # Top 5 people by total GMUDs
    c.execute(f"""
        SELECT assigned_to,
               COUNT(*) AS total,
               SUM(CASE WHEN upper(status) IN ('ENCERRADA','ENCERRADO') THEN 1 ELSE 0 END) AS closed
        FROM gmuds {where}
        AND assigned_to IS NOT NULL AND assigned_to != ''
        GROUP BY assigned_to ORDER BY total DESC LIMIT 5
    """, params)
    by_person = [dict(r) for r in c.fetchall()]

    # By environment
    c.execute(f"""
        SELECT environment, COUNT(*) AS total
        FROM gmuds {where}
        AND environment IS NOT NULL AND environment != ''
        GROUP BY environment ORDER BY total DESC
    """, params)
    by_env = [dict(r) for r in c.fetchall()]

    # By squad
    c.execute(f"""
        SELECT COALESCE(squad, 'dba') AS squad,
               COUNT(*) AS total,
               SUM(CASE WHEN upper(status) IN ('ENCERRADA','ENCERRADO') THEN 1 ELSE 0 END) AS closed
        FROM gmuds {where}
        GROUP BY COALESCE(squad, 'dba') ORDER BY total DESC
    """, params)
    by_squad = [dict(r) for r in c.fetchall()]

    conn.close()

    success_rate = round(closed / total * 100, 1) if total > 0 else 0
    replan_rate = round(replanned / total * 100, 1) if total > 0 else 0
    on_time_rate = round(on_time / closed * 100, 1) if closed > 0 else 0

    return {
        "total": total,
        "closed": closed,
        "cancelled": cancelled,
        "replanned": replanned,
        "success_rate": success_rate,
        "replan_rate": replan_rate,
        "on_time_rate": on_time_rate,
        "avg_duration_days": avg_duration,
        "by_month": by_month,
        "by_client": by_client,
        "by_person": by_person,
        "by_env": by_env,
        "by_squad": by_squad,
    }
