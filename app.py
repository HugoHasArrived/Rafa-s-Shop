import os, sqlite3, secrets, hashlib, hmac, json
from datetime import datetime, timezone
from functools import wraps
from urllib.request import urlopen, Request
from urllib.parse import quote

from flask import Flask, g, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "store.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "CHANGE_THIS_SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
ALLOWED_IMAGES = {"png", "jpg", "jpeg", "webp", "gif"}

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()

def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210000)
    return salt.hex() + ":" + digest.hex()

def password_ok(password, stored):
    try:
        salt, digest = stored.split(":")
        test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 210000)
        return hmac.compare_digest(test.hex(), digest)
    except Exception:
        return False

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        price REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        sizes TEXT DEFAULT '',
        colors TEXT DEFAULT '',
        image TEXT DEFAULT '',
        featured INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS visitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        country TEXT DEFAULT '',
        region TEXT DEFAULT '',
        city TEXT DEFAULT '',
        device TEXT DEFAULT '',
        browser TEXT DEFAULT '',
        os TEXT DEFAULT '',
        path TEXT DEFAULT '',
        referrer TEXT DEFAULT '',
        visited_at TEXT NOT NULL
    );
    """)

    defaults = {
        "store_name": "Progressive Footwear",
        "tagline": "Estela Interchangeable Straps — mix, match, and make every step yours.",
        "address": "Gat Tayaw Street, Liliw, Laguna, Philippines",
        "contact": "(049) 5633 352",
        "email": "",
        "facebook": "",
        "privacy_notice": "This website records basic technical visitor information for security and site analytics. Visitor information is restricted to authorized staff."
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            (key, value)
        )

    if conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
        username = os.environ.get("STAFF_USERNAME", "staff")
        password = os.environ.get("STAFF_PASSWORD", "ChangeMe123!")
        conn.execute(
            "INSERT INTO staff(username,password_hash,created_at) VALUES(?,?,?)",
            (username, password_hash(password), datetime.now(timezone.utc).isoformat())
        )

    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        products = [
            ("Estela Interchangeable Straps — Daisy",
             "Estela Interchangeable Straps with a woven natural-fiber style sole and floral daisy strap design. Mix and match your straps.",
             0, 0, "Ask staff", "Yellow / Daisy", "estela_1.jpeg", 1),
            ("Estela Interchangeable Straps — Classic Yellow",
             "Classic Estela interchangeable strap set featuring a warm yellow strap and woven natural-fiber style sole.",
             0, 0, "Ask staff", "Yellow", "estela_2.jpeg", 1),
            ("Estela Interchangeable Straps — Floral Collection",
             "Estela interchangeable straps shown with multiple colorful floral designs. Choose your favorite look.",
             0, 0, "Ask staff", "Navy, Brown, Red, Green, Black, Yellow", "estela_3.jpeg", 1),
            ("Estela Interchangeable Straps — Plain Colors",
             "Estela interchangeable strap collection in versatile plain colors for everyday styling.",
             0, 0, "Ask staff", "Navy, White, Black, Brown, Green", "estela_4.jpeg", 0)
        ]
        for name, desc, price, stock, sizes, colors, image, featured in products:
            conn.execute("""
                INSERT INTO products
                (name,description,price,stock,sizes,colors,image,featured,active,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (name, desc, price, stock, sizes, colors, image, featured, 1, now, now))
    conn.commit()
    conn.close()

def settings():
    return {r["key"]: r["value"] for r in db().execute("SELECT key,value FROM settings").fetchall()}

def client_ip():
    if os.environ.get("TRUST_PROXY_HEADERS", "").lower() == "true":
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"

