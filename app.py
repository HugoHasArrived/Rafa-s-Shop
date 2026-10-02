import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
    flash,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

DB_PATH = os.environ.get("DATABASE_PATH", "rafa_store.db")

STORE_NAME = "Rafa's Store"
STORE_ADDRESS = "268 A. Mabini Street, Liliw, Laguna"
STORE_PHONE = "0976 1296450"

# Staff credentials.
# For production, set STAFF_USERNAME and STAFF_PASSWORD as Render environment variables.
STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "staff")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "change-me")


# -------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            image TEXT DEFAULT '',
            category TEXT DEFAULT 'Slippers',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            device TEXT,
            language TEXT,
            visited_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    existing = conn.execute(
        "SELECT COUNT(*) AS count FROM products"
    ).fetchone()["count"]

    if existing == 0:
        sample_products = [
            (
                "Classic Filipino Slippers",
                "Comfortable everyday slippers.",
                299,
                15,
                "",
                "Slippers",
            ),
            (
                "Handcrafted Brown Slippers",
                "A simple handcrafted Filipino-inspired design.",
                399,
                10,
                "",
                "Handcrafted",
            ),
            (
                "Premium Comfort Slippers",
                "Soft and comfortable slippers for everyday use.",
                499,
                8,
                "",
                "Premium",
            ),
        ]

        conn.executemany("""
            INSERT INTO products
            (name, description, price, stock, image, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_products)

    conn.commit()
    conn.close()


init_db()


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def staff_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in"):
            return redirect(url_for("staff_login"))
        return func(*args, **kwargs)

    return wrapper


def detect_device(user_agent):
    ua = (user_agent or "").lower()

    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "Mobile"

    if "tablet" in ua or "ipad" in ua:
        return "Tablet"

    return "Desktop"


def record_visitor():
    # Do not store visitor information when staff is browsing the dashboard.
    if session.get("staff_logged_in"):
        return

    user_agent = request.headers.get("User-Agent", "")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    # If Render/proxy gives multiple forwarded IPs, use the first one.
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    device = detect_device(user_agent)
    language = request.headers.get("Accept-Language", "")

    conn = get_db()
    conn.execute("""
        INSERT INTO visitors
        (ip, user_agent, device, language, visited_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        ip,
        user_agent,
        device,
        language,
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()
    conn.close()


# -------------------------------------------------------------------
# STYLING
# -------------------------------------------------------------------

CSS = """
:root {
    --bg: #f7f1e8;
    --bg-secondary: #efe2d1;
    --card: #fffaf3;
    --brown: #a67c52;
    --brown-dark: #6f4e37;
    --brown-light: #c8a27a;
    --text: #3e2c1c;
    --muted: #796956;
    --border: #decbb5;
    --white: #ffffff;
    --danger: #a94442;
    --success: #537a55;
    --shadow: 0 12px 35px rgba(92, 65, 42, 0.12);
}

body.dark {
    --bg: #211a15;
    --bg-secondary: #2a211b;
    --card: #30251e;
    --brown: #c8a27a;
    --brown-dark: #e0bc91;
    --brown-light: #a67c52;
    --text: #f6ecdf;
    --muted: #c8b7a5;
    --border: #574536;
    --white: #ffffff;
    --shadow: 0 12px 35px rgba(0,0,0,.3);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    font-family: Inter, Arial, Helvetica, sans-serif;
    background:
        radial-gradient(circle at top left, rgba(200,162,122,.18), transparent 30%),
        var(--bg);
    color: var(--text);
    transition: background .25s, color .25s;
}

a {
    color: inherit;
    text-decoration: none;
}

button,
input,
textarea,
select {
    font: inherit;
}

button {
    cursor: pointer;
}

.navbar {
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(14px);
    background: rgba(255,250,243,.88);
    border-bottom: 1px solid var(--border);
}

body.dark .navbar {
    background: rgba(33,26,21,.9);
}

.nav-inner {
    max-width: 1200px;
    margin: auto;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.logo-area {
    display: flex;
    align-items: center;
    gap: 12px;
}

.logo {
    height: 54px;
    width: auto;
    object-fit: contain;
}

.brand-image {
    max-width: 150px;
    max-height: 48px;
    object-fit: contain;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.nav-links a,
.nav-button {
    border: 0;
    background: transparent;
    color: var(--text);
    padding: 9px 13px;
    border-radius: 10px;
    font-weight: 600;
}

.nav-links a:hover,
.nav-button:hover {
    background: var(--bg-secondary);
}

.container {
    max-width: 1200px;
    margin: auto;
    padding: 30px 22px;
}

.hero {
    min-height: 520px;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 70px 20px;
}

.hero-content {
    max-width: 800px;
}

.hero h1 {
    font-size: clamp(42px, 8vw, 78px);
    line-height: .95;
    margin: 15px 0;
    color: var(--brown-dark);
}

.hero p {
    font-size: 19px;
    line-height: 1.7;
    color: var(--muted);
}

.badge {
    display: inline-block;
    background: var(--brown-light);
    color: #fff;
    padding: 8px 15px;
    border-radius: 999px;
    font-weight: 700;
}

.btn {
    display: inline-block;
    border: 0;
    padding: 12px 20px;
    border-radius: 12px;
    background: var(--brown);
    color: white;
    font-weight: 700;
    box-shadow: var(--shadow);
    transition: transform .15s, opacity .15s;
}

.btn:hover {
    transform: translateY(-2px);
    opacity: .92;
}

.btn.secondary {
    background: var(--brown-dark);
}

.btn.danger {
    background: var(--danger);
}

.section {
    padding: 55px 0;
}

.section-title {
    text-align: center;
    margin-bottom: 30px;
}

.section-title h2 {
    font-size: 34px;
    margin-bottom: 8px;
    color: var(--brown-dark);
}

.section-title p {
    color: var(--muted);
}

.products {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 22px;
}

.product {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: var(--shadow);
    transition: transform .2s;
}

.product:hover {
    transform: translateY(-6px);
}

.product-image {
    width: 100%;
    height: 210px;
    object-fit: cover;
    background: var(--bg-secondary);
}

.product-placeholder {
    height: 210px;
    display: grid;
    place-items: center;
    background:
        linear-gradient(135deg, var(--bg-secondary), var(--card));
    color: var(--brown);
    font-size: 54px;
}

.product-body {
    padding: 20px;
}

.product h3 {
    margin-top: 0;
}

.price {
    color: var(--brown-dark);
    font-size: 22px;
    font-weight: 800;
}

.stock {
    color: var(--muted);
    margin: 8px 0 15px;
}

.about-box {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 30px;
    box-shadow: var(--shadow);
    line-height: 1.8;
}

.about-box h3 {
    color: var(--brown-dark);
}

.footer {
    margin-top: 70px;
    padding: 45px 22px;
    background: var(--brown-dark);
    color: #fff;
}

.footer-inner {
    max-width: 1200px;
    margin: auto;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 30px;
}

.footer h3 {
    color: #f1d4b1;
}

.footer p {
    color: #eadbca;
    line-height: 1.7;
}

.form-card {
    max-width: 700px;
    margin: 40px auto;
    background: var(--card);
    border: 1px solid var(--border);
    padding: 30px;
    border-radius: 20px;
    box-shadow: var(--shadow);
}

.form-group {
    margin-bottom: 17px;
}

.form-group label {
    display: block;
    margin-bottom: 7px;
    font-weight: 700;
}

.form-group input,
.form-group textarea,
.form-group select {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    background: var(--bg);
    color: var(--text);
    outline: none;
}

.form-group textarea {
    min-height: 110px;
    resize: vertical;
}

.flash {
    max-width: 1200px;
    margin: 20px auto;
    padding: 13px 18px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 18px;
    margin-bottom: 30px;
}

.stat {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 24px;
    box-shadow: var(--shadow);
}

.stat-number {
    font-size: 35px;
    font-weight: 900;
    color: var(--brown);
}

.table-wrap {
    overflow-x: auto;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 18px;
    box-shadow: var(--shadow);
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    padding: 14px;
    text-align: left;
    border-bottom: 1px solid var(--border);
}

th {
    background: var(--bg-secondary);
}

@media (max-width: 700px) {
    .nav-inner {
        flex-direction: column;
    }

    .hero {
        min-height: 430px;
    }

    .hero h1 {
        font-size: 48px;
    }
}
"""


# -------------------------------------------------------------------
# MAIN PAGE
# -------------------------------------------------------------------

PAGE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>{{ store_name }}</title>

    <style>{{ css|safe }}</style>
</head>

<body>

<nav class="navbar">
    <div class="nav-inner">

        <div class="logo-area">
            <img
                class="logo"
                src="{{ url_for('static', filename='image0 (3)') }}"
                alt="Logo"
                onerror="this.style.display='none'"
            >

            <img
                class="brand-image"
                src="{{ url_for('static', filename='image1') }}"
                alt="{{ store_name }}"
                onerror="this.style.display='none'"
            >
        </div>

        <div class="nav-links">
            <a href="#home" data-en="Home" data-fil="Home">Home</a>
            <a href="#products" data-en="Products" data-fil="Mga Produkto">Products</a>
            <a href="#about" data-en="About Us" data-fil="Tungkol sa Amin">About Us</a>
            <a href="#contact" data-en="Contact" data-fil="Kontak">Contact</a>

            <button class="nav-button" onclick="toggleLanguage()">
                <span id="languageLabel">FIL</span>
            </button>

            <button class="nav-button" onclick="toggleTheme()">
                ☀️ / 🌙
            </button>

            <a href="{{ url_for('staff_login') }}">Staff</a>
        </div>

    </div>
</nav>


{% with messages = get_flashed_messages() %}
    {% if messages %}
        {% for message in messages %}
            <div class="flash">{{ message }}</div>
        {% endfor %}
    {% endif %}
{% endwith %}


<main>

<section class="hero" id="home">
    <div class="hero-content">

        <span class="badge"
              data-en="Handcrafted Filipino Footwear"
              data-fil="Gawang Pilipinong Sapatos">
            Handcrafted Filipino Footwear
        </span>

        <h1>{{ store_name }}</h1>

        <p
            data-en="Beautiful, comfortable and proudly Filipino footwear."
            data-fil="Maganda, komportable at ipinagmamalaking gawang Pilipino na sapatos."
        >
            Beautiful, comfortable and proudly Filipino footwear.
        </p>

        <a class="btn" href="#products"
           data-en="Explore Products"
           data-fil="Tingnan ang Mga Produkto">
            Explore Products
        </a>

    </div>
</section>


<section class="section" id="products">
    <div class="container">

        <div class="section-title">
            <h2 data-en="Our Products" data-fil="Mga Produkto">
                Our Products
            </h2>

            <p
                data-en="Browse our available footwear collection."
                data-fil="Tingnan ang aming mga available na footwear."
            >
                Browse our available footwear collection.
            </p>
        </div>

        <div class="products">

            {% for product in products %}

            <article class="product">

                {% if product["image"] %}
                    <img
                        class="product-image"
                        src="{{ product['image'] }}"
                        alt="{{ product['name'] }}"
                    >
                {% else %}
                    <div class="product-placeholder">
                        🥿
                    </div>
                {% endif %}

                <div class="product-body">

                    <h3>{{ product["name"] }}</h3>

                    <p>{{ product["description"] }}</p>

                    <div class="price">
                        ₱{{ "%.2f"|format(product["price"]) }}
                    </div>

                    <div class="stock">
                        {% if product["stock"] > 0 %}
                            <span
                                data-en="{{ product['stock'] }} in stock"
                                data-fil="{{ product['stock'] }} available"
                            >
                                {{ product["stock"] }} in stock
                            </span>
                        {% else %}
                            <span
                                data-en="Out of stock"
                                data-fil="Walang stock"
                            >
                                Out of stock
                            </span>
                        {% endif %}
                    </div>

                </div>

            </article>

            {% endfor %}

        </div>
    </div>
</section>


<section class="section" id="about">
    <div class="container">

        <div class="section-title">
            <h2 data-en="About Us" data-fil="Tungkol sa Amin">
                About Us
            </h2>
        </div>

        <div class="about-box">

            <h3>Golden Zapatillas Corporation</h3>

            <p>
                Golden Zapatillas Corporation is a family-owned business
                established in 2015, continuing a family tradition of
                manufacturing high-quality footwear in Liliw, Laguna.
            </p>

            <p>
                Our main goal is to create pairs of shoes that showcase
                the creativity and craftsmanship of our artisans:
                artist painters, beadworkers, embroiderers and shoemakers
                from Laguna.
            </p>

            <p>
                We use locally sourced materials like abaca and indigenous
                fabrics such as Ifugao fabric and Inabel to support local
                suppliers and create a Filipino touch in footwear that is
                world-class in quality and durability.
            </p>

            <h3>Padron</h3>

            <p>
                Padron is the brand name we are known for. The name means
                "pattern" in Spanish because every footwear design starts
                with creating a padron or pattern.
            </p>

            <h3 data-en="Our Products" data-fil="Mga Produkto">
                Our Products
            </h3>

            <p>
                Padron is committed to quality, heritage, sustainability
                and women empowerment. We offer handmade mules, flats,
                platforms and wedge espadrilles showcasing the skills of
                Laguna artisans.
            </p>

            <p>
                We use materials such as abaca, Ifugao fabric and Inabel
                to support local suppliers. We continually innovate our
                designs, including the Estela interchangeable strap.
            </p>

            <h3>Mission</h3>

            <p>
                To empower Filipino artisans, including shoemakers and
                women artisans skilled in handpainting, embroidery and
                crochet, by creating sustainable, high-quality footwear
                that celebrates local heritage and craftsmanship.
            </p>

            <h3>Vision</h3>

            <p>
                To be one of the leading pioneers in sustainable,
                handcrafted footwear, incorporating the expertise of
                shoemakers and women artisans while preserving the
                family's legacy and positioning Liliw as a center of
                footwear excellence.
            </p>

        </div>

    </div>
</section>

</main>


<footer class="footer" id="contact">
    <div class="footer-inner">

        <div>
            <h3>{{ store_name }}</h3>
            <p>
                Proudly supporting Filipino craftsmanship and local
                footwear traditions.
            </p>
        </div>

        <div>
            <h3 data-en="Address" data-fil="Address">
                Address
            </h3>

            <p>{{ store_address }}</p>
        </div>

        <div>
            <h3 data-en="Contact" data-fil="Kontak">
                Contact
            </h3>

            <p>{{ store_phone }}</p>
        </div>

    </div>
</footer>


<script>

let language = localStorage.getItem("rafaLanguage") || "en";

function updateLanguage() {

    document.querySelectorAll("[data-en]").forEach(function(element) {

        const value =
            language === "en"
                ? element.getAttribute("data-en")
                : element.getAttribute("data-fil");

        if (value) {
            element.textContent = value;
        }

    });

    document.getElementById("languageLabel").textContent =
        language === "en" ? "FIL" : "ENG";

    localStorage.setItem("rafaLanguage", language);
}

function toggleLanguage() {

    language = language === "en"
        ? "fil"
        : "en";

    updateLanguage();
}


function toggleTheme() {

    document.body.classList.toggle("dark");

    localStorage.setItem(
        "rafaTheme",
        document.body.classList.contains("dark")
            ? "dark"
            : "light"
    );
}


if (localStorage.getItem("rafaTheme") === "dark") {
    document.body.classList.add("dark");
}

updateLanguage();

</script>

</body>
</html>
"""


# -------------------------------------------------------------------
# STAFF LOGIN
# -------------------------------------------------------------------

LOGIN_PAGE = """
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Staff Login - {{ store_name }}</title>
    <style>{{ css|safe }}</style>
</head>

<body>

<div class="form-card">

    <h1>{{ store_name }}</h1>

    <h2>Staff Login</h2>

    {% with messages = get_flashed_messages() %}
        {% for message in messages %}
            <div class="flash">{{ message }}</div>
        {% endfor %}
    {% endwith %}

    <form method="POST">

        <div class="form-group">
            <label>Username</label>
            <input name="username" required autocomplete="username">
        </div>

        <div class="form-group">
            <label>Password</label>
            <input
                type="password"
                name="password"
                required
                autocomplete="current-password"
            >
        </div>

        <button class="btn" type="submit">
            Login
        </button>

        <a class="btn secondary" href="{{ url_for('index') }}">
            Back
        </a>

    </form>

</div>

</body>
</html>
"""


# -------------------------------------------------------------------
# STAFF DASHBOARD
# -------------------------------------------------------------------

DASHBOARD_PAGE = """
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Staff Dashboard - {{ store_name }}</title>
    <style>{{ css|safe }}</style>
</head>

<body>

<nav class="navbar">
    <div class="nav-inner">
        <strong>{{ store_name }} Staff</strong>

        <div class="nav-links">
            <a href="{{ url_for('index') }}">Store</a>
            <a href="{{ url_for('add_product') }}">Add Product</a>
            <a href="{{ url_for('staff_logout') }}">Logout</a>
        </div>
    </div>
</nav>


<div class="container">

    {% with messages = get_flashed_messages() %}
        {% for message in messages %}
            <div class="flash">{{ message }}</div>
        {% endfor %}
    {% endwith %}


    <h1>Staff Dashboard</h1>

    <div class="dashboard-grid">

        <div class="stat">
            <div>Products</div>
            <div class="stat-number">{{ product_count }}</div>
        </div>

        <div class="stat">
            <div>Total Stock</div>
            <div class="stat-number">{{ total_stock }}</div>
        </div>

        <div class="stat">
            <div>Visitors</div>
            <div class="stat-number">{{ visitor_count }}</div>
        </div>

    </div>


    <h2>Products</h2>

    <div class="table-wrap">

        <table>

            <thead>
                <tr>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Price</th>
                    <th>Stock</th>
                    <th>Action</th>
                </tr>
            </thead>

            <tbody>

                {% for product in products %}

                <tr>
                    <td>{{ product["name"] }}</td>
                    <td>{{ product["category"] }}</td>
                    <td>₱{{ "%.2f"|format(product["price"]) }}</td>
                    <td>{{ product["stock"] }}</td>

                    <td>
                        <a
                            class="btn"
                            href="{{ url_for('edit_product', product_id=product['id']) }}"
                        >
                            Edit
                        </a>

                        <form
                            method="POST"
                            action="{{ url_for('delete_product', product_id=product['id']) }}"
                            style="display:inline"
                            onsubmit="return confirm('Delete this product?')"
                        >
                            <button class="btn danger" type="submit">
                                Delete
                            </button>
                        </form>
                    </td>

                </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>


    <h2 style="margin-top:50px">
        Visitor Information
    </h2>

    <p>
        Visitor records are available only to logged-in staff.
    </p>

    <div class="table-wrap">

        <table>

            <thead>
                <tr>
                    <th>Date</th>
                    <th>IP</th>
                    <th>Device</th>
                    <th>Language</th>
                    <th>User Agent</th>
                </tr>
            </thead>

            <tbody>

                {% for visitor in visitors %}

                <tr>
                    <td>{{ visitor["visited_at"] }}</td>
                    <td>{{ visitor["ip"] }}</td>
                    <td>{{ visitor["device"] }}</td>
                    <td>{{ visitor["language"] }}</td>
                    <td style="max-width:400px;word-break:break-word">
                        {{ visitor["user_agent"] }}
                    </td>
                </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>

</body>
</html>
"""


# -------------------------------------------------------------------
# PRODUCT FORM
# -------------------------------------------------------------------

PRODUCT_FORM = """
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} - {{ store_name }}</title>
    <style>{{ css|safe }}</style>
</head>

<body>

<div class="form-card">

    <h1>{{ title }}</h1>

    <form method="POST">

        <div class="form-group">
            <label>Product Name</label>
            <input
                name="name"
                value="{{ product['name'] if product else '' }}"
                required
            >
        </div>

        <div class="form-group">
            <label>Description</label>
            <textarea name="description">{{ product['description'] if product else '' }}</textarea>
        </div>

        <div class="form-group">
            <label>Price (₱)</label>
            <input
                type="number"
                step="0.01"
                min="0"
                name="price"
                value="{{ product['price'] if product else 0 }}"
                required
            >
        </div>

        <div class="form-group">
            <label>Stock</label>
            <input
                type="number"
                min="0"
                name="stock"
                value="{{ product['stock'] if product else 0 }}"
                required
            >
        </div>

        <div class="form-group">
            <label>Category</label>

            <select name="category">
                {% for category in ["Slippers", "Handcrafted", "Premium", "New", "Sale"] %}
                    <option
                        value="{{ category }}"
                        {% if product and product['category'] == category %}
                            selected
                        {% endif %}
                    >
                        {{ category }}
                    </option>
                {% endfor %}
            </select>

        </div>

        <div class="form-group">
            <label>Image URL</label>
            <input
                name="image"
                value="{{ product['image'] if product else '' }}"
                placeholder="Optional image URL"
            >
        </div>

        <button class="btn" type="submit">
            Save
        </button>

        <a class="btn secondary" href="{{ url_for('dashboard') }}">
            Cancel
        </a>

    </form>

</div>

</body>
</html>
"""


# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------

@app.route("/")
def index():

    record_visitor()

    conn = get_db()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template_string(
        PAGE,
        css=CSS,
        products=products,
        store_name=STORE_NAME,
        store_address=STORE_ADDRESS,
        store_phone=STORE_PHONE,
    )


@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == STAFF_USERNAME
            and password == STAFF_PASSWORD
        ):
            session["staff_logged_in"] = True
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template_string(
        LOGIN_PAGE,
        css=CSS,
        store_name=STORE_NAME,
    )


@app.route("/staff/logout")
def staff_logout():

    session.pop("staff_logged_in", None)

    return redirect(url_for("index"))


@app.route("/staff")
@staff_required
def dashboard():

    conn = get_db()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    product_count = conn.execute(
        "SELECT COUNT(*) AS count FROM products"
    ).fetchone()["count"]

    total_stock = conn.execute(
        "SELECT COALESCE(SUM(stock), 0) AS total FROM products"
    ).fetchone()["total"]

    visitor_count = conn.execute(
        "SELECT COUNT(*) AS count FROM visitors"
    ).fetchone()["count"]

    visitors = conn.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 500
    """).fetchall()

    conn.close()

    return render_template_string(
        DASHBOARD_PAGE,
        css=CSS,
        store_name=STORE_NAME,
        products=products,
        product_count=product_count,
        total_stock=total_stock,
        visitor_count=visitor_count,
        visitors=visitors,
    )


