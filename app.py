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

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "rafa-store-change-this-secret"
)

DB_PATH = os.environ.get("DATABASE_PATH", "rafa_store.db")

STORE_NAME = "Rafa's Store"
STORE_ADDRESS = "268 A. Mabini Street, Liliw, Laguna"
STORE_PHONE = "0976 1296450"

STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "staff")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "change-me")


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            category TEXT DEFAULT 'Slippers',
            image TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            device TEXT,
            language TEXT,
            visited_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    count = db.execute(
        "SELECT COUNT(*) AS count FROM products"
    ).fetchone()["count"]

    if count == 0:
        db.executemany("""
            INSERT INTO products
            (name, description, price, stock, category, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (
                "Classic Comfort",
                "Simple everyday slippers designed for comfort.",
                299,
                20,
                "Slippers",
                "",
            ),
            (
                "Filipino Craft",
                "A warm Filipino-inspired footwear style.",
                399,
                15,
                "Handcrafted",
                "",
            ),
            (
                "Premium Everyday",
                "Comfortable footwear for everyday use.",
                499,
                10,
                "Premium",
                "",
            ),
            (
                "Liliw Collection",
                "Inspired by the footwear-making tradition of Liliw.",
                599,
                8,
                "Collection",
                "",
            ),
        ])

    db.commit()
    db.close()


init_db()


# ============================================================
# VISITOR HELPERS
# ============================================================

def get_device(user_agent):
    ua = (user_agent or "").lower()

    if "ipad" in ua or "tablet" in ua:
        return "Tablet"

    if (
        "mobile" in ua
        or "android" in ua
        or "iphone" in ua
        or "ipod" in ua
    ):
        return "Mobile"

    return "Desktop"


def record_visitor():
    if session.get("staff_logged_in"):
        return

    ip = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr
    )

    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    user_agent = request.headers.get("User-Agent", "")
    language = request.headers.get("Accept-Language", "")
    device = get_device(user_agent)

    db = get_db()

    db.execute("""
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

    db.commit()
    db.close()


def staff_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in"):
            return redirect(url_for("staff_login"))

        return func(*args, **kwargs)

    return wrapper


# ============================================================
# PREMIUM FRONT-END CSS
# ============================================================

CSS = r"""
:root {
    --bg: #f8f0e5;
    --bg2: #efe0cc;
    --card: rgba(255, 250, 243, .82);
    --solid-card: #fffaf3;

    --brown-1: #5e402b;
    --brown-2: #79563a;
    --brown-3: #a67c52;
    --brown-4: #c8a27a;
    --brown-5: #ead5bb;

    --text: #39271a;
    --muted: #806b57;

    --border: rgba(121, 86, 58, .18);
    --shadow: 0 25px 70px rgba(83, 55, 34, .14);

    --white: #fff;
    --green: #58785c;
    --red: #a44e4e;
}

body.dark {
    --bg: #17110d;
    --bg2: #241912;
    --card: rgba(44, 32, 23, .86);
    --solid-card: #2b2018;

    --brown-1: #f1d5b1;
    --brown-2: #d8b58d;
    --brown-3: #bd9164;
    --brown-4: #9b704b;
    --brown-5: #60432d;

    --text: #f7eadc;
    --muted: #c6af98;

    --border: rgba(239, 211, 178, .15);
    --shadow: 0 25px 70px rgba(0, 0, 0, .35);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    color: var(--text);
    background:
        radial-gradient(
            circle at 10% 5%,
            rgba(200,162,122,.27),
            transparent 25%
        ),
        radial-gradient(
            circle at 90% 20%,
            rgba(166,124,82,.18),
            transparent 25%
        ),
        linear-gradient(
            135deg,
            var(--bg),
            var(--bg2)
        );
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
    transition:
        background .35s ease,
        color .35s ease;
}

body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    opacity: .13;
    background-image:
        radial-gradient(
            rgba(120, 83, 53, .35) 1px,
            transparent 1px
        );
    background-size: 24px 24px;
    mask-image: linear-gradient(
        to bottom,
        black,
        transparent 80%
    );
}

a {
    color: inherit;
    text-decoration: none;
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

::-webkit-scrollbar {
    width: 10px;
}

::-webkit-scrollbar-track {
    background: var(--bg2);
}

::-webkit-scrollbar-thumb {
    background: var(--brown-3);
    border-radius: 99px;
}


/* NAVIGATION */

.navbar {
    position: sticky;
    top: 0;
    z-index: 999;

    backdrop-filter: blur(22px);

    background: color-mix(
        in srgb,
        var(--card) 88%,
        transparent
    );

    border-bottom: 1px solid var(--border);
}

.nav-inner {
    max-width: 1280px;
    margin: auto;
    min-height: 78px;
    padding: 12px 24px;

    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 13px;
}

.logo {
    width: 58px;
    height: 58px;
    object-fit: contain;
    border-radius: 15px;
}

.brand-title {
    font-weight: 900;
    letter-spacing: -.5px;
    font-size: 19px;
}

.brand-subtitle {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 6px;
}

.nav-links a,
.nav-button {
    border: 0;
    background: transparent;
    color: var(--text);

    padding: 10px 13px;
    border-radius: 12px;

    font-size: 14px;
    font-weight: 700;

    transition:
        background .2s,
        transform .2s;
}

.nav-links a:hover,
.nav-button:hover {
    background: var(--bg2);
    transform: translateY(-2px);
}

.nav-cta {
    background: var(--brown-3) !important;
    color: white !important;
    box-shadow: 0 10px 25px rgba(121,86,58,.25);
}


/* HERO */

.hero {
    position: relative;
    max-width: 1280px;
    min-height: 700px;
    margin: auto;
    padding: 100px 24px 70px;

    display: grid;
    place-items: center;

    text-align: center;
}

.hero-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(3px);
    pointer-events: none;
}

.orb-1 {
    width: 320px;
    height: 320px;
    background: rgba(200,162,122,.23);
    left: -100px;
    top: 90px;
    animation: float 8s ease-in-out infinite;
}

.orb-2 {
    width: 220px;
    height: 220px;
    background: rgba(166,124,82,.17);
    right: -30px;
    bottom: 100px;
    animation: float 7s ease-in-out infinite reverse;
}

.hero-content {
    position: relative;
    z-index: 2;
    max-width: 900px;
}

.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 9px;

    padding: 9px 15px;

    border: 1px solid var(--border);
    border-radius: 999px;

    background: var(--card);
    box-shadow: var(--shadow);

    color: var(--brown-2);
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 1.7px;
    text-transform: uppercase;
}

.eyebrow::before {
    content: "";
    width: 7px;
    height: 7px;
    background: var(--brown-3);
    border-radius: 50%;
    box-shadow: 0 0 0 6px rgba(166,124,82,.13);
}

.hero h1 {
    margin: 27px 0 17px;

    font-size: clamp(
        54px,
        10vw,
        110px
    );

    line-height: .88;
    letter-spacing: -7px;

    color: var(--brown-1);

    text-shadow:
        0 18px 35px rgba(94,64,43,.12);
}

.hero-description {
    max-width: 700px;
    margin: auto;

    font-size: clamp(17px, 2vw, 21px);
    line-height: 1.8;

    color: var(--muted);
}

.hero-buttons {
    margin-top: 35px;

    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
}

.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 9px;

    border: 0;
    padding: 14px 21px;

    border-radius: 14px;

    background: var(--brown-3);
    color: white;

    font-weight: 850;

    box-shadow:
        0 14px 35px rgba(121,86,58,.24);

    transition:
        transform .2s,
        box-shadow .2s,
        filter .2s;
}

.btn:hover {
    transform: translateY(-4px);
    filter: brightness(1.05);

    box-shadow:
        0 18px 45px rgba(121,86,58,.3);
}

.btn.secondary {
    background: var(--card);
    color: var(--text);
    border: 1px solid var(--border);
    box-shadow: none;
}


/* FLOATING FEATURE CARDS */

.floating-card {
    position: absolute;
    z-index: 3;

    width: 175px;

    padding: 18px;

    text-align: left;

    background: var(--card);
    border: 1px solid var(--border);

    backdrop-filter: blur(18px);

    border-radius: 20px;

    box-shadow: var(--shadow);

    animation: float 6s ease-in-out infinite;
}

.floating-card strong {
    display: block;
    font-size: 15px;
}

.floating-card span {
    display: block;
    margin-top: 5px;
    color: var(--muted);
    font-size: 12px;
}

.fc-left {
    left: 3%;
    top: 42%;
}

.fc-right {
    right: 3%;
    top: 27%;
    animation-delay: -2s;
}

.fc-icon {
    width: 42px;
    height: 42px;

    display: grid;
    place-items: center;

    margin-bottom: 10px;

    border-radius: 13px;

    background: var(--bg2);
    color: var(--brown-2);

    font-size: 20px;
}


/* SECTION */

.section {
    max-width: 1280px;
    margin: auto;
    padding: 80px 24px;
}

.section-heading {
    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 20px;
    margin-bottom: 32px;
}

.section-heading h2 {
    margin: 0;
    font-size: clamp(31px, 5vw, 50px);
    letter-spacing: -2px;
}

.section-heading p {
    margin: 8px 0 0;
    color: var(--muted);
}


/* SEARCH */

.search-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 25px;
}

.search-box {
    flex: 1;
    min-width: 220px;

    display: flex;
    align-items: center;
    gap: 10px;

    padding: 13px 16px;

    background: var(--card);
    border: 1px solid var(--border);

    border-radius: 15px;

    box-shadow: var(--shadow);
}

.search-box input {
    width: 100%;
    border: 0;
    outline: 0;

    background: transparent;
    color: var(--text);
}

.filter-button {
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);

    border-radius: 13px;
    padding: 12px 15px;

    font-weight: 700;
}

.filter-button.active {
    background: var(--brown-3);
    color: white;
}


/* PRODUCTS */

.products {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(245px, 1fr)
        );
    gap: 22px;
}

.product {
    position: relative;

    overflow: hidden;

    background: var(--card);
    border: 1px solid var(--border);

    border-radius: 24px;

    box-shadow: var(--shadow);

    transition:
        transform .3s,
        box-shadow .3s;

    animation: reveal .7s ease both;
}

.product:hover {
    transform:
        translateY(-9px)
        rotateX(2deg);

    box-shadow:
        0 30px 70px rgba(83,55,34,.2);
}

.product-visual {
    height: 230px;
    position: relative;
    overflow: hidden;

    background:
        radial-gradient(
            circle at 30% 25%,
            rgba(255,255,255,.7),
            transparent 25%
        ),
        linear-gradient(
            135deg,
            var(--brown-5),
            var(--bg2)
        );
}

.product-visual::before {
    content: "";
    position: absolute;

    width: 180px;
    height: 180px;

    border-radius: 50%;

    background: rgba(255,255,255,.2);

    top: -70px;
    right: -50px;

    animation: pulse 5s ease-in-out infinite;
}

.slipper-shape {
    position: absolute;

    left: 50%;
    top: 53%;

    width: 105px;
    height: 165px;

    transform:
        translate(-50%, -50%)
        rotate(-25deg);

    border-radius:
        58% 58% 38% 38%
        / 25% 25% 75% 75%;

    background:
        linear-gradient(
            145deg,
            var(--brown-3),
            var(--brown-1)
        );

    box-shadow:
        12px 18px 25px rgba(72,47,29,.2);

    transition: transform .35s;
}

.product:hover .slipper-shape {
    transform:
        translate(-50%, -50%)
        rotate(-18deg)
        scale(1.08);
}

.slipper-strap {
    position: absolute;

    left: 50%;
    top: 48%;

    width: 65px;
    height: 75px;

    transform:
        translate(-50%, -50%);

    border: 10px solid var(--brown-5);
    border-bottom: 0;

    border-radius:
        50% 50% 0 0;
}

.product-label {
    position: absolute;
    top: 15px;
    left: 15px;

    padding: 7px 10px;

    border-radius: 999px;

    background: rgba(255,255,255,.7);
    color: var(--brown-1);

    font-size: 10px;
    font-weight: 900;

    backdrop-filter: blur(8px);
}

.product-body {
    padding: 21px;
}

.product-body h3 {
    margin: 0 0 7px;
    font-size: 20px;
}

.product-body p {
    min-height: 50px;
    color: var(--muted);
    line-height: 1.6;
    font-size: 14px;
}

.product-bottom {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 10px;
}

.price {
    color: var(--brown-2);
    font-size: 22px;
    font-weight: 950;
}

.stock {
    font-size: 11px;
    color: var(--muted);
}


/* ABOUT */

.about-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 25px;
}

.about-card {
    padding: 32px;

    background: var(--card);
    border: 1px solid var(--border);

    border-radius: 25px;

    box-shadow: var(--shadow);
}

.about-card h3 {
    margin-top: 0;
    color: var(--brown-2);
    font-size: 25px;
}

.about-card p {
    line-height: 1.85;
    color: var(--muted);
}

.highlight {
    padding: 17px;
    margin-top: 17px;

    border-left: 4px solid var(--brown-3);

    background: var(--bg2);
    border-radius: 10px;
}


/* STATS */

.stats {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(190px, 1fr)
        );

    gap: 16px;
    margin-top: 30px;
}

.stat-card {
    padding: 24px;

    border: 1px solid var(--border);
    background: var(--card);

    border-radius: 20px;

    text-align: center;

    box-shadow: var(--shadow);
}

.stat-number {
    font-size: 38px;
    font-weight: 950;
    color: var(--brown-2);
}

.stat-label {
    color: var(--muted);
    font-size: 13px;
}


/* FOOTER */

.footer {
    margin-top: 70px;
    padding: 65px 24px 30px;

    background:
        radial-gradient(
            circle at 10% 0,
            rgba(200,162,122,.25),
            transparent 30%
        ),
        #5e402b;

    color: white;
}

.footer-inner {
    max-width: 1280px;
    margin: auto;

    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px, 1fr)
        );

    gap: 40px;
}

.footer h3 {
    color: #f2d5b3;
}

.footer p {
    color: #ead8c5;
    line-height: 1.8;
}

.footer-bottom {
    max-width: 1280px;
    margin: 45px auto 0;
    padding-top: 20px;

    border-top: 1px solid rgba(255,255,255,.15);

    color: #d9c4ad;
    font-size: 12px;
}


/* STAFF */

.form-card {
    width: min(680px, calc(100% - 35px));
    margin: 70px auto;

    padding: 32px;

    background: var(--card);
    border: 1px solid var(--border);

    border-radius: 25px;

    box-shadow: var(--shadow);
}

.form-group {
    margin-bottom: 18px;
}

.form-group label {
    display: block;
    margin-bottom: 7px;
    font-weight: 800;
}

.form-group input,
.form-group textarea,
.form-group select {
    width: 100%;

    padding: 13px;

    border: 1px solid var(--border);
    border-radius: 12px;

    outline: 0;

    background: var(--bg);
    color: var(--text);
}

.form-group textarea {
    min-height: 120px;
    resize: vertical;
}

.flash {
    max-width: 900px;
    margin: 20px auto;
    padding: 14px 18px;

    background: var(--bg2);
    border: 1px solid var(--border);

    border-radius: 14px;
}


/* DASHBOARD */

.dashboard {
    max-width: 1280px;
    margin: auto;
    padding: 40px 24px;
}

.dashboard-grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(190px, 1fr)
        );
    gap: 17px;
    margin: 25px 0;
}

.stat {
    padding: 24px;

    background: var(--card);
    border: 1px solid var(--border);

    border-radius: 20px;
    box-shadow: var(--shadow);
}

.stat strong {
    display: block;
    margin-top: 5px;

    font-size: 38px;
    color: var(--brown-3);
}

.table-wrap {
    overflow-x: auto;

    background: var(--card);
    border: 1px solid var(--border);

    border-radius: 20px;

    box-shadow: var(--shadow);

    margin-bottom: 40px;
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
    background: var(--bg2);
}

td {
    color: var(--muted);
}


/* ANIMATIONS */

@keyframes float {
    0%, 100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-16px);
    }
}

@keyframes pulse {
    0%, 100% {
        transform: scale(1);
        opacity: .45;
    }

    50% {
        transform: scale(1.15);
        opacity: .75;
    }
}

@keyframes reveal {
    from {
        opacity: 0;
        transform: translateY(25px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}


/* MOBILE */

@media (max-width: 850px) {

    .nav-inner {
        flex-direction: column;
        padding: 12px 15px;
    }

    .nav-links {
        justify-content: center;
        flex-wrap: wrap;
    }

    .hero {
        min-height: 620px;
        padding-top: 70px;
    }

    .hero h1 {
        letter-spacing: -4px;
    }

    .floating-card {
        display: none;
    }

    .about-grid {
        grid-template-columns: 1fr;
    }

    .section-heading {
        display: block;
    }
}

@media (max-width: 520px) {

    .nav-links a:nth-child(3),
    .nav-links a:nth-child(4) {
        display: none;
    }

    .hero h1 {
        font-size: 55px;
    }

    .section {
        padding: 60px 16px;
    }

    .hero {
        padding-left: 16px;
        padding-right: 16px;
    }
}
"""


# ============================================================
# MAIN PAGE
# ============================================================

INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <meta
        name="description"
        content="Rafa's Store — handcrafted Filipino footwear."
    >

    <title>{{ store_name }}</title>

    <style>
        {{ css|safe }}
    </style>
</head>


<body>

<nav class="navbar">

    <div class="nav-inner">

        <a href="#home" class="brand">

            <img
                class="logo"
                src="{{ url_for('static', filename='image0 (3)') }}"
                alt="Rafa's Store logo"
                onerror="this.style.display='none'"
            >

            <div>
                <div class="brand-title">
                    {{ store_name }}
                </div>

                <div class="brand-subtitle">
                    Filipino Footwear
                </div>
            </div>

        </a>


        <div class="nav-links">

            <a href="#home">Home</a>
            <a href="#products">Products</a>
            <a href="#about">About</a>
            <a href="#contact">Contact</a>

            <button
                class="nav-button"
                onclick="toggleLanguage()"
                id="languageButton"
            >
                FIL
            </button>

            <button
                class="nav-button"
                onclick="toggleTheme()"
                id="themeButton"
            >
                🌙
            </button>

            <a
                href="{{ url_for('staff_login') }}"
                class="nav-cta"
            >
                Staff
            </a>

        </div>

    </div>

</nav>


<section class="hero" id="home">

    <div class="hero-orb orb-1"></div>
    <div class="hero-orb orb-2"></div>


    <div class="floating-card fc-left">

        <div class="fc-icon">
            ✨
        </div>

        <strong>Filipino Craft</strong>

        <span>
            Inspired by local artistry
        </span>

    </div>


    <div class="floating-card fc-right">

        <div class="fc-icon">
            ♡
        </div>

        <strong>Made With Care</strong>

        <span>
            Comfort meets craftsmanship
        </span>

    </div>


    <div class="hero-content">

        <div class="eyebrow">
            Proudly Filipino Footwear
        </div>


        <h1>
            {{ store_name }}
        </h1>


        <p
            class="hero-description"
            id="heroDescription"
        >
            Comfortable footwear with a warm Filipino spirit.
            Discover simple, beautiful styles made for everyday life.
        </p>


        <div class="hero-buttons">

            <a
                class="btn"
                href="#products"
            >
                Explore Collection ↓
            </a>

            <a
                class="btn secondary"
                href="#about"
            >
                Our Story
            </a>

        </div>

    </div>

</section>


<section class="section" id="products">

    <div class="section-heading">

        <div>

            <h2>
                Our Collection
            </h2>

            <p>
                Explore the footwear currently available.
            </p>

        </div>

    </div>


    <div class="search-row">

        <div class="search-box">

            🔎

            <input
                id="productSearch"
                type="search"
                placeholder="Search slippers..."
                oninput="filterProducts()"
            >

        </div>


        <button
            class="filter-button active"
            onclick="setFilter('all', this)"
        >
            All
        </button>

        <button
            class="filter-button"
            onclick="setFilter('Slippers', this)"
        >
            Slippers
        </button>

        <button
            class="filter-button"
            onclick="setFilter('Handcrafted', this)"
        >
            Handcrafted
        </button>

        <button
            class="filter-button"
            onclick="setFilter('Premium', this)"
        >
            Premium
        </button>

    </div>


    <div class="products" id="productsGrid">

        {% for product in products %}

        <article
            class="product"
            data-name="{{ product['name']|lower }}"
            data-category="{{ product['category'] }}"
        >

            <!-- No product images are used yet.
                 This is an animated placeholder. -->

            <div class="product-visual">

                <div class="product-label">
                    {{ product["category"] }}
                </div>


                <div class="slipper-shape">

                    <div class="slipper-strap"></div>

                </div>

            </div>


            <div class="product-body">

                <h3>
                    {{ product["name"] }}
                </h3>

                <p>
                    {{ product["description"] }}
                </p>


                <div class="product-bottom">

                    <div>

                        <div class="price">
                            ₱{{ "%.2f"|format(product["price"]) }}
                        </div>

                        <div class="stock">

                            {% if product["stock"] > 0 %}

                                {{ product["stock"] }}
                                available

                            {% else %}

                                Out of stock

                            {% endif %}

                        </div>

                    </div>


                    <span>
                        🥿
                    </span>

                </div>

            </div>

        </article>

        {% endfor %}

    </div>

</section>


<section class="section">

    <div class="stats">

        <div class="stat-card">

            <div class="stat-number" data-count="100">
                0
            </div>

            <div class="stat-label">
                Filipino Craft
            </div>

        </div>


        <div class="stat-card">

            <div class="stat-number" data-count="2015">
                0
            </div>

            <div class="stat-label">
                Family Business Since
            </div>

        </div>


        <div class="stat-card">

            <div class="stat-number" data-count="{{ products|length }}">
                0
            </div>

            <div class="stat-label">
                Products Listed
            </div>

        </div>

    </div>

</section>


<section class="section" id="about">

    <div class="section-heading">

        <div>

            <h2>
                Our Story
            </h2>

            <p>
                Filipino craftsmanship, creativity and tradition.
            </p>

        </div>

    </div>


    <div class="about-grid">

        <div class="about-card">

            <h3>
                About Us
            </h3>

            <p>
                Golden Zapatillas Corporation is a family-owned
                business established in 2015, continuing a family
                tradition of manufacturing high-quality footwear
                in Liliw, Laguna.
            </p>

            <p>
                Our goal is to create footwear that showcases the
                creativity and craftsmanship of Filipino artisans,
                including painters, beadworkers, embroiderers and
                shoemakers from Laguna.
            </p>

            <div class="highlight">
                🇵🇭 Supporting Filipino craftsmanship and local
                suppliers.
            </div>

        </div>


        <div class="about-card">

            <h3>
                Padron
            </h3>

            <p>
                Padron is the brand name known for footwear designs
                inspired by patterns and craftsmanship.
            </p>

            <p>
                We use locally sourced materials such as abaca,
                Ifugao fabric and Inabel to support local suppliers
                while creating footwear with a distinctly Filipino
                character.
            </p>

            <div class="highlight">
                🌿 Heritage · Sustainability · Craftsmanship
            </div>

        </div>


        <div class="about-card">

            <h3>
                Mission
            </h3>

            <p>
                To empower Filipino artisans and women artisans
                skilled in handpainting, embroidery and crochet by
                creating sustainable, high-quality footwear that
                celebrates local heritage and craftsmanship.
            </p>

        </div>


        <div class="about-card">

            <h3>
                Vision
            </h3>

            <p>
                To become a leading pioneer in sustainable,
                handcrafted footwear while preserving the family's
                footwear-making legacy and positioning Liliw as a
                center of footwear excellence.
            </p>

        </div>

    </div>

</section>


<footer class="footer" id="contact">

    <div class="footer-inner">

        <div>

            <h3>
                {{ store_name }}
            </h3>

            <p>
                Proudly showcasing Filipino footwear,
                craftsmanship and creativity.
            </p>

        </div>


        <div>

            <h3>
                Visit Us
            </h3>

            <p>
                {{ store_address }}
            </p>

        </div>


        <div>

            <h3>
                Contact
            </h3>

            <p>
                {{ store_phone }}
            </p>

        </div>

    </div>


    <div class="footer-bottom">

        © {{ current_year }} {{ store_name }}.
        All rights reserved.

    </div>

</footer>


<script>

let currentFilter = "all";


function toggleTheme() {

    document.body.classList.toggle("dark");

    const dark =
        document.body.classList.contains("dark");

    localStorage.setItem(
        "rafaTheme",
        dark ? "dark" : "light"
    );

    document.getElementById("themeButton").textContent =
        dark ? "☀️" : "🌙";
}


function loadTheme() {

    if (
        localStorage.getItem("rafaTheme")
        === "dark"
    ) {
        document.body.classList.add("dark");

        document.getElementById(
            "themeButton"
        ).textContent = "☀️";
    }
}


function toggleLanguage() {

    const button =
        document.getElementById("languageButton");

    const description =
        document.getElementById("heroDescription");

    if (
        button.textContent.trim() === "FIL"
    ) {

        button.textContent = "ENG";

        description.textContent =
            "Komportableng footwear na may mainit na pusong Pilipino. " +
            "Tuklasin ang simple at magandang mga disenyo para sa araw-araw.";

    } else {

        button.textContent = "FIL";

        description.textContent =
            "Comfortable footwear with a warm Filipino spirit. " +
            "Discover simple, beautiful styles made for everyday life.";
    }
}


function setFilter(category, button) {

    currentFilter = category;

    document
        .querySelectorAll(".filter-button")
        .forEach(function(btn) {
            btn.classList.remove("active");
        });

    button.classList.add("active");

    filterProducts();
}


function filterProducts() {

    const search =
        document
            .getElementById("productSearch")
            .value
            .toLowerCase()
            .trim();

    document
        .querySelectorAll(".product")
        .forEach(function(product) {

            const name =
                product.dataset.name || "";

            const category =
                product.dataset.category || "";

            const matchesSearch =
                name.includes(search);

            const matchesCategory =
                currentFilter === "all"
                || category === currentFilter;

            product.style.display =
                matchesSearch && matchesCategory
                    ? ""
                    : "none";
        });
}


/* Animated numbers */

function animateCounters() {

    document
        .querySelectorAll("[data-count]")
        .forEach(function(counter) {

            const target =
                Number(counter.dataset.count);

            let current = 0;

            const duration = 1200;
            const start = performance.now();

            function update(time) {

                const progress =
                    Math.min(
                        (time - start) / duration,
                        1
                    );

                current =
                    Math.floor(
                        progress * target
                    );

                counter.textContent =
                    current.toLocaleString();

                if (progress < 1) {
                    requestAnimationFrame(update);
                }
            }

            requestAnimationFrame(update);
        });
}


/* Scroll reveal */

const observer =
    new IntersectionObserver(
        function(entries) {

            entries.forEach(function(entry) {

                if (entry.isIntersecting) {

                    entry.target.style.opacity = "1";
                    entry.target.style.transform =
                        "translateY(0)";

                }

            });

        },
        {
            threshold: .12
        }
    );


document
    .querySelectorAll(".product, .about-card, .stat-card")
    .forEach(function(element) {

        element.style.opacity = "0";
        element.style.transform =
            "translateY(25px)";

        element.style.transition =
            "opacity .7s ease, transform .7s ease";

        observer.observe(element);
    });


loadTheme();


setTimeout(
    animateCounters,
    350
);

</script>

</body>

</html>
"""


# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN_HTML = r"""
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>Staff Login — {{ store_name }}</title>

<style>
{{ css|safe }}
</style>

</head>


<body>

<div class="form-card">

    <h1>{{ store_name }}</h1>

    <p>
        Staff Dashboard
    </p>


    {% with messages = get_flashed_messages() %}

        {% for message in messages %}

            <div class="flash">
                {{ message }}
            </div>

        {% endfor %}

    {% endwith %}


    <form method="POST">

        <div class="form-group">

            <label>
                Username
            </label>

            <input
                name="username"
                autocomplete="username"
                required
            >

        </div>


        <div class="form-group">

            <label>
                Password
            </label>

            <input
                type="password"
                name="password"
                autocomplete="current-password"
                required
            >

        </div>


        <button
            class="btn"
            type="submit"
        >
            Login
        </button>


        <a
            class="btn secondary"
            href="{{ url_for('index') }}"
        >
            Back to Store
        </a>

    </form>

</div>

</body>
</html>
"""


# ============================================================
# PRODUCT FORM
# ============================================================

PRODUCT_FORM_HTML = r"""
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>{{ title }}</title>

<style>
{{ css|safe }}
</style>

</head>


<body>

<div class="form-card">

    <h1>
        {{ title }}
    </h1>


    <form method="POST">

        <div class="form-group">

            <label>
                Product Name
            </label>

            <input
                name="name"
                value="{{ product['name'] if product else '' }}"
                required
            >

        </div>


        <div class="form-group">

            <label>
                Description
            </label>

            <textarea name="description">{{ product['description'] if product else '' }}</textarea>

        </div>


        <div class="form-group">

            <label>
                Price (₱)
            </label>

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

            <label>
                Stock
            </label>

            <input
                type="number"
                min="0"
                name="stock"
                value="{{ product['stock'] if product else 0 }}"
                required
            >

        </div>


        <div class="form-group">

            <label>
                Category
            </label>

            <select name="category">

                {% for category in [
                    "Slippers",
                    "Handcrafted",
                    "Premium",
                    "Collection",
                    "New",
                    "Sale"
                ] %}

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


        <button
            class="btn"
            type="submit"
        >
            Save Product
        </button>


        <a
            class="btn secondary"
            href="{{ url_for('dashboard') }}"
        >
            Cancel
        </a>

    </form>

</div>

</body>
</html>
"""


# ============================================================
# DASHBOARD
# ============================================================

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>Staff Dashboard — {{ store_name }}</title>

<style>
{{ css|safe }}
</style>

</head>


<body>

<nav class="navbar">

    <div class="nav-inner">

        <div class="brand">

            <strong>
                {{ store_name }}
            </strong>

            <span>
                Staff Dashboard
            </span>

        </div>


        <div class="nav-links">

            <a href="{{ url_for('index') }}">
                Store
            </a>

            <a href="{{ url_for('add_product') }}">
                + Product
            </a>

            <a href="{{ url_for('staff_logout') }}">
                Logout
            </a>

        </div>

    </div>

</nav>


<div class="dashboard">

    {% with messages = get_flashed_messages() %}

        {% for message in messages %}

            <div class="flash">
                {{ message }}
            </div>

        {% endfor %}

    {% endwith %}


    <h1>
        Staff Dashboard
    </h1>

    <p>
        Manage products and view store visitor information.
    </p>


    <div class="dashboard-grid">

        <div class="stat">

            Products

            <strong>
                {{ product_count }}
            </strong>

        </div>


        <div class="stat">

            Total Stock

            <strong>
                {{ total_stock }}
            </strong>

        </div>


        <div class="stat">

            Visitors

            <strong>
                {{ visitor_count }}
            </strong>

        </div>

    </div>


    <h2>
        Product Inventory
    </h2>


    <div class="table-wrap">

        <table>

            <thead>

                <tr>

                    <th>
                        Name
                    </th>

                    <th>
                        Category
                    </th>

                    <th>
                        Price
                    </th>

                    <th>
                        Stock
                    </th>

                    <th>
                        Actions
                    </th>

                </tr>

            </thead>


            <tbody>

            {% for product in products %}

                <tr>

                    <td>
                        {{ product["name"] }}
                    </td>

                    <td>
                        {{ product["category"] }}
                    </td>

                    <td>
                        ₱{{ "%.2f"|format(product["price"]) }}
                    </td>

                    <td>
                        {{ product["stock"] }}
                    </td>

                    <td>

                        <a
                            class="btn"
                            href="{{ url_for(
                                'edit_product',
                                product_id=product['id']
                            ) }}"
                        >
                            Edit
                        </a>


                        <form
                            method="POST"
                            action="{{ url_for(
                                'delete_product',
                                product_id=product['id']
                            ) }}"
                            style="display:inline"
                            onsubmit="return confirm('Delete this product?')"
                        >

                            <button
                                class="btn"
                                style="background:#a44e4e"
                                type="submit"
                            >
                                Delete
                            </button>

                        </form>

                    </td>

                </tr>

            {% endfor %}

            </tbody>

        </table>

    </div>


    <h2>
        Visitor Information
    </h2>


    <div class="table-wrap">

        <table>

            <thead>

                <tr>

                    <th>
                        Date
                    </th>

                    <th>
                        IP
                    </th>

                    <th>
                        Device
                    </th>

                    <th>
                        Language
                    </th>

                    <th>
                        Browser Information
                    </th>

                </tr>

            </thead>


            <tbody>

            {% for visitor in visitors %}

                <tr>

                    <td>
                        {{ visitor["visited_at"] }}
                    </td>

                    <td>
                        {{ visitor["ip"] }}
                    </td>

                    <td>
                        {{ visitor["device"] }}
                    </td>

                    <td>
                        {{ visitor["language"] }}
                    </td>

                    <td>
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


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():

    record_visitor()

    db = get_db()

    products = db.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    db.close()

    return render_template_string(
        INDEX_HTML,
        css=CSS,
        products=products,
        store_name=STORE_NAME,
        store_address=STORE_ADDRESS,
        store_phone=STORE_PHONE,
        current_year=datetime.now().year,
    )


# ============================================================
# STAFF LOGIN
# ============================================================

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        )

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == STAFF_USERNAME
            and password == STAFF_PASSWORD
        ):

            session["staff_logged_in"] = True

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid username or password."
        )

    return render_template_string(
        LOGIN_HTML,
        css=CSS,
        store_name=STORE_NAME,
    )


@app.route("/staff/logout")
def staff_logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# ============================================================
# STAFF DASHBOARD
# ============================================================

@app.route("/staff")
@staff_required
def dashboard():

    db = get_db()

    products = db.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    product_count = db.execute("""
        SELECT COUNT(*) AS count
        FROM products
    """).fetchone()["count"]

    total_stock = db.execute("""
        SELECT COALESCE(SUM(stock), 0) AS total
        FROM products
    """).fetchone()["total"]

    visitor_count = db.execute("""
        SELECT COUNT(*) AS count
        FROM visitors
    """).fetchone()["count"]

    visitors = db.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 500
    """).fetchall()

    db.close()

    return render_template_string(
        DASHBOARD_HTML,
        css=CSS,
        store_name=STORE_NAME,
        products=products,
        product_count=product_count,
        total_stock=total_stock,
        visitor_count=visitor_count,
        visitors=visitors,
    )


