import os
import sqlite3
import hashlib
from functools import wraps
from flask import (
    Flask, request, redirect, url_for, session,
    jsonify, render_template_string
)

app = Flask(__name__)

# ============================================================
# CONFIG
# ============================================================

app.secret_key = os.environ.get("SECRET_KEY", "padron-change-this-secret-key")

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "padron.db")

STORE_NAME = "PADRON"
STORE_ADDRESS = "268 A. Mabini Street, Liliw, Laguna"
STORE_PHONE = "0976 1296450"

# Change these credentials before using the staff system publicly.
STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "staff")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "padron2026")


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Footwear',
            description TEXT DEFAULT '',
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            sizes TEXT DEFAULT '',
            color TEXT DEFAULT '',
            material TEXT DEFAULT '',
            featured INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            language TEXT,
            page TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add starter products only if database is empty.
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    if count == 0:
        starter_products = [
            (
                "Handmade Mule",
                "Mules",
                "Handcrafted footwear inspired by Filipino artistry.",
                0,
                0,
                "35,36,37,38,39,40",
                "Natural",
                "Abaca",
                1
            ),
            (
                "Classic Flat",
                "Flats",
                "Elegant handmade flats created by Laguna artisans.",
                0,
                0,
                "35,36,37,38,39,40",
                "Brown",
                "Inabel",
                0
            ),
            (
                "Platform Espadrille",
                "Platform",
                "A handcrafted platform design celebrating local craftsmanship.",
                0,
                0,
                "35,36,37,38,39,40",
                "Natural",
                "Abaca",
                0
            ),
            (
                "Wedge Espadrille",
                "Wedges",
                "A Filipino-inspired wedge featuring locally sourced materials.",
                0,
                0,
                "35,36,37,38,39,40",
                "Earth",
                "Ifugao Fabric",
                0
            )
        ]

        conn.executemany("""
            INSERT INTO products
            (name, category, description, price, stock, sizes, color,
             material, featured)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, starter_products)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# AUTHENTICATION
# ============================================================

def staff_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in"):
            return redirect(url_for("staff_login"))
        return function(*args, **kwargs)

    return wrapper


# ============================================================
# VISITOR TRACKING
# ============================================================

@app.before_request
def track_visitor():
    # Don't record staff dashboard/API traffic.
    if request.path.startswith("/staff") or request.path.startswith("/api"):
        return

    try:
        conn = get_db()

        # Render/proxies can send the real visitor IP in X-Forwarded-For.
        forwarded = request.headers.get("X-Forwarded-For", "")
        ip = forwarded.split(",")[0].strip() if forwarded else request.remote_addr

        conn.execute("""
            INSERT INTO visitors (ip, user_agent, language, page)
            VALUES (?, ?, ?, ?)
        """, (
            ip,
            request.headers.get("User-Agent", "")[:500],
            request.headers.get("Accept-Language", "")[:200],
            request.path[:200]
        ))

        conn.commit()
        conn.close()
    except Exception:
        pass


# ============================================================
# MAIN PAGE
# ============================================================

@app.route("/")
def index():
    conn = get_db()
    products = conn.execute("""
        SELECT * FROM products
        ORDER BY featured DESC, id DESC
    """).fetchall()
    conn.close()

    return render_template_string(
        MAIN_PAGE,
        products=products
    )


# ============================================================
# STAFF LOGIN
# ============================================================

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == STAFF_USERNAME and password == STAFF_PASSWORD:
            session["staff_logged_in"] = True
            session["staff_username"] = username
            return redirect(url_for("staff_dashboard"))

        error = "Incorrect username or password."

    return render_template_string(
        LOGIN_PAGE,
        error=error
    )


@app.route("/staff/logout")
def staff_logout():
    session.clear()
    return redirect(url_for("index"))


# ============================================================
# STAFF DASHBOARD
# ============================================================

@app.route("/staff")
@staff_required
def staff_dashboard():

    conn = get_db()

    products = conn.execute("""
        SELECT * FROM products
        ORDER BY id DESC
    """).fetchall()

    visitor_count = conn.execute("""
        SELECT COUNT(*) FROM visitors
    """).fetchone()[0]

    recent_visitors = conn.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 100
    """).fetchall()

    total_stock = conn.execute("""
        SELECT COALESCE(SUM(stock), 0)
        FROM products
    """).fetchone()[0]

    conn.close()

    return render_template_string(
        STAFF_PAGE,
        products=products,
        visitors=recent_visitors,
        visitor_count=visitor_count,
        total_stock=total_stock
    )


