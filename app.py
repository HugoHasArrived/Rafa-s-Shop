import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask,
    request,
    redirect,
    session,
    flash,
    render_template_string,
    url_for,
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

app.secret_key = os.getenv(
    "SECRET_KEY",
    "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
)

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

STAFF_PASSWORD = os.getenv(
    "STAFF_PASSWORD",
    "CHANGE_THIS_STAFF_PASSWORD"
)

IP_HASH_SALT = os.getenv(
    "IP_HASH_SALT",
    "CHANGE_THIS_IP_SALT"
)

DATABASE = os.getenv(
    "DATABASE_PATH",
    "store.db"
)


# ============================================================
# DATABASE
# ============================================================

def db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = db()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            sizes TEXT DEFAULT '',
            color TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT,
            device TEXT DEFAULT 'Unknown',
            browser TEXT DEFAULT 'Unknown',
            user_agent TEXT DEFAULT '',
            visited_at TEXT NOT NULL
        );
        """
    )

    product_count = connection.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if product_count == 0:
        sample_products = [
            (
                "Purple Cloud Slides",
                "Soft cushioned slippers for everyday comfort.",
                399,
                25,
                "36,37,38,39,40,41,42",
                "Purple",
                ""
            ),
            (
                "Lavender Comfort",
                "Lightweight slippers with a soft comfortable sole.",
                349,
                18,
                "36,37,38,39,40",
                "Lavender",
                ""
            ),
            (
                "Midnight Purple",
                "Simple, durable slippers for everyday use.",
                449,
                12,
                "38,39,40,41,42,43",
                "Dark Purple",
                ""
            )
        ]

        for product in sample_products:
            connection.execute(
                """
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
                """,
                (
                    *product,
                    datetime.now(timezone.utc).isoformat()
                )
            )

    connection.commit()
    connection.close()


# ============================================================
# PRIVACY-FRIENDLY VISITOR ANALYTICS
# ============================================================

def get_ip_hash():
    ip = request.remote_addr or "unknown"

    return hashlib.sha256(
        f"{IP_HASH_SALT}:{ip}".encode("utf-8")
    ).hexdigest()[:32]


def get_device(user_agent):
    ua = user_agent.lower()

    if "ipad" in ua or "tablet" in ua:
        return "Tablet"

    if "iphone" in ua:
        return "iPhone"

    if "android" in ua:
        return "Android"

    if "windows" in ua:
        return "Windows PC"

    if "macintosh" in ua or "mac os" in ua:
        return "Mac"

    if "linux" in ua:
        return "Linux"

    return "Unknown"


def get_browser(user_agent):
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

    return "Unknown"


def record_visitor():
    user_agent = request.headers.get("User-Agent", "")

    connection = db()

    connection.execute(
        """
        INSERT INTO visitors
        (
            ip_hash,
            device,
            browser,
            user_agent,
            visited_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            get_ip_hash(),
            get_device(user_agent),
            get_browser(user_agent),
            user_agent[:500],
            datetime.now(timezone.utc).isoformat()
        )
    )

    connection.commit()
    connection.close()


# ============================================================
# STAFF AUTHENTICATION
# ============================================================

def staff_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("staff"):
            return redirect("/staff/login")

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# HTML / CSS
# ============================================================

