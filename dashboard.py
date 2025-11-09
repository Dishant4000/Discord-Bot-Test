# dashboard.py
# Minimal Flask dashboard for your Discord shop bot.
# Usage:
# 1) put a "DASHBOARD_TOKEN" field under BOT_DATA in config.json
# 2) pip install flask
# 3) python dashboard.py
# 4) open http://127.0.0.1:5000 and login with the token

import os
import json
import platform
import psutil
import time
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import jsonify, render_template_string
from manage.database_manager import load_logs, load_customers, save_customers

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, send_from_directory
)

# ---------- CONFIG ----------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "dashboard_templates")


# Filemanager path
FILEMANAGER_BASE = os.path.abspath(os.path.join(os.getcwd(), "softwares", "filemanager"))

# Load config.json
if not os.path.exists(CONFIG_PATH):
    raise RuntimeError("config.json not found — create it as in your bot project.")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

# secret token for dashboard login (put in config.json under BOT_DATA.DASHBOARD_TOKEN)
DASHBOARD_TOKEN = cfg.get("BOT_DATA", {}).get("DASHBOARD_TOKEN", None)
if not DASHBOARD_TOKEN:
    print("⚠️ Warning: BOT_DATA.DASHBOARD_TOKEN not set in config.json. Create one and restart dashboard.")
# Paths for JSON DB files (match your bot)
ORDERS_DB_PATH = os.path.join(PROJECT_ROOT, "data", "database", "orders_database.json")
PRODUCTS_DB_PATH = os.path.join(PROJECT_ROOT, "data", "database", "products_database.json")
RECEIVE_LTC_DB_PATH = os.path.join(PROJECT_ROOT, "data", "database", "receive_ltc_database.json")