# ============================================================
# PRODUCT API
# ============================================================

@app.route("/api/products", methods=["POST"])
@staff_required
def add_product():

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()

    if not name:
        return jsonify({
            "success": False,
            "message": "Product name is required."
        }), 400

    try:
        price = float(data.get("price", 0))
        stock = int(data.get("stock", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid price or stock."
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO products
        (name, category, description, price, stock, sizes,
         color, material, featured)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        str(data.get("category", "Footwear")),
        str(data.get("description", "")),
        price,
        stock,
        str(data.get("sizes", "")),
        str(data.get("color", "")),
        str(data.get("material", "")),
        1 if data.get("featured") else 0
    ))

    conn.commit()
    product_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "success": True,
        "id": product_id
    })


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@staff_required
def update_product(product_id):

    data = request.get_json(silent=True) or {}

    try:
        price = float(data.get("price", 0))
        stock = int(data.get("stock", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid price or stock."
        }), 400

    conn = get_db()

    result = conn.execute("""
        UPDATE products
        SET
            name = ?,
            category = ?,
            description = ?,
            price = ?,
            stock = ?,
            sizes = ?,
            color = ?,
            material = ?,
            featured = ?
        WHERE id = ?
    """, (
        str(data.get("name", "")).strip(),
        str(data.get("category", "Footwear")),
        str(data.get("description", "")),
        price,
        stock,
        str(data.get("sizes", "")),
        str(data.get("color", "")),
        str(data.get("material", "")),
        1 if data.get("featured") else 0,
        product_id
    ))

    conn.commit()
    conn.close()

    if result.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    return jsonify({"success": True})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@staff_required
def delete_product(product_id):

    conn = get_db()

    result = conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()
    conn.close()

    if result.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    return jsonify({"success": True})


# ============================================================
# CLEAR VISITOR LOG
# ============================================================

@app.route("/api/visitors/clear", methods=["POST"])
@staff_required
def clear_visitors():

    conn = get_db()
    conn.execute("DELETE FROM visitors")
    conn.commit()
    conn.close()

    return jsonify({"success": True})


# ============================================================
# MAIN WEBSITE HTML
# ============================================================

MAIN_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>PADRON | Filipino Handcrafted Footwear</title>

<style>

:root {
    --bg: #f7efe5;
    --surface: #fffaf4;
    --surface2: #efe0cf;
    --text: #3a2418;
    --muted: #806858;
    --brown: #8a5a3b;
    --brown2: #b47b55;
    --gold: #d4a15c;
    --border: rgba(92,55,31,.15);
    --shadow: 0 18px 50px rgba(82,49,27,.13);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    font-family: Inter, Arial, sans-serif;
    background:
        radial-gradient(circle at 10% 10%, rgba(212,161,92,.15), transparent 30%),
        radial-gradient(circle at 90% 20%, rgba(180,123,85,.12), transparent 30%),
        var(--bg);
    color: var(--text);
    transition: .35s;
    text-align: center;
}

body.dark {
    --bg: #211812;
    --surface: #2e211a;
    --surface2: #3c2a20;
    --text: #fff3e4;
    --muted: #c8ad98;
    --brown: #d49b70;
    --brown2: #e5b285;
    --gold: #e1b66f;
    --border: rgba(255,255,255,.12);
    --shadow: 0 20px 60px rgba(0,0,0,.35);
}

button,
input,
select,
textarea {
    font: inherit;
}

button {
    cursor: pointer;
}

.nav {
    position: sticky;
    top: 0;
    z-index: 50;
    backdrop-filter: blur(18px);
    background: color-mix(in srgb, var(--surface), transparent 12%);
    border-bottom: 1px solid var(--border);
}

