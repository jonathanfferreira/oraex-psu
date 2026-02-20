"""
ORAEX PSU Manager — Flask Application
"""
from flask import Flask, render_template, jsonify, request, Response, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import csv
import io
from database import (
    init_db, get_dashboard_stats, get_servers, get_gmuds,
    get_cmdb_databases, get_filter_options, get_planning_data,
    get_cmdb_full, get_cmdb_full_stats, get_cmdb_full_filters,
    get_pagonxt_databases, search_hostnames,
    get_gmud_by_id, update_gmud, delete_gmud,
    get_user_by_id, verify_user, ensure_admin_exists,
    get_server_details
)
from import_excel import run_import, run_cmdb_full_import
from import_qualys import import_qualys_scan
from export_excel import write_gmud_to_excel
from config import SECRET_KEY, DEBUG, HOST, PORT, MAX_CONTENT_LENGTH, QUALYS_PAGONXT_PATH, QUALYS_GETNET_PATH
import sqlite3
import os
import tempfile

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


# ══════════════════════════════════════════════════════════
#  AUTHENTICATION (Flask-Login)
# ══════════════════════════════════════════════════════════

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar o sistema.'


class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.display_name = user_dict['display_name']
        self.role = user_dict['role']


@login_manager.user_loader
def load_user(user_id):
    user_dict = get_user_by_id(int(user_id))
    if user_dict:
        return User(user_dict)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({"message": "Autenticação necessária"}), 401
    return redirect(url_for('login', next=request.url))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user_dict = verify_user(username, password)
        if user_dict:
            login_user(User(user_dict))
            next_page = request.args.get('next', '/')
            return redirect(next_page)
        return render_template("login.html", error="Usuário ou senha incorretos")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# ══════════════════════════════════════════════════════════
#  PÁGINAS (Frontend Routes)
# ══════════════════════════════════════════════════════════

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@app.route("/inventory")
@login_required
def inventory():
    return render_template("inventory.html", active="inventory")

@app.route("/vulnerabilities")
@login_required
def vulnerabilities():
    return render_template("vulnerabilities.html", active="vulnerabilities")


@app.route("/cmdb-full")
@login_required
def cmdb_full():
    return render_template("cmdb_full.html", active="cmdb_full")


@app.route("/gmud")
@login_required
def gmud():
    return render_template("gmud.html", active="gmud")


@app.route("/gmud/create")
@login_required
def gmud_create():
    """Página de formulário para criar nova GMUD."""
    return render_template("gmud_create.html", active="gmud")


@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html", active="reports")


# ══════════════════════════════════════════════════════════
#  API ENDPOINTS (Backend)
# ══════════════════════════════════════════════════════════

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    stats = get_dashboard_stats()
    return jsonify(stats)


@app.route("/api/servers")
@login_required
def api_servers():
    data = get_servers(
        environment=request.args.get("environment"),
        psu_version=request.args.get("psu_version"),
        search=request.args.get("search"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 50)),
    )
    return jsonify(data)


@app.route("/api/gmuds")
@login_required
def api_gmuds():
    data = get_gmuds(
        year=request.args.get("year", type=int),
        month=request.args.get("month", type=int),
        status=request.args.get("status"),
        assigned_to=request.args.get("assigned_to"),
        search=request.args.get("search"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 50)),
    )
    return jsonify(data)


@app.route("/api/gmud/create", methods=["POST"])
@login_required
def api_create_gmud():
    """Recebe dados do formulário e grava na planilha Excel."""
    try:
        data = request.json
        success, msg = write_gmud_to_excel(data)
        if success:
            return jsonify({"message": msg})
        else:
            return jsonify({"message": msg}), 500
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/api/cmdb")
@login_required
def api_cmdb():
    data = get_cmdb_databases(
        environment=request.args.get("environment"),
        db_type=request.args.get("db_type"),
        status=request.args.get("status"),
        search=request.args.get("search"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 50)),
    )
    return jsonify(data)


