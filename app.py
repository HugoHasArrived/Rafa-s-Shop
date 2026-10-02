import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

# Needed when deployed behind a reverse proxy.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

DATABASE = os.getenv("DATABASE_PATH", "store.db")
STAFF_PASSWORD = os.getenv("STAFF_PASSWORD", "change-me-now")

STORE_NAME = os.getenv("STORE_NAME", "Luna Steps PH")
STORE_ADDRESS = os.getenv(
    "STORE_ADDRESS",
    "Philippines"
)
STORE_PHONE = os.getenv(
    "STORE_PHONE",
    "+63 900 000 0000"
)
STORE_EMAIL = os.getenv(
    "STORE_EMAIL",
    "hello@example.com"
)


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            sizes TEXT DEFAULT '',
            color TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            country TEXT DEFAULT 'Unknown',
            region TEXT DEFAULT 'Unknown',
            device TEXT DEFAULT 'Unknown',
            browser TEXT DEFAULT 'Unknown',
            user_agent TEXT DEFAULT '',
            visited_at TEXT NOT NULL
        );
    """)

    # Add sample products only on first run.
    count = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count == 0:
        products = [
            (
                "Purple Cloud Slides",
                "Soft everyday slides with a cushioned sole.",
                399,
                25,
                "36,37,38,39,40,41,42",
                "Purple",
                "https://images.unsplash.com/photo-1603487742131-4160ec999306?auto=format&fit=crop&w=900&q=80"
            ),
            (
                "Lavender Comfort",
                "Lightweight slippers designed for daily comfort.",
                349,
                18,
                "36,37,38,39,40",
                "Lavender",
                "https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?auto=format&fit=crop&w=900&q=80"
            ),
            (
                "Midnight Purple",
                "Simple, durable house and outdoor slippers.",
                449,
                12,
                "38,39,40,41,42,43",
                "Dark Purple",
                "https://images.unsplash.com/photo-1562273138-f46be4ebdf33?auto=format&fit=crop&w=900&q=80"
            )
        ]

        conn.executemany("""
            INSERT INTO products
            (name, description, price, stock, sizes, color, image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (*product, datetime.now(timezone.utc).isoformat())
            for product in products
        ])

    conn.commit()
    conn.close()


def hash_ip(ip):
    """
    Store a privacy-preserving fingerprint rather than exposing
    the raw IP address in the database.
    """
    salt = os.getenv("IP_HASH_SALT", "change-this-ip-salt")
    return hashlib.sha256(
        f"{salt}:{ip}".encode("utf-8")
    ).hexdigest()[:24]


def get_client_ip():
    """
    Gets the client IP when deployed behind a trusted reverse proxy.
    ProxyFix handles X-Forwarded-For.
    """
    return request.remote_addr or "unknown"


def detect_device(user_agent):
    ua = user_agent.lower()

    if "ipad" in ua or "tablet" in ua:
        return "Tablet"
    if "iphone" in ua or "android" in ua:
        return "Mobile"
    return "Desktop"


def detect_browser(user_agent):
    ua = user_agent.lower()

    if "edg/" in ua:
        return "Edge"
    if "chrome/" in ua and "edg/" not in ua:
        return "Chrome"
    if "firefox/" in ua:
        return "Firefox"
    if "safari/" in ua and "chrome/" not in ua:
        return "Safari"
    if "opera" in ua or "opr/" in ua:
        return "Opera"

    return "Other"


