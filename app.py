"""
ORAEX PSU Manager — Flask Application
"""
from flask import Flask, render_template, jsonify, request
from database import (
    init_db, get_dashboard_stats, get_servers, get_gmuds,
    get_cmdb_databases, get_filter_options, get_planning_data,
    get_cmdb_full, get_cmdb_full_stats, get_cmdb_full_filters,
    get_pagonxt_databases
)
from import_excel import run_import, run_cmdb_full_import
from export_excel import write_gmud_to_excel
from config import SECRET_KEY, DEBUG, HOST, PORT
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ══════════════════════════════════════════════════════════
#  PÁGINAS (Frontend Routes)
# ══════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@app.route("/inventory")
def inventory():
    return render_template("inventory.html", active="inventory")


@app.route("/cmdb-full")
def cmdb_full():
    return render_template("cmdb_full.html", active="cmdb_full")


@app.route("/gmud")
def gmud():
    return render_template("gmud.html", active="gmud")


@app.route("/gmud/create")
def gmud_create():
    """Página de formulário para criar nova GMUD."""
    return render_template("gmud_create.html", active="gmud")


@app.route("/reports")
def reports():
    return render_template("reports.html", active="reports")


# ══════════════════════════════════════════════════════════
#  API ENDPOINTS (Backend)
# ══════════════════════════════════════════════════════════

@app.route("/api/dashboard")
def api_dashboard():
    stats = get_dashboard_stats()
    return jsonify(stats)


@app.route("/api/servers")
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


@app.route("/api/cmdb-full/stats")
def api_cmdb_full_stats():
    stats = get_cmdb_full_stats(client=request.args.get("client"))
    return jsonify(stats)


@app.route("/api/cmdb-full/filters")
def api_cmdb_full_filters():
    options = get_cmdb_full_filters()
    return jsonify(options)


@app.route("/api/pagonxt")
def api_pagonxt():
    data = get_pagonxt_databases(
        search=request.args.get("search"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 50)),
    )
    return jsonify(data)


@app.route("/api/planning")
def api_planning():
    data = get_planning_data()
    return jsonify(data)


@app.route("/api/filters")
def api_filters():
    options = get_filter_options()
    return jsonify(options)


@app.route("/api/import", methods=["POST"])
def api_import():
    try:
        result = run_import()
        if result:
            return jsonify({"status": "success", "message": "Import completed successfully!"})
        else:
            return jsonify({"status": "error", "message": "Import failed. Check the Excel file path."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/import-cmdb-full", methods=["POST"])
def api_import_cmdb_full():
    try:
        result = run_cmdb_full_import()
        if result:
            return jsonify({"status": "success", "message": "CMDB Full import completed successfully!"})
        else:
            return jsonify({"status": "error", "message": "Import failed. Check the CMDB Full file path."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/gmud/generate-title", methods=["POST"])
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
#  INICIALIZAÇÃO (Startup)
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    print("\n🚀 ORAEX PSU Manager")
    print(f"🌐 Open: http://{HOST}:{PORT}")
    print(f"📊 Dashboard: http://{HOST}:{PORT}/")
    print(f"🖥️  Inventory: http://{HOST}:{PORT}/inventory")
    print(f"🗄️  CMDB Full: http://{HOST}:{PORT}/cmdb-full")
    print(f"📋 GMUDs: http://{HOST}:{PORT}/gmud")
    print(f"📈 Reports: http://{HOST}:{PORT}/reports\n")
    app.run(host=HOST, port=PORT, debug=DEBUG)