def parse_ua(ua):
    u = ua.lower()
    if "iphone" in u: device = "iPhone"
    elif "ipad" in u: device = "iPad"
    elif "android" in u: device = "Android"
    elif "mobile" in u: device = "Mobile"
    elif "windows" in u: device = "Windows PC"
    elif "macintosh" in u: device = "Mac"
    elif "linux" in u: device = "Linux PC"
    else: device = "Other"

    if "edg/" in u: browser = "Edge"
    elif "chrome/" in u: browser = "Chrome"
    elif "firefox/" in u: browser = "Firefox"
    elif "safari/" in u: browser = "Safari"
    else: browser = "Other"

    if "windows" in u: os_name = "Windows"
    elif "android" in u: os_name = "Android"
    elif "iphone" in u or "ipad" in u: os_name = "iOS"
    elif "mac os" in u: os_name = "macOS"
    elif "linux" in u: os_name = "Linux"
    else: os_name = "Other"
    return device, browser, os_name

def ip_location(ip):
    if ip in ("127.0.0.1", "::1", "unknown") or ip.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
        return "Local/Private", "", ""
    try:
        req = Request(
            f"http://ip-api.com/json/{quote(ip)}?fields=status,country,regionName,city",
            headers={"User-Agent": "EstelaStore/1.0"}
        )
        with urlopen(req, timeout=2.5) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("status") == "success":
            return data.get("country", ""), data.get("regionName", ""), data.get("city", "")
    except Exception:
        pass
    return "Unknown", "", ""

