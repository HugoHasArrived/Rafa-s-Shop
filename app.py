import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET")

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

DATABASE = os.getenv("DATABASE_PATH", "store.db")
STAFF_PASSWORD = os.getenv("STAFF_PASSWORD", "CHANGE_THIS_PASSWORD")
IP_HASH_SALT = os.getenv("IP_HASH_SALT", "CHANGE_THIS_IP_SALT")

STORE_NAME = "Rafa's Store"
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
    "hello@rafasstore.com"
)


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()

    connection.executescript("""
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
            visited_at TEXT NOT NULL
        );
    """)

    count = connection.execute(
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
                ""
            ),
            (
                "Lavender Comfort",
                "Lightweight slippers designed for daily comfort.",
                349,
                18,
                "36,37,38,39,40",
                "Lavender",
                ""
            ),
            (
                "Midnight Purple",
                "Simple and durable slippers for everyday use.",
                449,
                12,
                "38,39,40,41,42,43",
                "Dark Purple",
                ""
            )
        ]

        for product in products:
            connection.execute("""
                INSERT INTO products
                (
                    name,
                    description,
                    price,
                    stock,
                    sizes,
                    color,
                    image_url,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                *product,
                datetime.now(timezone.utc).isoformat()
            ))

    connection.commit()
    connection.close()


def get_client_ip():
    return request.remote_addr or "unknown"


def hash_ip(ip):
    return hashlib.sha256(
        f"{IP_HASH_SALT}:{ip}".encode()
    ).hexdigest()[:24]


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

    if "chrome/" in ua:
        return "Chrome"

    if "firefox/" in ua:
        return "Firefox"

    if "safari/" in ua:
        return "Safari"

    if "opera" in ua or "opr/" in ua:
        return "Opera"

    return "Other"


def record_visitor():
    """
    Privacy-friendly analytics.

    We do not request GPS or precise location.
    The IP is hashed before storage.
    """

    user_agent = request.headers.get("User-Agent", "")
    ip = get_client_ip()

    connection = get_db()

    connection.execute("""
        INSERT INTO visitors
        (
            ip_address,
            country,
            region,
            device,
            browser,
            visited_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        hash_ip(ip),
        "Unknown",
        "Unknown",
        detect_device(user_agent),
        detect_browser(user_agent),
        datetime.now(timezone.utc).isoformat()
    ))

    connection.commit()
    connection.close()


@app.context_processor
def store_information():
    return {
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "store_phone": STORE_PHONE,
        "store_email": STORE_EMAIL
    }


@app.route("/")
def index():
    record_visitor()

    connection = get_db()

    products = connection.execute("""
        SELECT *
        FROM products
        WHERE active = 1
        ORDER BY id DESC
    """).fetchall()

    connection.close()

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


def require_staff():

    if not session.get("staff"):
        abort(403)


@app.route("/staff")
def dashboard():

    require_staff()

    connection = get_db()

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    visitors = connection.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 200
    """).fetchall()

    total_visitors = connection.execute(
        "SELECT COUNT(*) FROM visitors"
    ).fetchone()[0]

    total_stock = connection.execute(
        "SELECT COALESCE(SUM(stock), 0) FROM products"
    ).fetchone()[0]

    product_count = connection.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    connection.close()

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

    require_staff()

    name = request.form.get("name", "").strip()

    if not name:
        flash("Product name is required.", "error")
        return redirect(url_for("dashboard"))

    try:
        price = max(float(request.form.get("price", 0)), 0)
        stock = max(int(request.form.get("stock", 0)), 0)

    except ValueError:
        flash("Invalid price or stock.", "error")
        return redirect(url_for("dashboard"))

    connection = get_db()

    connection.execute("""
        INSERT INTO products
        (
            name,
            description,
            price,
            stock,
            sizes,
            color,
            image_url,
            active,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        name,
        request.form.get("description", "").strip(),
        price,
        stock,
        request.form.get("sizes", "").strip(),
        request.form.get("color", "").strip(),
        request.form.get("image_url", "").strip(),
        datetime.now(timezone.utc).isoformat()
    ))

    connection.commit()
    connection.close()

    flash("Product added successfully.", "success")

    return redirect(url_for("dashboard"))


@app.route("/staff/product/<int:product_id>/update", methods=["POST"])
def update_product(product_id):

    require_staff()

    name = request.form.get("name", "").strip()

    if not name:
        flash("Product name is required.", "error")
        return redirect(url_for("dashboard"))

    try:
        price = max(float(request.form.get("price", 0)), 0)
        stock = max(int(request.form.get("stock", 0)), 0)

    except ValueError:
        flash("Invalid price or stock.", "error")
        return redirect(url_for("dashboard"))

    active = 1 if request.form.get("active") == "1" else 0

    connection = get_db()

    product = connection.execute(
        "SELECT id FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not product:
        connection.close()
        abort(404)

    connection.execute("""
        UPDATE products
        SET
            name = ?,
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

    connection.commit()
    connection.close()

    flash("Product updated successfully.", "success")

    return redirect(url_for("dashboard"))


@app.route("/staff/product/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):

    require_staff()

    connection = get_db()

    connection.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    connection.commit()
    connection.close()

    flash("Product deleted.", "success")

    return redirect(url_for("dashboard"))


@app.errorhandler(403)
def forbidden(error):
    return "Staff access required.", 403


@app.errorhandler(404)
def not_found(error):
    return "Page not found.", 404


init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1"
    )