@app.route("/api/cmdb-full")
@login_required
def api_cmdb_full():
    data = get_cmdb_full(
        client=request.args.get("client"),
        db_type=request.args.get("db_type"),
        status=request.args.get("status"),
        environment=request.args.get("environment"),
        search=request.args.get("search"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 50)),
    )
    return jsonify(data)


@app.route("/server/<path:hostname>")
@login_required
def server_details(hostname):
    """Página de detalhes do servidor."""
    result = get_server_details(hostname)
    if not result:
        return f"<h3>Servidor '{hostname}' não encontrado.</h3><a href='/cmdb-full'>Voltar</a>", 404
    return render_template("server_details.html", 
                         server=result['server'], 
                         gmuds=result['gmuds'], 
                         active="cmdb_full")


@app.route("/api/cmdb-full/stats")
@login_required
def api_cmdb_full_stats():
    stats = get_cmdb_full_stats(client=request.args.get("client"))
    return jsonify(stats)


@app.route("/api/cmdb-full/filters")
@login_required
def api_cmdb_full_filters():
    options = get_cmdb_full_filters()
    return jsonify(options)


@app.route("/api/pagonxt")
@login_required
def api_pagonxt():
    data = get_pagonxt_databases(
        search=request.args.get("search"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 50)),
    )
    return jsonify(data)


@app.route("/api/planning")
@login_required
def api_planning():
    data = get_planning_data()
    return jsonify(data)


@app.route("/api/filters")
@login_required
def api_filters():
    options = get_filter_options()
    return jsonify(options)