.nav-inner {
    max-width: 1200px;
    margin: auto;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 900;
    letter-spacing: 4px;
}

.brand img {
    width: 45px;
    height: 45px;
    object-fit: contain;
    border-radius: 12px;
}

.nav-links {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
}

.nav-links a,
.nav-button {
    border: 0;
    background: transparent;
    color: var(--text);
    text-decoration: none;
    padding: 9px 13px;
    border-radius: 999px;
    transition: .25s;
}

.nav-links a:hover,
.nav-button:hover {
    background: var(--surface2);
    transform: translateY(-2px);
}

.hero {
    min-height: 78vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 70px 20px;
}

.hero-inner {
    max-width: 950px;
    margin: auto;
}

.hero-logo {
    width: min(170px, 45vw);
    height: 170px;
    object-fit: contain;
    filter: drop-shadow(0 15px 25px rgba(100,60,30,.2));
    animation: float 5s ease-in-out infinite;
}

@keyframes float {
    0%,100% { transform: translateY(0); }
    50% { transform: translateY(-12px); }
}

.badge {
    display: inline-block;
    margin: 20px 0 10px;
    padding: 8px 16px;
    border-radius: 999px;
    background: var(--surface2);
    color: var(--brown);
    font-weight: 800;
    letter-spacing: 1px;
}

h1 {
    font-size: clamp(50px, 10vw, 110px);
    line-height: .9;
    margin: 12px 0;
    letter-spacing: -5px;
}

.hero p {
    max-width: 700px;
    margin: 25px auto;
    color: var(--muted);
    font-size: 18px;
    line-height: 1.8;
}

.hero-buttons {
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
}

.btn {
    border: 1px solid var(--border);
    padding: 14px 22px;
    border-radius: 999px;
    text-decoration: none;
    font-weight: 800;
    transition: .25s;
}

.btn-primary {
    color: white;
    background: linear-gradient(135deg, var(--brown), var(--brown2));
    box-shadow: 0 12px 30px rgba(120,75,40,.2);
}

.btn-secondary {
    color: var(--text);
    background: var(--surface);
}

.btn:hover {
    transform: translateY(-4px) scale(1.02);
}

.section {
    padding: 90px 20px;
}

.section-inner {
    max-width: 1150px;
    margin: auto;
}

.section-title {
    font-size: clamp(35px, 6vw, 60px);
    margin: 0 0 15px;
    letter-spacing: -2px;
}

.section-subtitle {
    max-width: 750px;
    margin: 0 auto 45px;
    color: var(--muted);
    line-height: 1.8;
}

.about-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
}

.info-card {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 30px;
    border-radius: 30px;
    box-shadow: var(--shadow);
    transition: .3s;
}

.info-card:hover {
    transform: translateY(-8px);
}

.info-card h3 {
    color: var(--brown);
}

.products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 22px;
}

.product {
    position: relative;
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 30px;
    padding: 25px;
    box-shadow: var(--shadow);
    transition: .35s;
}

.product:hover {
    transform: translateY(-10px) rotate(-.5deg);
}

.product-art {
    height: 190px;
    border-radius: 22px;
    background:
        radial-gradient(circle at 50% 40%, rgba(212,161,92,.55), transparent 28%),
        linear-gradient(135deg, var(--surface2), transparent);
    display: grid;
    place-items: center;
    font-size: 75px;
}

.product h3 {
    margin: 20px 0 5px;
}

.product p {
    color: var(--muted);
    line-height: 1.6;
}

.price {
    font-weight: 900;
    color: var(--brown);
    font-size: 20px;
}

.stock {
    display: inline-block;
    margin-top: 10px;
    padding: 7px 12px;
    border-radius: 999px;
    background: var(--surface2);
    color: var(--muted);
    font-size: 13px;
}

.mission {
    background: var(--surface2);
}

.contact {
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 70px 20px;
}

.contact-box {
    max-width: 800px;
    margin: auto;
}

.contact h2 {
    font-size: 45px;
}

.contact-line {
    color: var(--muted);
    margin: 12px 0;
}