# Ensure data folder exists
os.makedirs(os.path.dirname(ORDERS_DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(PRODUCTS_DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(RECEIVE_LTC_DB_PATH), exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = cfg.get("BOT", {}).get("TOKEN", "replace-with-random-secret")[:32]

# ------------- helpers -------------
def now_india_str():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d - %I:%M:%S%p")

def load_json(path, default=None):
    if not os.path.exists(path):
        if default is None:
            default = {}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

# ------------- routes -------------

@app.route("/", methods=["GET"])
def root():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None
    if request.method == "POST":
        token = request.form.get("token", "").strip()
        if DASHBOARD_TOKEN and token == DASHBOARD_TOKEN:
            session["logged_in"] = True
            flash("✅ Logged in to dashboard", "success")
            nxt = request.args.get("next") or url_for("dashboard")
            return redirect(nxt)
        else:
            msg = "Invalid token."
    return render_template("login.html", message=msg, now=now_india_str())

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    flash("Logged out", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    orders_db = load_json(ORDERS_DB_PATH, {"pending_payment_orders": {}, "pending_delivery_orders": {}, "delivered_orders": {}})
    products_db = load_json(PRODUCTS_DB_PATH, {"products": {}})
    payments_db = load_json(RECEIVE_LTC_DB_PATH, {"payments": {}})

    stats = {
        "total_products": len(products_db.get("products", {})),
        "pending_payments": len(orders_db.get("pending_payment_orders", {})),
        "pending_delivery": len(orders_db.get("pending_delivery_orders", {})),
        "delivered": len(orders_db.get("delivered_orders", {})),
        "payments": len(payments_db.get("payments", {}))
    }

    # show recent orders (mix)
    recent = []
    for bucket in ("pending_delivery_orders", "pending_payment_orders", "delivered_orders"):
        for oid, o in (orders_db.get(bucket) or {}).items():
            recent.append({**o, "bucket": bucket})
    recent = sorted(recent, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]

    return render_template("dashboard.html", stats=stats, recent=recent, now=now_india_str())

# ---------------- Orders ----------------
@app.route("/orders")
@login_required
def orders_page():
    orders_db = load_json(ORDERS_DB_PATH, {"pending_payment_orders": {}, "pending_delivery_orders": {}, "delivered_orders": {}})

    return render_template("orders.html",
                           pending_payments=orders_db.get("pending_payment_orders", {}),
                           pending_delivery=orders_db.get("pending_delivery_orders", {}),
                           delivered=orders_db.get("delivered_orders", {}),
                           now=now_india_str())

@app.route("/orders/mark_delivered", methods=["POST"])
@login_required
def mark_delivered():
    data = load_json(ORDERS_DB_PATH, {"pending_payment_orders": {}, "pending_delivery_orders": {}, "delivered_orders": {}})
    order_id = request.form.get("order_id")
    if not order_id:
        abort(400)

    # Try find in pending_delivery first, then pending_payment
    if order_id in data.get("pending_delivery_orders", {}):
        order = data["pending_delivery_orders"].pop(order_id)
    elif order_id in data.get("pending_payment_orders", {}):
        order = data["pending_payment_orders"].pop(order_id)
    else:
        return redirect(url_for("orders_page"))

    order["status"] = "Delivered"
    order["delivered_at"] = now_india_str()

    data.setdefault("delivered_orders", {})[order_id] = order
    save_json(ORDERS_DB_PATH, data)
    flash(f"Order {order_id} moved to Delivered", "success")
    return redirect(url_for("orders_page"))

@app.route("/orders/move_to_delivery", methods=["POST"])
@login_required
def move_to_delivery():
    data = load_json(ORDERS_DB_PATH, {"pending_payment_orders": {}, "pending_delivery_orders": {}, "delivered_orders": {}})
    order_id = request.form.get("order_id")
    if not order_id:
        abort(400)
    if order_id in data.get("pending_payment_orders", {}):
        order = data["pending_payment_orders"].pop(order_id)
        order["status"] = "Completed"
        order["timestamp"] = now_india_str()
        data.setdefault("pending_delivery_orders", {})[order_id] = order
        save_json(ORDERS_DB_PATH, data)
        flash(f"Order {order_id} moved to Pending Delivery", "success")
    return redirect(url_for("orders_page"))

@app.route("/orders/delete", methods=["POST"])
@login_required
def delete_order():
    data = load_json(ORDERS_DB_PATH, {"pending_payment_orders": {}, "pending_delivery_orders": {}, "delivered_orders": {}})
    order_id = request.form.get("order_id")
    if not order_id:
        abort(400)
    removed = False
    for bucket in ("pending_payment_orders", "pending_delivery_orders", "delivered_orders"):
        if order_id in data.get(bucket, {}):
            data[bucket].pop(order_id, None)
            removed = True
    if removed:
        save_json(ORDERS_DB_PATH, data)
        flash(f"Order {order_id} removed", "info")
    return redirect(url_for("orders_page"))

# ---------------- Products ----------------
@app.route("/products")
@login_required
def products_page():
    products_db = load_json(PRODUCTS_DB_PATH, {"products": {}})
    return render_template("products.html", products=products_db.get("products", {}), now=now_india_str())

@app.route("/products/add", methods=["POST"])
@login_required
def products_add():
    name = request.form.get("name", "").strip()
    price = request.form.get("price", "").strip()
    stock = request.form.get("stock", "0").strip()
    description = request.form.get("description", "").strip()

    if not name or not price:
        flash("Name and price are required", "danger")
        return redirect(url_for("products_page"))

    products_db = load_json(PRODUCTS_DB_PATH, {"products": {}})
    products_db.setdefault("products", {})[name] = {
        "price": float(price),
        "description": description or "No Description",
        "stock": int(stock or 0),
        "added_at": now_india_str()
    }
    save_json(PRODUCTS_DB_PATH, products_db)
    flash(f"Product {name} added", "success")
    return redirect(url_for("products_page"))

@app.route("/products/delete", methods=["POST"])
@login_required
def products_delete():
    name = request.form.get("name")
    if not name:
        abort(400)
    products_db = load_json(PRODUCTS_DB_PATH, {"products": {}})
    if name in products_db.get("products", {}):
        products_db["products"].pop(name)
        save_json(PRODUCTS_DB_PATH, products_db)
        flash(f"Product {name} deleted", "info")
    return redirect(url_for("products_page"))

@app.route("/products/edit", methods=["POST"])
@login_required
def products_edit():
    name = request.form.get("name")
    price = request.form.get("price")
    stock = request.form.get("stock")
    description = request.form.get("description", "")
    if not name:
        abort(400)
    products_db = load_json(PRODUCTS_DB_PATH, {"products": {}})
    prod = products_db.get("products", {}).get(name)
    if not prod:
        flash("Product not found", "danger")
        return redirect(url_for("products_page"))

    if price:
        prod["price"] = float(price)
    if stock is not None:
        prod["stock"] = int(stock or 0)
    if description:
        prod["description"] = description
    products_db["products"][name] = prod
    save_json(PRODUCTS_DB_PATH, products_db)
    flash(f"Product {name} updated", "success")
    return redirect(url_for("products_page"))

# ---------------- Payments ----------------
@app.route("/payments")
@login_required
def payments_page():
    payments_db = load_json(RECEIVE_LTC_DB_PATH, {"payments": {}})
    return render_template("payments.html", payments=payments_db.get("payments", {}), now=now_india_str())

# -------------- static/simple favicon --------------
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(PROJECT_ROOT, "dashboard_templates"), "favicon.ico")

@app.route("/serverinfo")
@login_required
def serverinfo_page():
    """Display server info from server_database.json"""
    import json, os
    db_path = "data/database/server_database.json"

    if not os.path.exists(db_path):
        return render_template("serverinfo.html", serverinfo=None)

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    info = data.get("SERVERINFO", {})
    servers = info.get("servers", {})
    total_servers = info.get("total_servers", 0)
    total_members = info.get("total_members", 0)
    updated = info.get("last_updated", "Never")

    return render_template(
        "serverinfo.html",
        info=info,
        servers=servers,
        total_servers=total_servers,
        total_members=total_members,
        updated=updated,
        now=now_india_str()
    )

# ============================
# 📂 File Manager Main Page
# ============================
@app.route("/filemanager", defaults={"subpath": ""})
@app.route("/filemanager/<path:subpath>")
@login_required
def filemanager(subpath):
    full_path = os.path.join(FILEMANAGER_BASE, subpath)
    os.makedirs(full_path, exist_ok=True)

    items = []
    for name in os.listdir(full_path):
        fpath = os.path.join(full_path, name)
        stat = os.stat(fpath)
        items.append({
            "name": name,
            "is_dir": os.path.isdir(fpath),
            "size": f"{os.path.getsize(fpath)} bytes" if os.path.isfile(fpath) else "",
            "modified": f"{int(stat.st_mtime)}",
        })

    parent = os.path.dirname(subpath) if subpath else None
    return render_template("filemanager.html", items=items, current=subpath, parent=parent, now=now_india_str())

# ============================
# ➕ Create File/Folder
# ============================
@app.route("/filemanager/create", methods=["POST"])
@login_required
def filemanager_create():
    subpath = request.form.get("current", "")
    name = request.form.get("name")
    type_ = request.form.get("type")

    target_dir = os.path.join(FILEMANAGER_BASE, subpath)
    os.makedirs(target_dir, exist_ok=True)

    new_path = os.path.join(target_dir, name)
    try:
        if type_ == "folder":
            os.makedirs(new_path, exist_ok=True)
            flash(f"📁 Folder '{name}' created!")
        else:
            with open(new_path, "w", encoding="utf-8") as f:
                f.write("")
            flash(f"📝 File '{name}' created!")
    except Exception as e:
        flash(f"❌ {e}")

    return redirect(url_for("filemanager", subpath=subpath))

# ============================
# 🗑️ Delete File/Folder
# ============================
@app.route("/filemanager/delete", methods=["POST"])
@login_required
def filemanager_delete():
    subpath = request.form.get("current", "")
    name = request.form.get("name")

    target = os.path.join(FILEMANAGER_BASE, subpath, name)
    try:
        if os.path.isdir(target):
            import shutil; shutil.rmtree(target)
        else:
            os.remove(target)
        flash(f"🗑️ Deleted '{name}'")
    except Exception as e:
        flash(f"❌ {e}")

    return redirect(url_for("filemanager", subpath=subpath))

# ============================
# ✏️ Edit File
# ============================
@app.route("/filemanager/edit/<path:subpath>", methods=["GET", "POST"])
@login_required
def filemanager_edit(subpath):
    import os
    from flask import request, redirect, url_for, flash, render_template

    allowed_extensions = {".txt", ".json", ".py", ".yml", ".yaml", ".html", ".css", ".js", ".md"}
    base_path = os.path.abspath(os.path.join(os.getcwd(), "softwares", "filemanager"))
    file_path = os.path.abspath(os.path.join(base_path, subpath))

    # Prevent directory traversal
    if not file_path.startswith(base_path):
        flash("❌ Access denied.")
        return redirect(url_for("filemanager"))

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in allowed_extensions:
        flash(f"❌ Editing not allowed for '{ext}' files.")
        return redirect(url_for("filemanager", subpath=os.path.dirname(subpath)))

    # Handle save
    if request.method == "POST":
        content = request.form.get("content", "")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            flash(f"💾 Saved changes to '{os.path.basename(file_path)}'")
        except Exception as e:
            flash(f"❌ Failed to save: {e}")
        return redirect(url_for("filemanager", subpath=os.path.dirname(subpath)))

    # Handle open
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        flash(f"⚠️ Could not read file: {e}")
        content = ""

    return render_template("filemanager_edit.html", subpath=subpath, content=content, extension=ext, now=now_india_str())

@app.route("/logs")
def logs_page():
    logs = load_logs()
    entries = logs.get("global", [])
    return render_template("logs.html", logs=entries, page_title="Logs", now=now_india_str())

@app.route("/customers")
def customers_page():
    customers = load_customers()
    return render_template("customers.html", customers=customers, now=datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"))


@app.route("/customers/add", methods=["POST"])
def add_customer():
    name = request.form.get("name")
    user_id = request.form.get("user_id")
    email = request.form.get("email")

    if not name or not user_id:
        flash("⚠️ Please enter all required fields!", "error")
        return redirect(url_for("customers_page"))

    data = load_customers()
    data[user_id] = {
        "name": name,
        "email": email or "N/A",
        "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_customers(data)
    flash(f"✅ Added new customer: {name}", "success")
    return redirect(url_for("customers_page"))


@app.route("/customers/delete", methods=["POST"])
def delete_customer():
    user_id = request.form.get("user_id")
    data = load_customers()

    if user_id in data:
        del data[user_id]
        save_customers(data)
        flash("🗑️ Customer deleted successfully!", "success")
    else:
        flash("⚠️ Customer not found!", "error")

    return redirect(url_for("customers_page"))

# -------------- run --------------
if __name__ == "__main__":
    print("Starting dashboard at http://127.0.0.1:5000 (templates in dashboard_templates/)")
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host="0.0.0.0", port=port)