def record_visitor():
    """
    Records coarse analytics only.

    No GPS or exact physical location is collected.
    Country/region are intentionally left as Unknown unless
    you connect a privacy-compliant coarse geolocation service.
    """
    ua = request.headers.get("User-Agent", "")
    raw_ip = get_client_ip()

    conn = get_db()

    conn.execute("""
        INSERT INTO visitors
        (ip_address, country, region, device, browser, user_agent, visited_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        hash_ip(raw_ip),
        "Unknown",
        "Unknown",
        detect_device(ua),
        detect_browser(ua),
        ua[:500],
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()


@app.context_processor
def inject_store():
    return {
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "store_phone": STORE_PHONE,
        "store_email": STORE_EMAIL
    }


@app.route("/")
def index():
    record_visitor()

    conn = get_db()
    products = conn.execute("""
        SELECT *
        FROM products
        WHERE active = 1
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return render_template(
        "index.html",
        products=products
    )


@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        password = request.form.get("password", "")

        if secrets.compare_digest(password, STAFF_PASSWORD):
            session.clear()
            session["staff"] = True
            return redirect(url_for("dashboard"))

        flash("Incorrect staff password.", "error")

    return render_template("login.html")


@app.route("/staff/logout")
def staff_logout():
    session.clear()
    return redirect(url_for("index"))


def staff_required():
    if not session.get("staff"):
        abort(403)


@app.route("/staff")
def dashboard():
    staff_required()

    conn = get_db()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    visitors = conn.execute("""
        SELECT
            id,
            ip_address,
            country,
            region,
            device,
            browser,
            visited_at
        FROM visitors
        ORDER BY id DESC
        LIMIT 200
    """).fetchall()

    total_visitors = conn.execute(
        "SELECT COUNT(*) FROM visitors"
    ).fetchone()[0]

    total_stock = conn.execute(
        "SELECT COALESCE(SUM(stock), 0) FROM products"
    ).fetchone()[0]

    product_count = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        products=products,
        visitors=visitors,
        total_visitors=total_visitors,
        total_stock=total_stock,
        product_count=product_count
    )


@app.route("/staff/product/new", methods=["POST"])
def create_product():
    staff_required()

    name = request.form.get("name", "").strip()

    if not name:
        flash("Product name is required.", "error")
        return redirect(url_for("dashboard"))

    try:
        price = float(request.form.get("price", 0))
        stock = int(request.form.get("stock", 0))
    except ValueError:
        flash("Price and stock must be valid numbers.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()

    conn.execute("""
        INSERT INTO products
        (name, description, price, stock, sizes, color, image_url, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        name,
        request.form.get("description", "").strip(),
        max(price, 0),
        max(stock, 0),
        request.form.get("sizes", "").strip(),
        request.form.get("color", "").strip(),
        request.form.get("image_url", "").strip(),
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()

    flash("Product added.", "success")
    return redirect(url_for("dashboard"))


@app.route("/staff/product/<int:product_id>/update", methods=["POST"])
def update_product(product_id):
    staff_required()

    name = request.form.get("name", "").strip()

    if not name:
        flash("Product name is required.", "error")
        return redirect(url_for("dashboard"))

    try:
        price = max(float(request.form.get("price", 0)), 0)
        stock = max(int(request.form.get("stock", 0)), 0)
    except ValueError:
        flash("Price and stock must be valid numbers.", "error")
        return redirect(url_for("dashboard"))

    active = 1 if request.form.get("active") == "1" else 0

    conn = get_db()

    exists = conn.execute(
        "SELECT id FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not exists:
        conn.close()
        abort(404)

    conn.execute("""
        UPDATE products
        SET name = ?,
            description = ?,
            price = ?,
            stock = ?,
            sizes = ?,
            color = ?,
            image_url = ?,
            active = ?
        WHERE id = ?
    """, (
        name,
        request.form.get("description", "").strip(),
        price,
        stock,
        request.form.get("sizes", "").strip(),
        request.form.get("color", "").strip(),
        request.form.get("image_url", "").strip(),
        active,
        product_id
    ))

    conn.commit()
    conn.close()

    flash("Product updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/staff/product/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    staff_required()

    conn = get_db()
    conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )
    conn.commit()
    conn.close()

    flash("Product deleted.", "success")
    return redirect(url_for("dashboard"))


@app.errorhandler(403)
def forbidden(error):
    return "Staff access required.", 403


@app.errorhandler(404)
def not_found(error):
    return "Page not found.", 404


if __name__ == "__main__":
    init_db()

    # Debug should be disabled in production.
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1"
    )