footer {
    padding: 35px 20px;
    color: var(--muted);
    background: var(--surface);
    border-top: 1px solid var(--border);
}

#toast {
    position: fixed;
    bottom: 25px;
    left: 50%;
    transform: translate(-50%, 120px);
    z-index: 100;
    background: var(--text);
    color: var(--bg);
    padding: 14px 20px;
    border-radius: 999px;
    transition: .3s;
    box-shadow: var(--shadow);
}

#toast.show {
    transform: translate(-50%, 0);
}

@media(max-width:700px) {

    .nav-inner {
        flex-direction: column;
    }

    .nav-links {
        width: 100%;
    }

    h1 {
        letter-spacing: -3px;
    }

    .hero {
        padding-top: 45px;
    }
}

</style>
</head>

<body>

<nav class="nav">

<div class="nav-inner">

<div class="brand">

<img
    src="{{ url_for('static', filename='Image0 (3).jpeg') }}"
    onerror="this.style.display='none'"
    alt="PADRON logo"
>

<span>PADRON</span>

</div>

<div class="nav-links">

<a href="#about" data-en="About" data-fil="Tungkol">About</a>

<a href="#products" data-en="Products" data-fil="Mga Produkto">
Products
</a>

<a href="#mission" data-en="Mission" data-fil="Misyon">
Mission
</a>

<a href="#contact" data-en="Contact" data-fil="Kontak">
Contact
</a>

<a href="{{ url_for('staff_login') }}">
Staff
</a>

<button class="nav-button" onclick="toggleLanguage()" id="languageButton">
🇵🇭 Filipino
</button>

<button class="nav-button" onclick="toggleDark()" id="themeButton">
🌙
</button>

</div>

</div>

</nav>


<section class="hero">

<div class="hero-inner">

<img
    class="hero-logo"
    src="{{ url_for('static', filename='Image0 (3).jpeg') }}"
    onerror="this.style.display='none'"
    alt="PADRON"
>

<div class="badge"
     data-en="Handcrafted in Liliw, Laguna"
     data-fil="Gawang-kamay sa Liliw, Laguna">
Handcrafted in Liliw, Laguna
</div>

<h1>PADRON</h1>

<p
data-en="Filipino footwear shaped by heritage, creativity, craftsmanship and the hands of local artisans."
data-fil="Sapatos na Pilipino, hinubog ng ating kultura, pagkamalikhain, husay at kamay ng mga lokal na artisan.">
Filipino footwear shaped by heritage, creativity, craftsmanship and the hands of local artisans.
</p>

<div class="hero-buttons">

<a href="#products" class="btn btn-primary"
data-en="Explore Products"
data-fil="Tingnan ang Mga Produkto">
Explore Products
</a>

<a href="#about" class="btn btn-secondary"
data-en="Our Story"
data-fil="Ang Aming Kuwento">
Our Story
</a>

</div>

</div>

</section>


<section class="section" id="about">

<div class="section-inner">

<h2 class="section-title"
data-en="Our Story"
data-fil="Ang Aming Kuwento">
Our Story
</h2>

<p class="section-subtitle">

Golden Zapatillas Corporation is a family-owned business established in
<strong>2015</strong>, continuing a family tradition of manufacturing
high-quality footwear in Liliw, Laguna.

<br><br>

Our artisans include artist painters, beadworkers, embroiderers and
shoemakers. We use locally sourced materials such as abaca, Ifugao fabric
and Inabel to support Filipino suppliers and bring Filipino craftsmanship
into world-class footwear.

</p>


<div class="about-grid">

<div class="info-card">

<h3>🇵🇭 Filipino Craft</h3>

<p>
Every design celebrates Filipino creativity, heritage and the craftsmanship
of Laguna artisans.
</p>

</div>


<div class="info-card">

<h3>🌿 Local Materials</h3>

<p>
We work with materials including abaca, Ifugao fabric and Inabel while
supporting local suppliers.
</p>

</div>


<div class="info-card">

<h3>✨ PADRON</h3>