STYLE = """
<style>

:root {
    --purple: #7c3aed;
    --purple-dark: #4c1d95;
    --purple-light: #a78bfa;
    --purple-pale: #f5f3ff;
    --white: #ffffff;
    --text: #24143d;
    --muted: #746b82;
    --border: #e9ddff;
    --green: #16a34a;
    --red: #dc2626;
    --shadow: 0 12px 35px rgba(76, 29, 149, .12);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    background:
        radial-gradient(
            circle at top right,
            #ede9fe 0,
            #faf8ff 35%,
            #ffffff 70%
        );
    color: var(--text);
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
    z-index: 20;
    background: rgba(255,255,255,.9);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
}

.nav-inner {
    max-width: 1150px;
    margin: auto;
    padding: 17px 22px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

.logo {
    font-size: 23px;
    font-weight: 900;
    color: var(--purple-dark);
}

.logo span {
    color: var(--purple);
}

.nav-links {
    display: flex;
    gap: 18px;
    align-items: center;
}

.nav-links a {
    color: #5b5268;
    font-weight: 700;
}

.nav-links a:hover {
    color: var(--purple);
}

.btn {
    border: 0;
    border-radius: 12px;
    padding: 11px 17px;
    font-weight: 800;
    transition: .2s;
    display: inline-block;
}

.btn:hover {
    transform: translateY(-1px);
}

.btn-purple {
    color: white;
    background: linear-gradient(
        135deg,
        var(--purple),
        var(--purple-dark)
    );
    box-shadow: 0 8px 20px rgba(124,58,237,.25);
}

.btn-light {
    background: var(--purple-pale);
    color: var(--purple-dark);
}

.btn-danger {
    background: #fee2e2;
    color: var(--red);
}

.container {
    max-width: 1150px;
    margin: auto;
    padding: 0 22px;
}

.hero {
    padding: 90px 0 70px;
}

.hero-box {
    border-radius: 30px;
    padding: 65px 45px;
    overflow: hidden;
    position: relative;
    background:
        radial-gradient(
            circle at 90% 10%,
            rgba(255,255,255,.3),
            transparent 35%
        ),
        linear-gradient(
            135deg,
            #6d28d9,
            #4c1d95
        );
    color: white;
    box-shadow: 0 25px 60px rgba(76,29,149,.25);
}

.hero-box:after {
    content: "";
    position: absolute;
    width: 240px;
    height: 240px;
    border-radius: 50%;
    right: -70px;
    bottom: -100px;
    background: rgba(255,255,255,.1);
}

.hero h1 {
    margin: 0 0 15px;
    max-width: 650px;
    font-size: clamp(40px, 7vw, 70px);
    line-height: .98;
}

.hero p {
    max-width: 610px;
    font-size: 18px;
    line-height: 1.7;
    color: #ede9fe;
}

.section {
    padding: 30px 0 80px;
}

.section-title {
    font-size: 32px;
    margin-bottom: 25px;
}

.products {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(245px, 1fr));
    gap: 22px;
}

.card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 22px;
    overflow: hidden;
    box-shadow: var(--shadow);
    transition: .2s;
}

.card:hover {
    transform: translateY(-4px);
}

.product-image {
    height: 205px;
    display: flex;
    justify-content: center;
    align-items: center;
    background:
        linear-gradient(
            135deg,
            #f5f3ff,
            #ede9fe
        );
    overflow: hidden;
}

.product-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.slipper-icon {
    font-size: 80px;
}

.card-body {
    padding: 20px;
}

.card h3 {
    margin: 0 0 8px;
    font-size: 20px;
}

.description {
    color: var(--muted);
    line-height: 1.55;
    min-height: 48px;
}

.price {
    color: var(--purple);
    font-size: 25px;
    font-weight: 900;
    margin: 15px 0 7px;
}

.stock {
    font-size: 13px;
    font-weight: 800;
}

.stock-good {
    color: var(--green);
}

.stock-low {
    color: #ca8a04;
}

.stock-out {
    color: var(--red);
}

.info-line {
    color: var(--muted);
    font-size: 14px;
    margin: 7px 0;
}

.footer {
    margin-top: 40px;
    padding: 50px 22px;
    background: #211036;
    color: #ddd1ed;
}

.footer-inner {
    max-width: 1150px;
    margin: auto;
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(220px, 1fr));
    gap: 35px;
}

.footer h3 {
    color: white;
    margin-top: 0;
}

.footer-bottom {
    max-width: 1150px;
    margin: 35px auto 0;
    padding-top: 20px;
    border-top: 1px solid rgba(255,255,255,.1);
    font-size: 13px;
}

.login-wrap {
    min-height: 75vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 50px 20px;
}

.login-card {
    width: 100%;
    max-width: 430px;
    background: white;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 35px;
    box-shadow: var(--shadow);
}

.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    font-weight: 800;
    margin-bottom: 7px;
}

.form-group input,
.form-group textarea,
.form-group select {
    width: 100%;
    border: 1px solid #ddd2eb;
    border-radius: 11px;
    padding: 12px;
    outline: none;
    background: white;
}

.form-group input:focus,
.form-group textarea:focus {
    border-color: var(--purple);
    box-shadow: 0 0 0 3px #ede9fe;
}

textarea {
    min-height: 90px;
    resize: vertical;
}

.dashboard {
    padding: 45px 0 80px;
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    margin-bottom: 30px;
}

.stats {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
}

.stat {
    background: white;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 22px;
    box-shadow: var(--shadow);
}

.stat-number {
    font-size: 32px;
    font-weight: 900;
    color: var(--purple);
}

.stat-label {
    color: var(--muted);
    margin-top: 4px;
}

.panel {
    background: white;
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 25px;
    margin-bottom: 25px;
    box-shadow: var(--shadow);
}

.panel h2 {
    margin-top: 0;
}

.product-editor {
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px;
    margin: 15px 0;
    background: #fcfbff;
}

.grid-form {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
}

.grid-form .full {
    grid-column: 1 / -1;
}

.table-wrap {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 720px;
}

th,
td {
    padding: 12px 10px;
    text-align: left;
    border-bottom: 1px solid #eee7f6;
    font-size: 13px;
}

th {
    color: var(--purple-dark);
    background: #faf8ff;
}

.alert {
    max-width: 1150px;
    margin: 15px auto 0;
    padding: 13px 18px;
    border-radius: 12px;
    background: #ede9fe;
    color: var(--purple-dark);
}

.empty {
    text-align: center;
    padding: 50px;
    color: var(--muted);
}

@media (max-width: 700px) {

    .nav-inner {
        flex-direction: column;
    }

    .hero {
        padding-top: 35px;
    }

    .hero-box {
        padding: 40px 25px;
        border-radius: 22px;
    }

    .hero h1 {
        font-size: 45px;
    }

    .dashboard-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .nav-links {
        flex-wrap: wrap;
        justify-content: center;
    }
}

</style>
"""


