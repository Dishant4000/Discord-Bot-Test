# ============================================================
# 📦 database_manager.py
# Simple async-safe JSON database handler for your Discord bot
# ============================================================

import json
import os
import asyncio
from datetime import datetime, timezone,timedelta

# ===========================
# 🔧 Path setup
# ===========================

# Tickets Path
# ---------------------------
TICKETS_DATA_DIR = os.path.join("data", "database")
TICKETS_DB_PATH = os.path.join(TICKETS_DATA_DIR, "ticket_database.json")
# Lock to prevent concurrent writes
_db_lock = asyncio.Lock()
# ---------------------------

# Orders Path
# ---------------------------
ORDERS_DB_PATH = "data/database/orders_database.json"
os.makedirs(os.path.dirname(ORDERS_DB_PATH), exist_ok=True)
# ---------------------------

# Receive ltc Path
# ---------------------------
RECEIVE_LTC_DATA_DIR = os.path.join("data", "database")
RECEIVE_LTC_DB_PATH = os.path.join(RECEIVE_LTC_DATA_DIR, "receive_ltc_database.json")
# async lock for safe writes
_receive_lock = asyncio.Lock()
# ---------------------------

# Products Path
# ---------------------------
PRODUCTS_DATA_DIR = os.path.join("data", "database")
PRODUCTS_DB_PATH = os.path.join(PRODUCTS_DATA_DIR, "products_database.json")
# Lock for async-safe writes
_products_lock = asyncio.Lock()
# ---------------------------

# Discord Logs Path
# ---------------------------
LOG_FILE = "data/database/logs_database.json"
# ---------------------------

# Customers Path
# ---------------------------
CUSTOMER_DB_PATH = "data/database/customers_database.json"
# ---------------------------