<p>
"Padron" means "pattern" in Spanish. Every footwear design begins with
a pattern before becoming the finished piece.
</p>

</div>

</div>

</div>

</section>


<section class="section" id="products">

<div class="section-inner">

<h2 class="section-title"
data-en="Our Products"
data-fil="Aming Mga Produkto">
Our Products
</h2>

<p class="section-subtitle"
data-en="Explore handcrafted footwear inspired by the creativity and skills of Filipino artisans."
data-fil="Tuklasin ang handmade footwear na hango sa pagkamalikhain at husay ng mga Pilipinong artisan.">
Explore handcrafted footwear inspired by the creativity and skills of Filipino artisans.
</p>


<div class="products-grid">

{% for product in products %}

<div class="product">

<div class="product-art">

{% if "wedge" in product["name"].lower() %}
👡
{% elif "flat" in product["name"].lower() %}
🥿
{% elif "mule" in product["name"].lower() %}
🩴
{% else %}
👞
{% endif %}

</div>

<h3>{{ product["name"] }}</h3>

<p>{{ product["description"] }}</p>

<div class="price">

{% if product["price"] > 0 %}
₱{{ "%.2f"|format(product["price"]) }}
{% else %}
Price available soon
{% endif %}

</div>

<div class="stock">

{{ product["category"] }}
{% if product["material"] %}
· {{ product["material"] }}
{% endif %}

</div>

</div>

{% endfor %}

</div>

</div>

</section>


<section class="section mission" id="mission">

<div class="section-inner">

<h2 class="section-title"
data-en="Mission"
data-fil="Misyon">
Mission
</h2>

<p class="section-subtitle">

To empower Filipino artisans, including shoemakers and women artisans
skilled in handpainting, embroidery and crochet, by creating sustainable,
high-quality footwear that celebrates local heritage and craftsmanship.

<br><br>

We aim to foster economic growth in Liliw and preserve our family's
footwear-making legacy established in <strong>1963</strong>.

</p>


<h2 class="section-title"
data-en="Vision"
data-fil="Bisyon">
Vision
</h2>

<p class="section-subtitle">

To be one of the leading pioneers in sustainable, handcrafted footwear,
inspiring a new generation of artisans, preserving our family's legacy,
and positioning Liliw as a center of footwear excellence.

</p>

</div>

</section>


<section class="contact" id="contact">

<div class="contact-box">

<h2>PADRON</h2>

<p class="contact-line">
📍 {{ store_address }}
</p>

<p class="contact-line">
📱 {{ store_phone }}
</p>

<p class="contact-line">
🇵🇭 Liliw, Laguna, Philippines
</p>

</div>

</section>


<footer>

<p>PADRON · Filipino Handcrafted Footwear</p>

<p>By JHR</p>

</footer>


<div id="toast"></div>


<script>

let language = localStorage.getItem("padron-language") || "en";

let dark = localStorage.getItem("padron-dark") === "true";


function updateLanguage() {

    document.querySelectorAll("[data-en]").forEach(element => {

        if (language === "fil") {
            element.textContent = element.dataset.fil;
        } else {
            element.textContent = element.dataset.en;
        }

    });

    document.getElementById("languageButton").textContent =
        language === "fil" ? "🇺🇸 English" : "🇵🇭 Filipino";

    localStorage.setItem("padron-language", language);
}


function toggleLanguage() {

    language = language === "en" ? "fil" : "en";

    updateLanguage();

    showToast(
        language === "fil"
        ? "Filipino language selected"
        : "English language selected"
    );
}


function toggleDark() {

    dark = !dark;

    document.body.classList.toggle("dark", dark);

    document.getElementById("themeButton").textContent =
        dark ? "☀️" : "🌙";

    localStorage.setItem("padron-dark", dark);
}


function showToast(message) {

    const toast = document.getElementById("toast");

    toast.textContent = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2200);
}


document.body.classList.toggle("dark", dark);

document.getElementById("themeButton").textContent =
    dark ? "☀️" : "🌙";

updateLanguage();

</script>