# ============================================================
# MAIN STORE PAGE
# ============================================================

HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>{{ store_name }} | Philippine Slippers</title>
    {{ style|safe }}
</head>

<body>

<nav class="navbar">
    <div class="nav-inner">

        <a class="logo" href="/">
            Rafa<span>'s</span> Store
        </a>

        <div class="nav-links">
            <a href="#shop">Shop</a>
            <a href="#contact">Contact</a>
            <a class="btn btn-light" href="/staff/login">
                Staff
            </a>
        </div>

    </div>
</nav>

{% with messages = get_flashed_messages() %}
    {% if messages %}
        {% for message in messages %}
            <div class="alert">
                {{ message }}
            </div>
        {% endfor %}
    {% endif %}
{% endwith %}

<main>

<section class="hero">
    <div class="container">

        <div class="hero-box">

            <div style="position:relative;z-index:2">

                <div style="
                    font-weight:800;
                    color:#ddd6fe;
                    margin-bottom:12px;
                ">
                    🇵🇭 Made for everyday comfort
                </div>

                <h1>
                    Step into comfort.
                </h1>

                <p>
                    Discover comfortable, stylish slippers from
                    Rafa's Store. Browse our current collection
                    and find your next favorite pair.
                </p>

                <a
                    class="btn"
                    href="#shop"
                    style="
                        background:white;
                        color:#4c1d95;
                        margin-top:10px;
                    "
                >
                    Shop Slippers
                </a>

            </div>

        </div>

    </div>
</section>


<section class="section" id="shop">

    <div class="container">

        <h2 class="section-title">
            Our Slippers
        </h2>

        {% if products %}

        <div class="products">

            {% for product in products %}

            <article class="card">

                <div class="product-image">

                    {% if product["image_url"] %}

                    <img
                        src="{{ product['image_url'] }}"
                        alt="{{ product['name'] }}"
                    >

                    {% else %}

                    <div class="slipper-icon">
                        🩴
                    </div>

                    {% endif %}

                </div>

                <div class="card-body">

                    <h3>
                        {{ product["name"] }}
                    </h3>

                    <div class="description">
                        {{ product["description"] }}
                    </div>

                    <div class="price">
                        ₱{{ "%.2f"|format(product["price"]) }}
                    </div>

                    <div class="info-line">
                        <strong>Color:</strong>
                        {{ product["color"] or "Various" }}
                    </div>

                    <div class="info-line">
                        <strong>Sizes:</strong>
                        {{ product["sizes"] or "Various" }}
                    </div>

                    {% if product["stock"] <= 0 %}

                        <div class="stock stock-out">
                            Out of stock
                        </div>

                    {% elif product["stock"] <= 5 %}

                        <div class="stock stock-low">
                            Only {{ product["stock"] }} left
                        </div>

                    {% else %}

                        <div class="stock stock-good">
                            In stock
                        </div>

                    {% endif %}

                </div>

            </article>

            {% endfor %}

        </div>

        {% else %}

        <div class="panel empty">
            No slippers are currently available.
        </div>

        {% endif %}

    </div>