@app.route("/staff/product/add", methods=["GET", "POST"])
@staff_required
def add_product():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Slippers").strip()
        image = request.form.get("image", "").strip()

        try:
            price = float(request.form.get("price", 0))
            stock = int(request.form.get("stock", 0))
        except ValueError:
            flash("Price and stock must contain valid numbers.")
            return redirect(url_for("add_product"))

        if not name:
            flash("Product name is required.")
            return redirect(url_for("add_product"))

        if price < 0 or stock < 0:
            flash("Price and stock cannot be negative.")
            return redirect(url_for("add_product"))

        conn = get_db()

        conn.execute("""
            INSERT INTO products
            (name, description, price, stock, image, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            description,
            price,
            stock,
            image,
            category,
        ))

        conn.commit()
        conn.close()

        flash("Product added successfully.")

        return redirect(url_for("dashboard"))

    return render_template_string(
        PRODUCT_FORM,
        css=CSS,
        store_name=STORE_NAME,
        title="Add Product",
        product=None,
    )


@app.route("/staff/product/<int:product_id>/edit", methods=["GET", "POST"])
@staff_required
def edit_product(product_id):

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        flash("Product not found.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Slippers").strip()
        image = request.form.get("image", "").strip()

        try:
            price = float(request.form.get("price", 0))
            stock = int(request.form.get("stock", 0))
        except ValueError:
            conn.close()
            flash("Price and stock must contain valid numbers.")
            return redirect(
                url_for("edit_product", product_id=product_id)
            )

        if not name:
            conn.close()
            flash("Product name is required.")
            return redirect(
                url_for("edit_product", product_id=product_id)
            )

        if price < 0 or stock < 0:
            conn.close()
            flash("Price and stock cannot be negative.")
            return redirect(
                url_for("edit_product", product_id=product_id)
            )

        conn.execute("""
            UPDATE products
            SET
                name = ?,
                description = ?,
                price = ?,
                stock = ?,
                image = ?,
                category = ?
            WHERE id = ?
        """, (
            name,
            description,
            price,
            stock,
            image,
            category,
            product_id,
        ))

        conn.commit()
        conn.close()

        flash("Product updated successfully.")

        return redirect(url_for("dashboard"))

    conn.close()

    return render_template_string(
        PRODUCT_FORM,
        css=CSS,
        store_name=STORE_NAME,
        title="Edit Product",
        product=product,
    )


@app.route("/staff/product/<int:product_id>/delete", methods=["POST"])
@staff_required
def delete_product(product_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()
    conn.close()

    flash("Product deleted.")

    return redirect(url_for("dashboard"))


# -------------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------------

@app.route("/health")
def health():
    return {
        "status": "ok",
        "store": STORE_NAME,
    }


# -------------------------------------------------------------------
# RUN
# -------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