</body>
</html>
"""


# ============================================================
# LOGIN HTML
# ============================================================

LOGIN_PAGE = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>PADRON Staff Login</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 20px;
    font-family: Arial, sans-serif;
    color: #3a2418;
    background:
        radial-gradient(circle at 20% 20%, #e7c7a8, transparent 30%),
        radial-gradient(circle at 80% 80%, #c99a72, transparent 30%),
        #f7efe5;
}

.login {
    width: min(430px, 100%);
    background: #fffaf4;
    border: 1px solid rgba(80,50,30,.15);
    border-radius: 35px;
    padding: 40px;
    box-shadow: 0 25px 80px rgba(80,50,30,.2);
    text-align: center;
}

.logo {
    width: 90px;
    height: 90px;
    object-fit: contain;
    border-radius: 20px;
}

h1 {
    margin-bottom: 5px;
}

p {
    color: #806858;
}

input {
    width: 100%;
    padding: 15px;
    margin: 8px 0;
    border: 1px solid #ddc7b1;
    border-radius: 15px;
    outline: none;
}

button {
    width: 100%;
    border: 0;
    padding: 15px;
    margin-top: 12px;
    border-radius: 999px;
    color: white;
    background: linear-gradient(135deg, #8a5a3b, #b47b55);
    font-weight: 800;
    cursor: pointer;
}

.error {
    color: #a33b2b;
    background: #f9d9d1;
    padding: 10px;
    border-radius: 12px;
}

.back {
    display: block;
    margin-top: 20px;
    color: #8a5a3b;
    text-decoration: none;
}

</style>

</head>

<body>

<div class="login">

<img
    class="logo"
    src="{{ url_for('static', filename='Image0 (3).jpeg') }}"
    onerror="this.style.display='none'"
    alt="PADRON"
>

<h1>PADRON</h1>

<p>Staff Portal</p>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

<form method="POST">

<input
    type="text"
    name="username"
    placeholder="Username"
    autocomplete="username"
    required
>

<input
    type="password"
    name="password"
    placeholder="Password"
    autocomplete="current-password"
    required
>

<button type="submit">
Sign In
</button>

</form>

<a class="back" href="/">
← Back to website
</a>

</div>

</body>
</html>
"""


# ============================================================
# STAFF DASHBOARD HTML
# ============================================================

STAFF_PAGE = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>PADRON Staff Dashboard</title>

<style>

:root {
    --bg:#f7efe5;
    --surface:#fffaf4;
    --surface2:#ead6c1;
    --text:#3a2418;
    --muted:#806858;
    --brown:#8a5a3b;
    --brown2:#b47b55;
    --red:#b34a3c;
    --green:#467d56;
    --border:rgba(70,40,20,.14);
}

* {
    box-sizing:border-box;
}