</section>

</main>


<footer class="footer" id="contact">

    <div class="footer-inner">

        <div>
            <h3>Rafa's Store</h3>
            <p>
                Comfortable slippers for everyday life.
            </p>
        </div>

        <div>
            <h3>Contact</h3>

            <p>
                {{ store_address }}
            </p>

            <p>
                {{ store_phone }}
            </p>

            <p>
                {{ store_email }}
            </p>
        </div>

    </div>

    <div class="footer-bottom">
        © {{ year }} Rafa's Store · Philippines
    </div>

</footer>

</body>
</html>
"""


# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN_HTML = """
<!doctype html>
<html lang="en">
<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Staff Login | {{ store_name }}</title>

{{ style|safe }}

</head>

<body>

<nav class="navbar">

    <div class="nav-inner">

        <a class="logo" href="/">
            Rafa<span>'s</span> Store
        </a>

        <a href="/">
            ← Back to store
        </a>

    </div>

</nav>


<div class="login-wrap">

    <div class="login-card">

        <h1>
            Staff Login
        </h1>

        <p style="color:#746b82">
            Sign in to manage products, stock and
            store analytics.
        </p>

        {% with messages = get_flashed_messages() %}

            {% for message in messages %}

                <div class="alert">
                    {{ message }}
                </div>

            {% endfor %}

        {% endwith %}

        <form method="POST">

            <div class="form-group">

                <label>
                    Staff Password
                </label>

                <input
                    type="password"
                    name="password"
                    required
                    autofocus
                    placeholder="Enter staff password"
                >

            </div>

            <button
                class="btn btn-purple"
                style="width:100%"
                type="submit"
            >
                Sign In
            </button>

        </form>

    </div>

</div>

</body>
</html>
"""


# ============================================================
# STAFF DASHBOARD
# ============================================================

DASHBOARD_HTML = """
<!doctype html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
    Staff Dashboard | {{ store_name }}
</title>

{{ style|safe }}

</head>

<body>

<nav class="navbar">

    <div class="nav-inner">

        <a class="logo" href="/">
            Rafa<span>'s</span> Store
        </a>

        <div class="nav-links">

            <a href="/" target="_blank">
                View Store
            </a>

            <a
                class="btn btn-light"
                href="/staff/logout"
            >
                Logout
            </a>

        </div>

    </div>

</nav>


<main class="dashboard">

