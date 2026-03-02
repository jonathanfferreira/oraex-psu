"""
ORAEX PSU Manager — Flask Application
"""
from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, session, flash, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
import csv
import io
import sqlite3
import os
import tempfile
import re
import uuid
import threading
from werkzeug.security import generate_password_hash, check_password_hash
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

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Dict global para rastrear status dos uploads assíncronos em memória
UPLOAD_TASKS = {}


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
        self.client_restriction = user_dict.get('client_restriction', 'none')


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


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({"message": "Acesso negado: Requer privilégios de administrador"}), 403
            return "Acesso negado", 403
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user_dict = verify_user(username, password)
        if user_dict:
            if not user_dict.get('is_active', 1):
                return render_template("login.html", error="Usuário desativado")
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


@app.route("/users")
@login_required
@admin_required
def users_page():
    return render_template("users.html", active="users", page_title="Gestão de Usuários")


# ══════════════════════════════════════════════════════════
#  API ENDPOINTS (Backend)
# ══════════════════════════════════════════════════════════

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    client_param = request.args.get('client', 'Todos')
    user_restriction = getattr(current_user, 'client_restriction', 'none')
    
    # Se o usuário tem restrição fixa, ele sobrepõe a seleção do dropdown
    if user_restriction and user_restriction != 'none':
        client_param = user_restriction
        
    actual_client = None
    if client_param and client_param != 'Todos':
        actual_client = client_param

    stats = get_dashboard_stats(client=actual_client)
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
    client_param = request.args.get('client')
    user_restriction = getattr(current_user, 'client_restriction', 'none')
    if user_restriction and user_restriction != 'none':
        client_param = user_restriction

    data = get_gmuds(
        client=client_param,
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
    client_param = request.args.get("client")
    user_restriction = getattr(current_user, 'client_restriction', 'none')
    if user_restriction and user_restriction != 'none':
        client_param = user_restriction

    data = get_cmdb_full(
        client=client_param,
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
    client_param = request.args.get("client")
    user_restriction = getattr(current_user, 'client_restriction', 'none')
    if user_restriction and user_restriction != 'none':
        client_param = user_restriction

    stats = get_cmdb_full_stats(client=client_param)
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


def background_import_task(task_id, import_func, *args, **kwargs):
    """Executa a importação no background e atualiza o UPLOAD_TASKS."""
    UPLOAD_TASKS[task_id] = {"status": "processing", "message": "Importação iniciada...", "progress": 10}
    try:
        # Se um arquivo temporário foi passado via kwargs, capturamos para apagar depois
        tmp_path = kwargs.get('excel_path') or kwargs.get('file_path') or (args[0] if args else None)
        
        result = import_func(*args, **kwargs)
        
        if result:
            UPLOAD_TASKS[task_id] = {"status": "success", "message": "Importação concluída com sucesso!", "progress": 100}
        else:
            UPLOAD_TASKS[task_id] = {"status": "error", "message": "Falha na importação. Verifique o arquivo.", "progress": 100}
            
    except Exception as e:
        UPLOAD_TASKS[task_id] = {"status": "error", "message": str(e), "progress": 100}
        import traceback
        traceback.print_exc()
    finally:
        # Tenta remover o arquivo temp, se existir, para não lotar o disco
        try:
            tmp_path = kwargs.get('excel_path') or kwargs.get('file_path') or (args[0] if args else None)
            if tmp_path and os.path.exists(tmp_path) and "temp" in tmp_path.lower():
                os.unlink(tmp_path)
        except Exception:
            pass


@app.route("/api/task-status/<task_id>", methods=["GET"])
@login_required
def api_task_status(task_id):
    """Endpoint de polling para o frontend checar o status do upload."""
    task = UPLOAD_TASKS.get(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Tarefa não encontrada"}), 404
    return jsonify(task)


@app.route("/api/import", methods=["POST"])
@login_required
def api_import():
    """Importa planilha Consolidação — Assíncrono."""
    try:
        task_id = str(uuid.uuid4())
        uploaded = request.files.get("file")
        
        if uploaded and uploaded.filename:
            suffix = os.path.splitext(uploaded.filename)[1] or ".xlsm"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            uploaded.save(tmp_path)
            
            thread = threading.Thread(target=background_import_task, args=(task_id, run_import), kwargs={"excel_path": tmp_path})
            thread.start()
        else:
            thread = threading.Thread(target=background_import_task, args=(task_id, run_import))
            thread.start()

        return jsonify({"status": "processing", "task_id": task_id, "message": "Importação iniciada."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/import-cmdb-full", methods=["POST"])
@login_required
def api_import_cmdb_full():
    """Importa planilha CMDB Full — Assíncrono."""
    try:
        task_id = str(uuid.uuid4())
        uploaded = request.files.get("file")
        
        if uploaded and uploaded.filename:
            suffix = os.path.splitext(uploaded.filename)[1] or ".xlsx"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            uploaded.save(tmp_path)
            
            thread = threading.Thread(target=background_import_task, args=(task_id, run_cmdb_full_import), kwargs={"excel_path": tmp_path})
            thread.start()
        else:
            thread = threading.Thread(target=background_import_task, args=(task_id, run_cmdb_full_import))
            thread.start()

        return jsonify({"status": "processing", "task_id": task_id, "message": "Importação CMDB Full iniciada."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/import-qualys", methods=["POST"])
@login_required
def api_import_qualys():
    """Importa planilhas do Qualys - Assíncrono."""
    source_type = request.form.get('source_type', 'GetNet')
    try:
        task_id = str(uuid.uuid4())
        uploaded = request.files.get("file")
        
        if uploaded and uploaded.filename:
            suffix = os.path.splitext(uploaded.filename)[1] or ".xlsx"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            uploaded.save(tmp_path)
            
            thread = threading.Thread(target=background_import_task, args=(task_id, import_qualys_scan, tmp_path, source_type))
            thread.start()
        else:
            path = QUALYS_PAGONXT_PATH if source_type == 'PagoNxt' else QUALYS_GETNET_PATH
            thread = threading.Thread(target=background_import_task, args=(task_id, import_qualys_scan, path, source_type))
            thread.start()

        return jsonify({"status": "processing", "task_id": task_id, "message": f"Importação Qualys {source_type} iniciada."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/vulnerabilities", methods=["GET"])
@login_required
def api_vulnerabilities():
    try:
        from database import get_connection
        import re
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        client_param = request.args.get("client")
        user_restriction = getattr(current_user, 'client_restriction', 'none')
        if user_restriction and user_restriction != 'none':
            client_param = user_restriction
            
        where_clause = ""
        params = []
        if client_param and client_param != 'Todos':
            where_clause = " WHERE client = ?"
            params.append(client_param)
            
        cmdb_rows = cursor.execute(f"SELECT hostname, client, db_type, status FROM cmdb_full{where_clause}", params).fetchall()
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
                
                # Classificação de Squad Baseada no Título da Vulnerabilidade
                title = str(row['title'] or '').lower()
                squad = "SO / Infra" # Default
                
                # Regras de Negócio e Regex
                if re.search(r'\b(oracle|sql server|mysql|postgresql|mongodb|mariadb|db2|sybase)\b', title):
                    squad = "DBA"
                elif re.search(r'\b(weblogic|tomcat|apache|nginx|java|iis|jboss|php|nodejs)\b', title):
                    squad = "Middleware"
                elif re.search(r'\b(ssh|ssl|tls|cipher|certificate|openssh|ssl/tls)\b', title):
                    squad = "Segurança / Crypto"
                elif re.search(r'\b(windows update|kb[0-9]{6,}|kernel|centos|red hat|ubuntu|debian|suse)\b', title):
                    squad = "Patch Manager"
                elif re.search(r'\b(custom|application|code|script)\b', title):
                    squad = "Desenvolvimento"
                    
                row['squad'] = squad
                result.append(row)
                
        def get_sev_order(sev):
            if sev == '5': return 1
            if sev == '4': return 2
            if sev == '3': return 3
            return 4
            
        squad_param = request.args.get("squad")
        if squad_param and squad_param != 'Todas':
            result = [r for r in result if r['squad'] == squad_param]

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
        import re
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        client_param = request.args.get("client")
        user_restriction = getattr(current_user, 'client_restriction', 'none')
        if user_restriction and user_restriction != 'none':
            client_param = user_restriction
            
        where_clause = ""
        params = []
        if client_param and client_param != 'Todos':
            where_clause = " WHERE client = ?"
            params.append(client_param)
            
        cmdb_rows = cursor.execute(f"SELECT hostname, client, db_type, environment, status FROM cmdb_full{where_clause}", params).fetchall()
        cmdb_dict = { (r['hostname'] or '').lower(): r for r in cmdb_rows if r['hostname'] }
        
        query = """
            SELECT d.asset_name, v.severity, v.title
            FROM qualys_detections d
            JOIN qualys_vulnerabilities v ON d.qid = v.qid
        """
        qualys_rows = cursor.execute(query).fetchall()
        conn.close()
        
        hosts_vuln = set()
        sev_counts = {}
        squad_counts = {}
        host_vuln_counts = {}
        
        for q in qualys_rows:
            host_lower = (q['asset_name'] or '').lower()
            if host_lower in cmdb_dict:
                title = str(q['title'] or '').lower()
                squad = "SO / Infra"
                if re.search(r'\b(oracle|sql server|mysql|postgresql|mongodb|mariadb|db2|sybase)\b', title):
                    squad = "DBA"
                elif re.search(r'\b(weblogic|tomcat|apache|nginx|java|iis|jboss|php|nodejs)\b', title):
                    squad = "Middleware"
                elif re.search(r'\b(ssh|ssl|tls|cipher|certificate|openssh|ssl/tls)\b', title):
                    squad = "Segurança / Crypto"
                elif re.search(r'\b(windows update|kb[0-9]{6,}|kernel|centos|red hat|ubuntu|debian|suse)\b', title):
                    squad = "Patch Manager"
                elif re.search(r'\b(custom|application|code|script)\b', title):
                    squad = "Desenvolvimento"
                    
                squad_param = request.args.get("squad")
                if squad_param and squad_param != 'Todas' and squad != squad_param:
                    continue

                hosts_vuln.add(host_lower)
                sev = str(q['severity'])
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
                squad_counts[squad] = squad_counts.get(squad, 0) + 1
                
                if sev in ('4', '5'):
                    if host_lower not in host_vuln_counts:
                        host_vuln_counts[host_lower] = {
                            'asset_name': q['asset_name'], 
                            'db_type': cmdb_dict[host_lower]['db_type'],
                            'environment': cmdb_dict[host_lower]['environment'],
                            'squad': squad,
                            'count': 0
                        }
                    host_vuln_counts[host_lower]['count'] += 1
                    
        squad_breakdown = [{'squad': k, 'count': v} for k, v in squad_counts.items()]
        squad_breakdown.sort(key=lambda x: x['count'], reverse=True)
        sev_breakdown = [{'severity': k, 'count': v} for k, v in sev_counts.items()]
        sev_breakdown.sort(key=lambda x: x['severity'], reverse=True)
        
        top_hosts = list(host_vuln_counts.values())
        top_hosts.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify({
            "total_db_hosts_vulnerable": len(hosts_vuln),
            "severity_breakdown": sev_breakdown,
            "squad_breakdown": squad_breakdown,
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
@admin_required
def api_update_gmud(gmud_id):
    try:
        data = request.json
        success = update_gmud(gmud_id, data)
        if success:
            return jsonify({"message": "GMUD atualizada com sucesso!"})
        return jsonify({"message": "GMUD não encontrada"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/api/gmuds/<int:gmud_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_gmud(gmud_id):
    success = delete_gmud(gmud_id)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Falha ao excluir GMUD"})


@app.route("/api/users", methods=["GET"])
@login_required
@admin_required
def api_users_list():
    users = get_all_users()
    return jsonify(users)


@app.route("/api/users", methods=["POST"])
@login_required
@admin_required
def api_create_user():
    data = request.json
    try:
        user_id = create_user(
            username=data.get('username'),
            password=data.get('password'),
            display_name=data.get('display_name'),
            role=data.get('role', 'viewer'),
            client_restriction=data.get('client_restriction', 'none')
        )
        return jsonify({"status": "success", "user_id": user_id})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Usuário já existe"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/users/<int:user_id>/status", methods=["PUT"])
@login_required
@admin_required
def api_update_user_status(user_id):
    data = request.json
    try:
        update_user_status(user_id, data.get('is_active'))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/users/<int:user_id>/reset-password", methods=["PUT"])
@login_required
@admin_required
def api_reset_password(user_id):
    data = request.json
    try:
        reset_user_password(user_id, data.get('new_password'))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



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
    client_param = request.args.get('client')
    user_restriction = getattr(current_user, 'client_restriction', 'none')
    if user_restriction and user_restriction != 'none':
        client_param = user_restriction

    data = get_gmuds(
        client=client_param,
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
    client_param = request.args.get("client")
    user_restriction = getattr(current_user, 'client_restriction', 'none')
    if user_restriction and user_restriction != 'none':
        client_param = user_restriction

    data = get_cmdb_full(
        client=client_param,
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