@app.route("/api/import", methods=["POST"])
@login_required
def api_import():
    """Importa planilha Consolidação — aceita upload ou usa arquivo local."""
    try:
        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            # Salvar arquivo enviado em diretório temporário
            suffix = os.path.splitext(uploaded.filename)[1] or ".xlsm"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            uploaded.save(tmp_path)
            try:
                result = run_import(excel_path=tmp_path)
            finally:
                os.unlink(tmp_path)  # Remove arquivo temporário
        else:
            result = run_import()

        if result:
            return jsonify({"status": "success", "message": "Importação da Consolidação concluída com sucesso!"})
        else:
            return jsonify({"status": "error", "message": "Falha na importação. Verifique o arquivo."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/import-cmdb-full", methods=["POST"])
@login_required
def api_import_cmdb_full():
    """Importa planilha CMDB Full — aceita upload ou usa arquivo local."""
    try:
        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            suffix = os.path.splitext(uploaded.filename)[1] or ".xlsx"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            uploaded.save(tmp_path)
            try:
                result = run_cmdb_full_import(excel_path=tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            result = run_cmdb_full_import()

        if result:
            return jsonify({"status": "success", "message": "Importação do CMDB Full concluída com sucesso!"})
        else:
            return jsonify({"status": "error", "message": "Falha na importação. Verifique o arquivo."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/import-qualys", methods=["POST"])
@login_required
def api_import_qualys():
    """Importa planilhas do Qualys - aceita upload ou usa arquivo local."""
    source_type = request.form.get('source_type', 'GetNet')
    try:
        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            suffix = os.path.splitext(uploaded.filename)[1] or ".xlsx"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            uploaded.save(tmp_path)
            try:
                result = import_qualys_scan(tmp_path, source_type)
            finally:
                os.unlink(tmp_path)
        else:
            path = QUALYS_PAGONXT_PATH if source_type == 'PagoNxt' else QUALYS_GETNET_PATH
            result = import_qualys_scan(path, source_type)

        if result:
            return jsonify({"status": "success", "message": f"Importação Qualys {source_type} concluída com sucesso!"})
        else:
            return jsonify({"status": "error", "message": "Falha na importação. Verifique o arquivo."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/vulnerabilities", methods=["GET"])
@login_required
def api_vulnerabilities():
    try:
        from database import get_connection
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cmdb_rows = cursor.execute("SELECT hostname, client, db_type, status FROM cmdb_full").fetchall()
        cmdb_dict = { (r['hostname'] or '').lower(): r for r in cmdb_rows if r['hostname'] }
        
        query = """
            SELECT d.id, d.qid, d.asset_name, d.asset_ip, d.environment, 
                   d.os, d.status, d.first_detected, d.last_detected,
                   v.title, v.severity, v.solution
            FROM qualys_detections d
            JOIN qualys_vulnerabilities v ON d.qid = v.qid
        """
        qualys_rows = cursor.execute(query).fetchall()
        
        result = []
        for q in qualys_rows:
            host_lower = (q['asset_name'] or '').lower()
            if host_lower in cmdb_dict:
                cmdb_ref = cmdb_dict[host_lower]
                row = dict(q)
                row['client'] = cmdb_ref['client']
                row['db_type'] = cmdb_ref['db_type']
                row['cmdb_status'] = cmdb_ref['status']
                result.append(row)
                
        def get_sev_order(sev):
            if sev == '5': return 1
            if sev == '4': return 2
            if sev == '3': return 3
            return 4
            
        result.sort(key=lambda x: (get_sev_order(str(x['severity'])), (x['asset_name'] or '').lower()))
        
        conn.close()
        return jsonify(result[:500])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/vulnerabilities/stats", methods=["GET"])
@login_required
def api_vulnerabilities_stats():
    try:
        from database import get_connection
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cmdb_rows = cursor.execute("SELECT hostname, client, db_type, environment, status FROM cmdb_full").fetchall()
        cmdb_dict = { (r['hostname'] or '').lower(): r for r in cmdb_rows if r['hostname'] }
        
        query = """
            SELECT d.asset_name, v.severity
            FROM qualys_detections d
            JOIN qualys_vulnerabilities v ON d.qid = v.qid
        """
        qualys_rows = cursor.execute(query).fetchall()
        conn.close()
        
        hosts_vuln = set()
        sev_counts = {}
        host_vuln_counts = {}
        
        for q in qualys_rows:
            host_lower = (q['asset_name'] or '').lower()
            if host_lower in cmdb_dict:
                hosts_vuln.add(host_lower)
                sev = str(q['severity'])
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
                
                if sev in ('4', '5'):
                    if host_lower not in host_vuln_counts:
                        host_vuln_counts[host_lower] = {
                            'asset_name': q['asset_name'], 
                            'db_type': cmdb_dict[host_lower]['db_type'],
                            'environment': cmdb_dict[host_lower]['environment'],
                            'count': 0
                        }
                    host_vuln_counts[host_lower]['count'] += 1
                    
        sev_breakdown = [{'severity': k, 'count': v} for k, v in sev_counts.items()]
        sev_breakdown.sort(key=lambda x: x['severity'], reverse=True)
        
        top_hosts = list(host_vuln_counts.values())
        top_hosts.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify({
            "total_db_hosts_vulnerable": len(hosts_vuln),
            "severity_breakdown": sev_breakdown,
            "top_vulnerable_hosts": top_hosts[:10]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/gmud/edit/<int:gmud_id>")
@login_required
def gmud_edit(gmud_id):
    """Página de edição de GMUD."""
    return render_template("gmud_edit.html", active="gmud", gmud_id=gmud_id)


@app.route("/api/gmud/<int:gmud_id>")
@login_required
def api_get_gmud(gmud_id):
    gmud = get_gmud_by_id(gmud_id)
    if not gmud:
        return jsonify({"message": "GMUD não encontrada"}), 404
    return jsonify(gmud)


@app.route("/api/gmud/<int:gmud_id>", methods=["PUT"])
@login_required
def api_update_gmud(gmud_id):
    try:
        data = request.json
        success = update_gmud(gmud_id, data)
        if success:
            return jsonify({"message": "GMUD atualizada com sucesso!"})
        return jsonify({"message": "GMUD não encontrada"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/api/gmud/<int:gmud_id>", methods=["DELETE"])
@login_required
def api_delete_gmud(gmud_id):
    try:
        success = delete_gmud(gmud_id)
        if success:
            return jsonify({"message": "GMUD excluída com sucesso!"})
        return jsonify({"message": "GMUD não encontrada"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/api/hostnames")
@login_required
def api_hostnames():
    """Search hostnames across all tables for autocomplete."""
    query = request.args.get("search", "")
    if len(query) < 2:
        return jsonify([])
    results = search_hostnames(query)
    return jsonify(results)


@app.route("/api/gmud/generate-title", methods=["POST"])
@login_required
def api_generate_gmud_title():
    """Gera um título padronizado para a GMUD."""
    data = request.json
    hostnames = data.get("hostnames", "")
    psu_version = data.get("psu_version", "19.29")
    gmud_type = data.get("type", "Escopo Fechado")
    priority = data.get("priority", "")

    # Build title
    prefix = f"[{gmud_type} - BD"
    if priority:
        prefix += f" - {priority}"
    prefix += "]"

    title = f"{prefix} Atualização PSU {psu_version} conforme orientação Oracle | {hostnames}"
    return jsonify({"title": title})


# ══════════════════════════════════════════════════════════
#  CSV EXPORT ENDPOINTS
# ══════════════════════════════════════════════════════════

def generate_csv(rows, fieldnames):
    """Generate CSV content from a list of dicts with UTF-8 BOM for Excel."""
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


@app.route("/api/servers/export")
@login_required
def api_servers_export():
    data = get_servers(
        environment=request.args.get("environment"),
        psu_version=request.args.get("psu_version"),
        search=request.args.get("search"),
        page=1, per_page=99999
    )
    fields = ["environment", "primary_hostname", "standby_hostname", "psu_version",
              "system_product", "responsible_team", "primary_contact",
              "start_time", "end_time", "observation"]
    content = generate_csv(data["servers"], fields)
    return Response(content, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=servidores_oracle.csv"})


@app.route("/api/gmuds/export")
@login_required
def api_gmuds_export():
    data = get_gmuds(
        year=request.args.get("year", type=int),
        month=request.args.get("month", type=int),
        status=request.args.get("status"),
        assigned_to=request.args.get("assigned_to"),
        search=request.args.get("search"),
        page=1, per_page=99999
    )
    fields = ["change_number", "title", "status", "environment", "db_type",
              "client", "start_date", "end_date", "assigned_to", "observation"]
    content = generate_csv(data["gmuds"], fields)
    return Response(content, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=gmuds.csv"})


@app.route("/api/cmdb-full/export")
@login_required
def api_cmdb_full_export():
    data = get_cmdb_full(
        client=request.args.get("client"),
        db_type=request.args.get("db_type"),
        status=request.args.get("status"),
        environment=request.args.get("environment"),
        search=request.args.get("search"),
        page=1, per_page=99999
    )
    fields = ["client", "hostname", "contingency", "db_type", "db_version",
              "status", "environment", "ip_service", "system_product",
              "responsible_team", "primary_contact"]
    content = generate_csv(data["data"], fields)
    return Response(content, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=cmdb_full.csv"})


# ══════════════════════════════════════════════════════════
#  INICIALIZAÇÃO (Startup)
# ══════════════════════════════════════════════════════════

# Inicializar DB sempre que o módulo for importado
# (necessário para gunicorn, que não roda via __main__)
init_db()
ensure_admin_exists()

if __name__ == "__main__":
    print(f"\n ORAEX PSU Manager")
    print(f" Open: http://{HOST}:{PORT}")
    print(f" Dashboard: http://{HOST}:{PORT}/")
    print(f" Inventory: http://{HOST}:{PORT}/inventory")
    print(f" CMDB Full: http://{HOST}:{PORT}/cmdb-full")
    print(f" GMUDs: http://{HOST}:{PORT}/gmud")
    print(f" Reports: http://{HOST}:{PORT}/reports")
    print(f" Login: http://{HOST}:{PORT}/login")
    print(f" Default user: admin / oraex2025\n")
    app.run(host=HOST, port=PORT, debug=DEBUG)