body {
    margin:0;
    font-family:Arial,sans-serif;
    color:var(--text);
    background:
        radial-gradient(circle at 10% 10%,#e8c7a5,transparent 25%),
        var(--bg);
}

header {
    position:sticky;
    top:0;
    z-index:10;
    background:rgba(255,250,244,.9);
    backdrop-filter:blur(15px);
    border-bottom:1px solid var(--border);
}

.header-inner {
    max-width:1250px;
    margin:auto;
    padding:18px 20px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:15px;
}

.logo-title {
    font-weight:900;
    letter-spacing:3px;
}

.actions {
    display:flex;
    gap:8px;
    flex-wrap:wrap;
}

.button {
    border:0;
    border-radius:999px;
    padding:11px 17px;
    cursor:pointer;
    background:var(--surface2);
    color:var(--text);
    text-decoration:none;
    font-weight:700;
}

.button.primary {
    color:white;
    background:linear-gradient(135deg,var(--brown),var(--brown2));
}

.button.danger {
    color:white;
    background:var(--red);
}

.container {
    max-width:1250px;
    margin:auto;
    padding:40px 20px 80px;
}

h1 {
    font-size:48px;
    margin-bottom:5px;
}

.subtitle {
    color:var(--muted);
}

.stats {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:15px;
    margin:30px 0;
}

.stat {
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:25px;
    padding:25px;
}

.stat-number {
    font-size:40px;
    font-weight:900;
    color:var(--brown);
}

.card {
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:28px;
    padding:25px;
    margin-top:25px;
    overflow:hidden;
}

.card h2 {
    margin-top:0;
}

.table-wrap {
    overflow:auto;
}

table {
    width:100%;
    border-collapse:collapse;
    min-width:900px;
}

th,
td {
    padding:13px 10px;
    border-bottom:1px solid var(--border);
    text-align:left;
}

th {
    color:var(--brown);
}

input,
select,
textarea {
    width:100%;
    padding:11px;
    border:1px solid var(--border);
    border-radius:10px;
    background:white;
    color:#2c1c13;
}

textarea {
    min-height:70px;
    resize:vertical;
}

.form-grid {
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:15px;
}

.form-grid .full {
    grid-column:1/-1;
}

.add-form {
    display:none;
}

.add-form.open {
    display:block;
}

.visitor-table {
    max-height:500px;
    overflow:auto;
}

.small {
    font-size:12px;
    color:var(--muted);
}

.badge {
    display:inline-block;
    padding:6px 10px;
    border-radius:999px;
    background:var(--surface2);
}

@media(max-width:700px) {

    .header-inner {
        flex-direction:column;
    }

    h1 {
        font-size:36px;
    }

    .form-grid {
        grid-template-columns:1fr;
    }

}

</style>

</head>

<body>

<header>

<div class="header-inner">

<div class="logo-title">
PADRON · STAFF
</div>

<div class="actions">

<a class="button" href="/">
View Store
</a>

<a class="button danger" href="{{ url_for('staff_logout') }}">
Logout
</a>

</div>

</div>

</header>


<main class="container">

<h1>Staff Dashboard</h1>

<p class="subtitle">
Manage PADRON products and monitor website activity.
</p>


<section class="stats">

<div class="stat">

<div class="small">TOTAL VISITOR RECORDS</div>

<div class="stat-number">
{{ visitor_count }}
</div>

</div>


<div class="stat">

<div class="small">TOTAL STOCK</div>

<div class="stat-number">
{{ total_stock }}
</div>

</div>


<div class="stat">

<div class="small">PRODUCTS</div>

<div class="stat-number">
{{ products|length }}
</div>

</div>

</section>


<section class="card">

<h2>Products</h2>

<button class="button primary"
onclick="document.getElementById('addForm').classList.toggle('open')">

＋ Add Product

</button>


<div id="addForm" class="add-form">

<br>

<div class="form-grid">

<div>
<label>Name</label>
<input id="new-name">
</div>

<div>
<label>Category</label>
<input id="new-category" value="Footwear">
</div>

<div>
<label>Price</label>
<input id="new-price" type="number" step="0.01" value="0">
</div>

<div>
<label>Stock</label>
<input id="new-stock" type="number" value="0">
</div>

<div>
<label>Sizes</label>
<input id="new-sizes" placeholder="35,36,37,38,39,40">
</div>

<div>
<label>Material</label>
<input id="new-material" placeholder="Abaca">
</div>

<div>
<label>Color</label>
<input id="new-color">
</div>

<div>
<label>Featured</label>
<select id="new-featured">
<option value="0">No</option>
<option value="1">Yes</option>
</select>
</div>

<div class="full">
<label>Description</label>
<textarea id="new-description"></textarea>
</div>

</div>

<br>

<button class="button primary" onclick="addProduct()">
Save Product
</button>

</div>


<div class="table-wrap">

<table>

<thead>

<tr>
<th>Name</th>
<th>Category</th>
<th>Price</th>
<th>Stock</th>
<th>Sizes</th>
<th>Material</th>
<th>Featured</th>
<th>Action</th>
</tr>

</thead>

<tbody>

{% for p in products %}

<tr data-id="{{ p.id }}">

<td>
<input class="name" value="{{ p.name }}">
</td>

<td>
<input class="category" value="{{ p.category }}">
</td>

<td>
<input class="price" type="number" step="0.01" value="{{ p.price }}">
</td>

<td>
<input class="stock" type="number" value="{{ p.stock }}">
</td>

<td>
<input class="sizes" value="{{ p.sizes }}">
</td>

<td>
<input class="material" value="{{ p.material }}">
</td>

<td>

<select class="featured">

<option value="0" {% if not p.featured %}selected{% endif %}>
No
</option>

<option value="1" {% if p.featured %}selected{% endif %}>
Yes
</option>

</select>

</td>

<td>

<button class="button primary"
onclick="saveProduct({{ p.id }})">
Save
</button>

<button class="button danger"
onclick="deleteProduct({{ p.id }})">
Delete
</button>

</td>

</tr>

{% endfor %}

</tbody>

</table>

</div>

</section>


<section class="card">

<div style="display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap">

<div>

<h2>Visitor Activity</h2>

<p class="small">
IP address, user agent, language and page information received by the server.
</p>

</div>

<button class="button danger"
onclick="clearVisitors()">
Clear Logs
</button>

</div>


<div class="visitor-table">

<table>

<thead>

<tr>
<th>Time</th>
<th>IP</th>
<th>Device / Browser</th>
<th>Language</th>
<th>Page</th>
</tr>

</thead>

<tbody>

{% for visitor in visitors %}

<tr>

<td>
{{ visitor.created_at }}
</td>

<td>
{{ visitor.ip }}
</td>

<td style="max-width:450px">
{{ visitor.user_agent }}
</td>

<td>
{{ visitor.language }}
</td>

<td>
{{ visitor.page }}
</td>

</tr>

{% endfor %}

</tbody>

</table>

</div>

</section>

</main>


<script>

async function addProduct() {

    const data = {
        name: document.getElementById("new-name").value,
        category: document.getElementById("new-category").value,
        price: document.getElementById("new-price").value,
        stock: document.getElementById("new-stock").value,
        sizes: document.getElementById("new-sizes").value,
        material: document.getElementById("new-material").value,
        color: document.getElementById("new-color").value,
        featured: document.getElementById("new-featured").value === "1",
        description: document.getElementById("new-description").value
    };

    const response = await fetch("/api/products", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(data)
    });

    const result = await response.json();

    if (result.success) {
        location.reload();
    } else {
        alert(result.message || "Unable to add product.");
    }
}