def log_visitor():
    ip = client_ip()
    device, browser, os_name = parse_ua(request.headers.get("User-Agent", ""))
    country, region, city = ip_location(ip)
    db().execute("""
        INSERT INTO visitors
        (ip,country,region,city,device,browser,os,path,referrer,visited_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        ip, country, region, city, device, browser, os_name,
        request.path, request.referrer or "",
        datetime.now(timezone.utc).isoformat()
    ))
    db().commit()

def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("staff_id"):
            return redirect(url_for("staff_login"))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def globals_for_templates():
    return {"settings": settings()}

@app.before_request
def visitor_middleware():
    if request.path.startswith("/static/") or request.path.startswith("/staff") or request.path.startswith("/robots.txt"):
        return
    if request.method == "GET":
        try:
            log_visitor()
        except Exception:
            pass

@app.route("/")
def home():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "featured")
    sql = "SELECT * FROM products WHERE active=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR description LIKE ? OR colors LIKE ? OR sizes LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like, like]
    if sort == "price_low":
        sql += " ORDER BY price ASC, featured DESC"
    elif sort == "price_high":
        sql += " ORDER BY price DESC, featured DESC"
    elif sort == "stock":
        sql += " ORDER BY stock DESC, featured DESC"
    else:
        sql += " ORDER BY featured DESC, id DESC"
    products = db().execute(sql, params).fetchall()
    return render_template("home.html", products=products, q=q, sort=sort)

@app.route("/product/<int:product_id>")
def product(product_id):
    p = db().execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if not p:
        return "Product not found", 404
    return render_template("product.html", product=p)

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if session.get("staff_id"):
        return redirect(url_for("staff_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM staff WHERE username=?", (username,)).fetchone()
        if user and password_ok(password, user["password_hash"]):
            session.clear()
            session["staff_id"] = user["id"]
            session["staff_username"] = user["username"]
            return redirect(url_for("staff_dashboard"))
        flash("Invalid staff username or password.", "error")
    return render_template("staff_login.html")

@app.route("/staff/logout")
def staff_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/staff")
@staff_required
def staff_dashboard():
    products = db().execute("SELECT * FROM products ORDER BY active DESC, id DESC").fetchall()
    total = db().execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today = db().execute("SELECT COUNT(*) FROM visitors WHERE visited_at >= ?", (today_start,)).fetchone()[0]
    low = db().execute("SELECT COUNT(*) FROM products WHERE active=1 AND stock <= 5").fetchone()[0]
    recent = db().execute("SELECT * FROM visitors ORDER BY id DESC LIMIT 100").fetchall()
    return render_template("staff.html", products=products, total=total, today=today, low=low, recent=recent)

@app.route("/staff/product/new", methods=["GET", "POST"])
@staff_required
def new_product():
    if request.method == "POST":
        return save_product(None)
    return render_template("product_form.html", product=None)

@app.route("/staff/product/<int:product_id>/edit", methods=["GET", "POST"])
@staff_required
def edit_product(product_id):
    product = db().execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        return "Product not found", 404
    if request.method == "POST":
        return save_product(product)
    return render_template("product_form.html", product=product)

def save_product(existing):
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("Product name is required.", "error")
        return redirect(request.url)

    try:
        price = max(0, float(f.get("price", "0")))
    except Exception:
        price = 0
    try:
        stock = max(0, int(f.get("stock", "0")))
    except Exception:
        stock = 0

    image = existing["image"] if existing else ""
    uploaded = request.files.get("image")
    if uploaded and uploaded.filename:
        ext = uploaded.filename.rsplit(".", 1)[-1].lower() if "." in uploaded.filename else ""
        if ext not in ALLOWED_IMAGES:
            flash("Unsupported image type.", "error")
            return redirect(request.url)
        filename = f"{secrets.token_hex(12)}.{ext}"
        uploaded.save(os.path.join(UPLOAD_DIR, filename))
        if image:
            old = os.path.join(UPLOAD_DIR, os.path.basename(image))
            if os.path.isfile(old):
                try:
                    os.remove(old)
                except Exception:
                    pass
        image = filename

    now = datetime.now(timezone.utc).isoformat()
    active = 1 if f.get("active") == "on" else 0
    featured = 1 if f.get("featured") == "on" else 0

    if existing:
        db().execute("""
            UPDATE products SET name=?,description=?,price=?,stock=?,sizes=?,colors=?,image=?,
            featured=?,active=?,updated_at=? WHERE id=?
        """, (
            name, f.get("description", ""), price, stock,
            f.get("sizes", ""), f.get("colors", ""), image,
            featured, active, now, existing["id"]
        ))
    else:
        db().execute("""
            INSERT INTO products
            (name,description,price,stock,sizes,colors,image,featured,active,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (
            name, f.get("description", ""), price, stock,
            f.get("sizes", ""), f.get("colors", ""), image,
            featured, active, now, now
        ))
    db().commit()
    flash("Product saved successfully.", "success")
    return redirect(url_for("staff_dashboard"))

@app.post("/staff/product/<int:product_id>/delete")
@staff_required
def delete_product(product_id):
    p = db().execute("SELECT image FROM products WHERE id=?", (product_id,)).fetchone()
    if p:
        db().execute("DELETE FROM products WHERE id=?", (product_id,))
        db().commit()
        if p["image"]:
            path = os.path.join(UPLOAD_DIR, os.path.basename(p["image"]))
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
    flash("Product deleted.", "success")
    return redirect(url_for("staff_dashboard"))

@app.route("/staff/settings", methods=["GET", "POST"])
@staff_required
def staff_settings():
    if request.method == "POST":
        allowed = ["store_name", "tagline", "address", "contact", "email", "facebook", "privacy_notice"]
        for key in allowed:
            db().execute("""
                INSERT INTO settings(key,value) VALUES(?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, request.form.get(key, "").strip()))
        db().commit()
        flash("Store settings updated.", "success")
        return redirect(url_for("staff_settings"))
    return render_template("settings.html")

@app.post("/staff/change-password")
@staff_required
def change_password():
    current = request.form.get("current", "")
    new = request.form.get("new", "")
    user = db().execute("SELECT * FROM staff WHERE id=?", (session["staff_id"],)).fetchone()
    if not user or not password_ok(current, user["password_hash"]):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("staff_settings"))
    if len(new) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("staff_settings"))
    db().execute("UPDATE staff SET password_hash=? WHERE id=?", (password_hash(new), user["id"]))
    db().commit()
    flash("Password changed.", "success")
    return redirect(url_for("staff_settings"))

@app.get("/robots.txt")
def robots():
    return "User-agent: *\nDisallow: /staff\n", 200, {"Content-Type": "text/plain"}

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