# ===========================
# 🎟️ Tickets Management
# ===========================
def init_tickets_db():
    """Create database file/folders if not exists."""
    os.makedirs(TICKETS_DATA_DIR, exist_ok=True)
    if not os.path.exists(TICKETS_DB_PATH):
        with open(TICKETS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump({"tickets": {}, "users": {}, "stats": {}}, f, indent=4)
        print("🗃️ [DATABASE] Created new database file.")
    else:
        # print("✅ [DATABASE] Database ready.")
        ""


# 📥 Load Tickets database
def load_tickets_db():
    """Load database into memory."""
    with open(TICKETS_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# 💾 Save tickets database
async def save_tickets_db(data):
    """Safely save data back to database.json."""
    async with _db_lock:
        with open(TICKETS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


async def create_ticket(user_id, channel_id):
    """Create a new ticket entry in the database."""
    db = load_tickets_db()
    ticket_id = str(int(datetime.now(timezone.utc).timestamp()))

    db["tickets"][ticket_id] = {
        "user_id": user_id,
        "channel_id": channel_id,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "closed_at": None
    }

    await save_tickets_db(db)
    return ticket_id


async def close_ticket(ticket_id):
    """Mark a ticket as closed."""
    db = load_tickets_db()
    if ticket_id in db["tickets"]:
        db["tickets"][ticket_id]["status"] = "closed"
        db["tickets"][ticket_id]["closed_at"] = datetime.now(timezone.utc).isoformat()
        await save_tickets_db(db)
        return True
    return False


# 🧹 Utility Functions
def get_user_tickets(user_id: int):
    """Return all tickets belonging to a specific user."""
    db = load_tickets_db()
    return {
        t_id: info
        for t_id, info in db["tickets"].items()
        if info["user_id"] == user_id
    }

def get_all_tickets():
    """Return all tickets."""
    db = load_tickets_db()
    return db.get("tickets", {})


# ===========================
# 📦 Orders Management
# ===========================
def load_orders_db():
    """Load the orders database or create if missing."""
    if not os.path.exists(ORDERS_DB_PATH):
        db = {"pending_payment_orders": {}, "pending_delivery_orders": {}}
        save_orders_db(db)
    with open(ORDERS_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders_db(data):
    """Save orders database."""
    with open(ORDERS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ===========================
# 📦 Receives LTC (Litecoin)
# ===========================
def init_receive_ltc_databases():
    """Create the receive_ltc database if not exists."""
    os.makedirs(RECEIVE_LTC_DATA_DIR, exist_ok=True)
    if not os.path.exists(RECEIVE_LTC_DB_PATH):
        with open(RECEIVE_LTC_DB_PATH, "w", encoding="utf-8") as f:
            json.dump({"payments": {}}, f, indent=4)
        print("🪙 [DATABASE] Created receive_ltc_database.json file.")
    else:
        # print("✅ [DATABASE] receive_ltc_database.json ready.")
        ""


# 📥 Load LTC database
def load_receive_ltc_db():
    """Load the receive LTC database."""
    if not os.path.exists(RECEIVE_LTC_DB_PATH):
        init_receive_ltc_databases()
    with open(RECEIVE_LTC_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# 💾 Save LTC database
async def save_receive_ltc_db(data):
    """Async-safe save for LTC database."""
    async with _receive_lock:
        with open(RECEIVE_LTC_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


# ➕ Add new LTC payment
async def add_receive_ltc(user_id, purchase_id, payment_id, amount_usd, ltc_amount, address, status):
    """Add a new LTC payment entry."""
    db = load_receive_ltc_db()

    db["payments"][payment_id] = {
        "user_id": user_id,
        "purchase_id": purchase_id,
        "payment_id": payment_id,
        "amount_usd": amount_usd,
        "ltc_amount": ltc_amount,
        "address": address,
        "status": status,
        "created_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d - %I:%M:%S%p"),
        "updated_at": None
    }

    await save_receive_ltc_db(db)
    print(f"💾 [DATABASE] Saved LTC payment {payment_id} for user {user_id}")


# 🔍 Get specific payment
def get_receive_ltc(payment_id: str):
    """Return a payment entry by ID."""
    db = load_receive_ltc_db()
    return db["payments"].get(payment_id)


# 🔁 Update payment status
def update_receive_ltc_status(payment_id: str, new_status: str):
    """Update the status of a payment entry."""
    db = load_receive_ltc_db()
    if payment_id in db["payments"]:
        db["payments"][payment_id]["status"] = new_status
        db["payments"][payment_id]["updated_at"] = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d - %I:%M:%S%p")
        with open(RECEIVE_LTC_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
        print(f"🔄 [DATABASE] Payment {payment_id} updated to '{new_status}'")
        return True
    else:
        print(f"⚠️ [DATABASE] Payment ID {payment_id} not found.")
        return False


# ===========================
# 🛍️ Products
# ===========================
def init_products_db():
    """Initialize the products database file."""
    os.makedirs(PRODUCTS_DATA_DIR, exist_ok=True)
    if not os.path.exists(PRODUCTS_DB_PATH):
        with open(PRODUCTS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump({"products": {}}, f, indent=4)
        print("🗃️ [DATABASE] Created products_database.json")
    else:
        # print("✅ [DATABASE] Products database ready.")
        pass

def load_products_db():
    """Load the products database into memory."""
    if not os.path.exists(PRODUCTS_DB_PATH):
        init_products_db()
    with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"products": {}}

async def save_products_db(data):
    """Safely save data to products_database.json"""
    async with _products_lock:
        with open(PRODUCTS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

# CRUD FUNCTIONS (Create, Read, Update, Delete)
async def add_product(name, price, description, stock=0):
    """Add a new product to the shop."""
    db = load_products_db()
    db["products"][name] = {
        "price": float(price),
        "description": description,
        "stock": int(stock),
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    await save_products_db(db)

async def remove_product(name):
    """Remove a product by name."""
    db = load_products_db()
    if name in db["products"]:
        del db["products"][name]
        await save_products_db(db)
        return True
    return False

def get_product(name):
    """Get a specific product by name."""
    db = load_products_db()
    return db["products"].get(name)

def get_all_products():
    """Return all available products."""
    db = load_products_db()
    return db.get("products", {})


# ===========================
# 📜 Discord Logs
# ===========================
def ensure_log_file():
    if not os.path.exists(os.path.dirname(LOG_FILE)):
        os.makedirs(os.path.dirname(LOG_FILE))
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump({"global": []}, f, indent=2)

def load_logs():
    ensure_log_file()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_logs(data):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_normal_log(message: str):
    data = load_logs()
    entry = {"log_type": "normal", "message": message}
    data["global"].append(entry)
    save_logs(data)

def add_embed_log(title, description = None, color="#2b2f7a", fields=None, footer_text=None, footer_icon=None):
    data = load_logs()
    entry = {
        "log_type": "embed",
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fields": fields or [],
        "footer_text": footer_text,
        "footer_icon": footer_icon
    }
    data["global"].append(entry)
    save_logs(data)


# ===========================
# 👥 Customers
# ===========================
# 🧠 Generic Loader
def load_customers_database(path):
    """Load JSON data from file safely"""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}

    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


# 🧾 Generic Saver
def save_database(path, data):
    """Save JSON data safely"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# 👥 Customers specific wrappers
def load_customers():
    return load_customers_database(CUSTOMER_DB_PATH)


def save_customers(data):
    save_database(CUSTOMER_DB_PATH, data)