# ============================================================
# ADD PRODUCT
# ============================================================

@app.route(
    "/staff/product/add",
    methods=["GET", "POST"]
)
@staff_required
def add_product():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        category = request.form.get(
            "category",
            "Slippers"
        ).strip()

        try:
            price = float(
                request.form.get(
                    "price",
                    0
                )
            )

            stock = int(
                request.form.get(
                    "stock",
                    0
                )
            )

        except ValueError:

            flash(
                "Price and stock must be valid numbers."
            )

            return redirect(
                url_for("add_product")
            )

        if not name:

            flash(
                "Product name is required."
            )

            return redirect(
                url_for("add_product")
            )

        if price < 0 or stock < 0:

            flash(
                "Price and stock cannot be negative."
            )

            return redirect(
                url_for("add_product")
            )

        db = get_db()

        db.execute("""
            INSERT INTO products
            (name, description, price, stock, category, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            description,
            price,
            stock,
            category,
            "",
        ))

        db.commit()
        db.close()

        flash(
            "Product added successfully."
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template_string(
        PRODUCT_FORM_HTML,
        css=CSS,
        title="Add Product",
        product=None,
    )


# ============================================================
# EDIT PRODUCT
# ============================================================

@app.route(
    "/staff/product/<int:product_id>/edit",
    methods=["GET", "POST"]
)
@staff_required
def edit_product(product_id):

    db = get_db()

    product = db.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()

    if product is None:

        db.close()

        flash(
            "Product not found."
        )

        return redirect(
            url_for("dashboard")
        )


    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        category = request.form.get(
            "category",
            "Slippers"
        ).strip()

        try:

            price = float(
                request.form.get(
                    "price",
                    0
                )
            )

            stock = int(
                request.form.get(
                    "stock",
                    0
                )
            )

        except ValueError:

            db.close()

            flash(
                "Price and stock must be valid numbers."
            )

            return redirect(
                url_for(
                    "edit_product",
                    product_id=product_id
                )
            )


        if not name:

            db.close()

            flash(
                "Product name is required."
            )

            return redirect(
                url_for(
                    "edit_product",
                    product_id=product_id
                )
            )


        if price < 0 or stock < 0:

            db.close()

            flash(
                "Price and stock cannot be negative."
            )

            return redirect(
                url_for(
                    "edit_product",
                    product_id=product_id
                )
            )


        db.execute("""
            UPDATE products

            SET
                name = ?,
                description = ?,
                price = ?,
                stock = ?,
                category = ?

            WHERE id = ?
        """, (
            name,
            description,
            price,
            stock,
            category,
            product_id,
        ))

        db.commit()
        db.close()

        flash(
            "Product updated successfully."
        )

        return redirect(
            url_for("dashboard")
        )


    db.close()

    return render_template_string(
        PRODUCT_FORM_HTML,
        css=CSS,
        title="Edit Product",
        product=product,
    )


# ============================================================
# DELETE PRODUCT
# ============================================================

@app.route(
    "/staff/product/<int:product_id>/delete",
    methods=["POST"]
)
@staff_required
def delete_product(product_id):

    db = get_db()

    db.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    db.commit()
    db.close()

    flash(
        "Product deleted."
    )

    return redirect(
        url_for("dashboard")
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "store": STORE_NAME,
    }


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