<div class="container">

    <div class="dashboard-header">

        <div>

            <h1>
                Staff Dashboard
            </h1>

            <p style="color:#746b82">
                Manage Rafa's Store.
            </p>

        </div>

    </div>


    <div class="stats">

        <div class="stat">

            <div class="stat-number">
                {{ total_visitors }}
            </div>

            <div class="stat-label">
                Total page views
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {{ product_count }}
            </div>

            <div class="stat-label">
                Products
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {{ total_stock }}
            </div>

            <div class="stat-label">
                Total stock
            </div>

        </div>

    </div>


    <!-- ADD PRODUCT -->

    <section class="panel">

        <h2>
            Add New Slipper
        </h2>

        <form
            method="POST"
            action="/staff/product/new"
        >

            <div class="grid-form">

                <div class="form-group">

                    <label>
                        Name
                    </label>

                    <input
                        name="name"
                        required
                        placeholder="Purple Cloud Slides"
                    >

                </div>


                <div class="form-group">

                    <label>
                        Price (₱)
                    </label>

                    <input
                        name="price"
                        type="number"
                        step="0.01"
                        min="0"
                        required
                        placeholder="399"
                    >

                </div>


                <div class="form-group">

                    <label>
                        Stock
                    </label>

                    <input
                        name="stock"
                        type="number"
                        min="0"
                        required
                        placeholder="20"
                    >

                </div>


                <div class="form-group">

                    <label>
                        Color
                    </label>

                    <input
                        name="color"
                        placeholder="Purple"
                    >

                </div>


                <div class="form-group">

                    <label>
                        Sizes
                    </label>

                    <input
                        name="sizes"
                        placeholder="36,37,38,39,40"
                    >

                </div>


                <div class="form-group">

                    <label>
                        Image URL
                    </label>

                    <input
                        name="image_url"
                        placeholder="https://..."
                    >

                </div>


                <div class="form-group full">

                    <label>
                        Description
                    </label>

                    <textarea
                        name="description"
                        placeholder="Describe the slippers..."
                    ></textarea>

                </div>

            </div>


            <button
                class="btn btn-purple"
                type="submit"
            >
                Add Product
            </button>

        </form>

    </section>


    <!-- PRODUCT MANAGEMENT -->

    <section class="panel">

        <h2>
            Manage Products
        </h2>


        {% for product in products %}

        <div class="product-editor">

            <form
                method="POST"
                action="/staff/product/{{ product['id'] }}/update"
            >

                <div class="grid-form">

                    <div class="form-group">

                        <label>
                            Name
                        </label>

                        <input
                            name="name"
                            value="{{ product['name'] }}"
                            required
                        >

                    </div>


                    <div class="form-group">

                        <label>
                            Price
                        </label>

                        <input
                            name="price"
                            type="number"
                            step="0.01"
                            min="0"
                            value="{{ product['price'] }}"
                            required
                        >

                    </div>


                    <div class="form-group">

                        <label>
                            Stock
                        </label>

                        <input
                            name="stock"
                            type="number"
                            min="0"
                            value="{{ product['stock'] }}"
                            required
                        >

                    </div>


                    <div class="form-group">

                        <label>
                            Color
                        </label>

                        <input
                            name="color"
                            value="{{ product['color'] }}"
                        >

                    </div>


                    <div class="form-group">

                        <label>
                            Sizes
                        </label>

                        <input
                            name="sizes"
                            value="{{ product['sizes'] }}"
                        >

                    </div>


                    <div class="form-group">

                        <label>
                            Image URL
                        </label>

                        <input
                            name="image_url"
                            value="{{ product['image_url'] }}"
                        >

                    </div>


                    <div class="form-group full">

                        <label>
                            Description
                        </label>

                        <textarea name="description">{{ product['description'] }}</textarea>

                    </div>


                    <div class="form-group">

                        <label>
                            Visibility
                        </label>

                        <select name="active">

                            <option
                                value="1"
                                {% if product['active'] %}
                                selected
                                {% endif %}
                            >
                                Visible
                            </option>

                            <option
                                value="0"
                                {% if not product['active'] %}
                                selected
                                {% endif %}
                            >
                                Hidden
                            </option>

                        </select>

                    </div>

                </div>


                <button
                    class="btn btn-purple"
                    type="submit"
                >
                    Save Changes
                </button>

            </form>


            <form
                method="POST"
                action="/staff/product/{{ product['id'] }}/delete"
                style="margin-top:10px"
                onsubmit="
                    return confirm(
                        'Delete this product?'
                    );
                "
            >

                <button
                    class="btn btn-danger"
                    type="submit"
                >
                    Delete Product
                </button>

            </form>

        </div>

        {% endfor %}

    </section>


    <!-- VISITOR ANALYTICS -->

    <section class="panel">

        <h2>
            Visitor Analytics
        </h2>

        <p style="color:#746b82">
            Recent visits recorded by the store.
            IP addresses are hashed before storage.
        </p>

        <div class="table-wrap">

            <table>

                <thead>

                    <tr>

                        <th>
                            Visitor
                        </th>

                        <th>
                            Device
                        </th>

                        <th>
                            Browser
                        </th>

                        <th>
                            Time
                        </th>

                    </tr>

                </thead>

                <tbody>

                    {% for visitor in visitors %}

                    <tr>

                        <td>
                            #{{ visitor["id"] }}
                        </td>

                        <td>
                            {{ visitor["device"] }}
                        </td>

                        <td>
                            {{ visitor["browser"] }}
                        </td>

                        <td>
                            {{ visitor["visited_at"] }}
                        </td>

                    </tr>

                    {% else %}

                    <tr>

                        <td colspan="4">
                            No visitor data yet.
                        </td>

                    </tr>

                    {% endfor %}

                </tbody>

            </table>

        </div>

    </section>