async function saveProduct(id) {

    const row = document.querySelector(
        'tr[data-id="' + id + '"]'
    );

    const data = {
        name: row.querySelector(".name").value,
        category: row.querySelector(".category").value,
        price: row.querySelector(".price").value,
        stock: row.querySelector(".stock").value,
        sizes: row.querySelector(".sizes").value,
        material: row.querySelector(".material").value,
        featured: row.querySelector(".featured").value === "1"
    };

    const response = await fetch(
        "/api/products/" + id,
        {
            method:"PUT",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify(data)
        }
    );

    const result = await response.json();

    if (result.success) {
        alert("Product updated.");
    } else {
        alert(result.message || "Unable to update product.");
    }
}


async function deleteProduct(id) {

    if (!confirm("Delete this product?")) {
        return;
    }

    const response = await fetch(
        "/api/products/" + id,
        {
            method:"DELETE"
        }
    );

    const result = await response.json();

    if (result.success) {
        location.reload();
    } else {
        alert(result.message || "Unable to delete product.");
    }
}


async function clearVisitors() {

    if (!confirm("Delete all visitor logs?")) {
        return;
    }

    const response = await fetch(
        "/api/visitors/clear",
        {
            method:"POST"
        }
    );

    const result = await response.json();

    if (result.success) {
        location.reload();
    }
}

</script>

</body>
</html>
"""


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return """
    <div style="font-family:Arial;text-align:center;padding:80px">
        <h1>404</h1>
        <p>Page not found.</p>
        <a href="/">Return to PADRON</a>
    </div>
    """, 404


@app.errorhandler(500)
def server_error(error):
    return """
    <div style="font-family:Arial;text-align:center;padding:80px">
        <h1>Something went wrong.</h1>
        <p>Please try again.</p>
        <a href="/">Return to PADRON</a>
    </div>
    """, 500


# ============================================================
# RUN LOCALLY
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