</div>

</main>

</body>
</html>
"""


# ============================================================
# ROUTES
# ============================================================

@app.context_processor
def common_variables():
    return {
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "store_phone": STORE_PHONE,
        "store_email": STORE_EMAIL,
        "style": STYLE,
        "year": datetime.now().year,
    }


@app.route("/")
def home():

    record_visitor()

    connection = db()

    products = connection.execute(
        """
        SELECT *
        FROM products
        WHERE active = 1
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template_string(
        HOME_HTML,
        products=products
    )


@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        if secrets.compare_digest(
            password,
            STAFF_PASSWORD
        ):

            session.clear()
            session["staff"] = True

            return redirect("/staff")

        flash("Incorrect password.")

    return render_template_string(
        LOGIN_HTML
    )


@app.route("/staff/logout")
def staff_logout():

    session.clear()

    return redirect("/")


@app.route("/staff")
@staff_required
def staff_dashboard():

    connection = db()

    products = connection.execute(
        """
        SELECT *
        FROM products
        ORDER BY id DESC
        """
    ).fetchall()

    visitors = connection.execute(
        """
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 200
        """
    ).fetchall()

    total_visitors = connection.execute(
        "SELECT COUNT(*) FROM visitors"
    ).fetchone()[0]

    total_stock = connection.execute(
        """
        SELECT COALESCE(SUM(stock), 0)
        FROM products
        """
    ).fetchone()[0]

    product_count = connection.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    connection.close()

    return render_template_string(
        DASHBOARD_HTML,
        products=products,
        visitors=visitors,
        total_visitors=total_visitors,
        total_stock=total_stock,
        product_count=product_count
    )


@app.route(
    "/staff/product/new",
    methods=["POST"]
)
@staff_required
def create_product():

    name = request.form.get(
        "name",
        ""
    ).strip()

    if not name:
        flash("Product name is required.")
        return redirect("/staff")

    try:

        price = max(
            float(
                request.form.get(
                    "price",
                    0
                )
            ),
            0
        )

        stock = max(
            int(
                request.form.get(
                    "stock",
                    0
                )
            ),
            0
        )

    except ValueError:

        flash("Invalid price or stock.")
        return redirect("/staff")

    connection = db()

    connection.execute(
        """
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
        """,
        (
            name,
            request.form.get(
                "description",
                ""
            ).strip(),

            price,
            stock,

            request.form.get(
                "sizes",
                ""
            ).strip(),

            request.form.get(
                "color",
                ""
            ).strip(),

            request.form.get(
                "image_url",
                ""
            ).strip(),

            datetime.now(
                timezone.utc
            ).isoformat()
        )
    )

    connection.commit()
    connection.close()

    flash("Product added.")

    return redirect("/staff")


@app.route(
    "/staff/product/<int:product_id>/update",
    methods=["POST"]
)
@staff_required
def update_product(product_id):

    name = request.form.get(
        "name",
        ""
    ).strip()

    try:

        price = max(
            float(
                request.form.get(
                    "price",
                    0
                )
            ),
            0
        )

        stock = max(
            int(
                request.form.get(
                    "stock",
                    0
                )
            ),
            0
        )

    except ValueError:

        flash("Invalid price or stock.")
        return redirect("/staff")

    active = (
        1
        if request.form.get("active") == "1"
        else 0
    )

    connection = db()

    connection.execute(
        """
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
        """,
        (
            name,

            request.form.get(
                "description",
                ""
            ).strip(),

            price,
            stock,

            request.form.get(
                "sizes",
                ""
            ).strip(),

            request.form.get(
                "color",
                ""
            ).strip(),

            request.form.get(
                "image_url",
                ""
            ).strip(),

            active,
            product_id
        )
    )

    connection.commit()
    connection.close()

    flash("Product updated.")

    return redirect("/staff")


@app.route(
    "/staff/product/<int:product_id>/delete",
    methods=["POST"]
)
@staff_required
def delete_product(product_id):

    connection = db()

    connection.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    connection.commit()
    connection.close()

    flash("Product deleted.")

    return redirect("/staff")


# ============================================================
# STARTUP
# ============================================================

init_database()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        ),
        debug=False
    )
