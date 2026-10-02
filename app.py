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

# ============================================================
# APP CONFIG
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "CHANGE-ME-IN-RENDER"
)

DATABASE = os.getenv(
    "DATABASE_PATH",
    "store.db"
)

STAFF_PASSWORD = os.getenv(
    "STAFF_PASSWORD",
    "CHANGE_THIS_PASSWORD"
)

IP_HASH_SALT = os.getenv(
    "IP_HASH_SALT",
    "CHANGE_THIS_IP_SALT"
)

STORE_NAME = "PADRON"

STORE_ADDRESS = "268 A. Mabini Street, Liliw, Laguna"

STORE_PHONE = "0976 1296450"

STORE_EMAIL = os.getenv("STORE_EMAIL", "")

# ------------------------------------------------------------
# YOUR GITHUB STATIC IMAGES
# ------------------------------------------------------------

IMAGE_0 = "/static/image0%20%283%29.jpg"
IMAGE_1 = "/static/image1.jpg"


# ============================================================
# DATABASE
# ============================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():

    connection = get_db()

    connection.executescript("""
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
            language TEXT DEFAULT 'Unknown',
            referrer TEXT DEFAULT '',
            visited_at TEXT NOT NULL
        );
    """)

    count = connection.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count == 0:

        now = datetime.now(timezone.utc).isoformat()

        products = [
            (
                "Handmade Mules",
                "Handcrafted footwear showcasing the creativity and craftsmanship of Laguna artisans.",
                0,
                0,
                "Various",
                "Various",
                IMAGE_0
            ),
            (
                "Flats",
                "Handcrafted flats using locally sourced materials and Filipino-inspired designs.",
                0,
                0,
                "Various",
                "Various",
                IMAGE_1
            ),
            (
                "Platform Espadrilles",
                "Handmade platform espadrilles featuring traditional Filipino craftsmanship.",
                0,
                0,
                "Various",
                "Various",
                IMAGE_0
            ),
            (
                "Wedge Espadrilles",
                "Handcrafted wedge espadrilles made with locally sourced materials.",
                0,
                0,
                "Various",
                "Various",
                IMAGE_1
            ),
            (
                "Estela Interchangeable Strap",
                "An innovative interchangeable-strap design created through continuous product innovation.",
                0,
                0,
                "Various",
                "Various",
                IMAGE_0
            )
        ]

        for product in products:

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
                (*product, now)
            )

    connection.commit()
    connection.close()


def update_default_images():

    connection = get_db()

    connection.execute(
        """
        UPDATE products
        SET image_url = ?
        WHERE name = 'Handmade Mules'
        """,
        (IMAGE_0,)
    )

    connection.execute(
        """
        UPDATE products
        SET image_url = ?
        WHERE name = 'Flats'
        """,
        (IMAGE_1,)
    )

    connection.execute(
        """
        UPDATE products
        SET image_url = ?
        WHERE name = 'Platform Espadrilles'
        """,
        (IMAGE_0,)
    )

    connection.execute(
        """
        UPDATE products
        SET image_url = ?
        WHERE name = 'Wedge Espadrilles'
        """,
        (IMAGE_1,)
    )

    connection.execute(
        """
        UPDATE products
        SET image_url = ?
        WHERE name = 'Estela Interchangeable Strap'
        """,
        (IMAGE_0,)
    )

    connection.commit()
    connection.close()


# ============================================================
# LANGUAGES
# ============================================================

TRANSLATIONS = {

    "en": {
        "shop": "Shop",
        "about": "About Us",
        "mission": "Mission",
        "vision": "Vision",
        "contact": "Contact",
        "staff": "Staff",
        "products": "Our Products",
        "hero_badge": "Filipino craftsmanship • Liliw, Laguna 🇵🇭",
        "hero_title": "Footwear with a Filipino soul.",
        "hero_text": (
            "Handcrafted footwear celebrating local heritage, "
            "Filipino artisans, creativity, sustainability, and craftsmanship."
        ),
        "explore": "Explore Products",
        "story": "Our Story",
        "materials": "Filipino Materials",
        "heritage": "Our Heritage",
        "mission_title": "Our Mission",
        "vision_title": "Our Vision",
        "sizes": "Sizes",
        "color": "Color",
        "in_stock": "In stock",
        "only_left": "Only {count} left",
        "out_stock": "Out of stock",
        "contact_title": "Contact Us",
        "staff_login": "Staff Login",
        "theme": "Theme",
        "light": "Bright",
        "dark": "Dark",
        "footer": (
            "Handcrafted footwear from Liliw, Laguna, "
            "celebrating Filipino creativity and craftsmanship."
        )
    },

    "fil": {
        "shop": "Mamili",
        "about": "Tungkol sa Amin",
        "mission": "Misyon",
        "vision": "Bisyon",
        "contact": "Kontak",
        "staff": "Staff",
        "products": "Aming mga Produkto",
        "hero_badge": "Gawang Pilipino • Liliw, Laguna 🇵🇭",
        "hero_title": "Footwear na may pusong Pilipino.",
        "hero_text": (
            "Handcrafted na footwear na nagpapakita ng lokal na kultura, "
            "mga artisan, pagkamalikhain, sustainability, at kalidad."
        ),
        "explore": "Tingnan ang mga Produkto",
        "story": "Aming Kuwento",
        "materials": "Mga Materyales na Pilipino",
        "heritage": "Aming Pamana",
        "mission_title": "Aming Misyon",
        "vision_title": "Aming Bisyon",
        "sizes": "Mga Sukat",
        "color": "Kulay",
        "in_stock": "May stock",
        "only_left": "{count} na lang ang natitira",
        "out_stock": "Walang stock",
        "contact_title": "Makipag-ugnayan",
        "staff_login": "Staff Login",
        "theme": "Tema",
        "light": "Maliwanag",
        "dark": "Madilim",
        "footer": (
            "Handcrafted footwear mula sa Liliw, Laguna, "
            "na nagpapakita ng galing at pagkamalikhain ng mga Pilipino."
        )
    },

    "ceb": {
        "shop": "Palit",
        "about": "Mahitungod Kanamo",
        "mission": "Misyon",
        "vision": "Bisyon",
        "contact": "Kontak",
        "staff": "Staff",
        "products": "Among mga Produkto",
        "hero_badge": "Pinoy nga pagkamaabtik • Liliw, Laguna 🇵🇭",
        "hero_title": "Footwear nga adunay Filipino nga kalag.",
        "hero_text": (
            "Handcrafted nga footwear nga nagpakita sa lokal nga kultura, "
            "mga artisan, pagkamamugnaon, sustainability, ug kalidad."
        ),
        "explore": "Tan-awa ang mga Produkto",
        "story": "Among Istorya",
        "materials": "Mga Materyales nga Pilipino",
        "heritage": "Atong Kabilin",
        "mission_title": "Among Misyon",
        "vision_title": "Among Bisyon",
        "sizes": "Mga Gidak-on",
        "color": "Kolor",
        "in_stock": "Adunay stock",
        "only_left": "{count} na lang nahibilin",
        "out_stock": "Walay stock",
        "contact_title": "Kontak Kami",
        "staff_login": "Staff Login",
        "theme": "Tema",
        "light": "Hayag",
        "dark": "Ngitngit",
        "footer": (
            "Handcrafted nga footwear gikan sa Liliw, Laguna, "
            "nga nagpasidungog sa Filipino nga pagkamamugnaon ug kahibalo."
        )
    }
}


def current_language():

    language = request.args.get(
        "lang",
        session.get("language", "en")
    )

    if language not in TRANSLATIONS:
        language = "en"

    session["language"] = language

    return language


# ============================================================
# PRIVACY-CONSCIOUS VISITOR ANALYTICS
# ============================================================

def hashed_ip():

    ip = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr or "unknown"
    )

    # Only use the first forwarded address.
    ip = ip.split(",")[0].strip()

    return hashlib.sha256(
        f"{IP_HASH_SALT}:{ip}".encode()
    ).hexdigest()[:32]


def detect_device(user_agent):

    ua = user_agent.lower()

    if "ipad" in ua or "tablet" in ua:
        return "Tablet"

    if "iphone" in ua:
        return "iPhone"

    if "android" in ua:
        return "Android"

    if "windows" in ua:
        return "Windows PC"

    if "macintosh" in ua:
        return "Mac"

    if "linux" in ua:
        return "Linux"

    return "Unknown"


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

    return "Unknown"


def record_visitor():

    user_agent = request.headers.get(
        "User-Agent",
        ""
    )

    connection = get_db()

    connection.execute(
        """
        INSERT INTO visitors
        (
            ip_hash,
            device,
            browser,
            language,
            referrer,
            visited_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            hashed_ip(),
            detect_device(user_agent),
            detect_browser(user_agent),
            session.get("language", "en"),
            request.referrer or "",
            datetime.now(timezone.utc).isoformat()
        )
    )

    connection.commit()
    connection.close()


# ============================================================
# STAFF SECURITY
# ============================================================

def staff_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("staff"):
            return redirect(
                url_for("staff_login")
            )

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# STYLES
# ============================================================

STYLE = r"""
<style>

:root {
    --purple: #8b5cf6;
    --purple2: #6d28d9;
    --pink: #ec4899;
    --orange: #f97316;
    --blue: #06b6d4;

    --background: #fbf8ff;
    --surface: rgba(255,255,255,.92);
    --surface2: #f5f0ff;

    --text: #261338;
    --muted: #77677f;

    --border: rgba(124,58,237,.15);

    --shadow:
        0 20px 60px rgba(76,29,149,.13);
}

body.dark {
    --background: #0e0916;
    --surface: #1b1125;
    --surface2: #271735;

    --text: #faf5ff;
    --muted: #c1b2cb;

    --border: rgba(196,181,253,.16);

    --shadow:
        0 25px 70px rgba(0,0,0,.4);
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

    background: var(--background);
    color: var(--text);

    transition:
        background .3s,
        color .3s;
}

a {
    text-decoration: none;
    color: inherit;
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

.container {
    max-width: 1200px;
    margin: auto;
    padding: 0 22px;
}

/* NAV */

.navbar {
    position: sticky;
    top: 0;
    z-index: 1000;

    backdrop-filter: blur(20px);

    background: rgba(255,255,255,.78);

    border-bottom:
        1px solid var(--border);
}

body.dark .navbar {
    background: rgba(14,9,22,.82);
}

.nav-inner {
    max-width: 1200px;
    margin: auto;

    padding: 14px 22px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 18px;
}

.logo {
    font-size: 25px;
    font-weight: 1000;

    color: var(--purple2);
}

.logo span {
    color: var(--pink);
}

.nav-links {
    display: flex;
    align-items: center;

    gap: 17px;

    flex-wrap: wrap;
}

.nav-links > a {
    color: var(--muted);

    font-weight: 800;
}

.nav-links > a:hover {
    color: var(--purple);
}

.controls {
    display: flex;
    align-items: center;
    gap: 7px;
}

.language {
    padding: 9px 11px;

    border:
        1px solid var(--border);

    border-radius: 12px;

    background: var(--surface);
    color: var(--text);

    font-weight: 800;
}

.theme-btn {
    width: 42px;
    height: 42px;

    border:
        1px solid var(--border);

    border-radius: 12px;

    background: var(--surface);
    color: var(--text);

    font-size: 18px;
}

/* HERO */

.hero {
    padding: 28px 0 30px;
}

.hero-box {
    min-height: 590px;

    border-radius: 42px;

    padding: 65px;

    position: relative;
    overflow: hidden;

    color: white;

    background:
        radial-gradient(
            circle at 80% 15%,
            rgba(255,255,255,.28),
            transparent 23%
        ),

        radial-gradient(
            circle at 15% 90%,
            rgba(249,115,22,.35),
            transparent 28%
        ),

        linear-gradient(
            135deg,
            #32135c,
            #7c3aed,
            #db2777
        );

    box-shadow:
        0 45px 100px rgba(76,29,149,.28);
}

.hero-content {
    max-width: 720px;

    position: relative;
    z-index: 2;
}

.hero-badge {
    display: inline-block;

    padding: 10px 16px;

    border-radius: 999px;

    background: rgba(255,255,255,.14);

    border:
        1px solid rgba(255,255,255,.25);

    backdrop-filter: blur(12px);

    font-weight: 900;
}

.hero h1 {
    margin: 25px 0 18px;

    font-size:
        clamp(
            48px,
            8vw,
            86px
        );

    line-height: .92;

    letter-spacing: -4px;
}

.hero p {
    max-width: 650px;

    font-size: 19px;

    line-height: 1.7;

    color: #f7f3ff;
}

.hero-buttons {
    margin-top: 27px;

    display: flex;
    gap: 12px;

    flex-wrap: wrap;
}

.hero-shoe {
    position: absolute;

    right: 7%;
    bottom: 50px;

    font-size: 180px;

    transform: rotate(-15deg);

    filter:
        drop-shadow(
            0 30px 25px rgba(0,0,0,.3)
        );

    animation:
        floating 3.5s ease-in-out infinite;
}

@keyframes floating {

    0%,100% {
        transform:
            rotate(-15deg)
            translateY(0);
    }

    50% {
        transform:
            rotate(-7deg)
            translateY(-22px);
    }
}

/* BUTTONS */

.btn {
    border: 0;

    border-radius: 14px;

    padding: 12px 19px;

    display: inline-flex;
    justify-content: center;
    align-items: center;

    font-weight: 900;

    transition:
        transform .2s,
        box-shadow .2s;
}

.btn:hover {
    transform: translateY(-3px);
}

.btn-purple {
    color: white;

    background:
        linear-gradient(
            135deg,
            var(--purple),
            var(--purple2)
        );

    box-shadow:
        0 12px 30px rgba(124,58,237,.25);
}

.btn-white {
    background: white;
    color: var(--purple2);
}

.btn-light {
    background: var(--surface2);
    color: var(--purple2);
}

/* SECTIONS */

.section {
    padding: 70px 0;
}

.section-title {
    margin: 0 0 12px;

    font-size: 39px;

    letter-spacing: -1px;
}

.section-subtitle {
    max-width: 760px;

    margin-bottom: 30px;

    color: var(--muted);

    line-height: 1.75;
}

/* ABOUT */

.about-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(270px,1fr)
        );

    gap: 22px;
}

.about-card {
    padding: 30px;

    border:
        1px solid var(--border);

    border-radius: 25px;

    background: var(--surface);

    box-shadow: var(--shadow);

    line-height: 1.75;
}

.about-card h3 {
    color: var(--purple);

    margin-top: 0;
}

/* PRODUCTS */

.product-toolbar {
    margin-bottom: 25px;

    display: flex;

    gap: 10px;

    flex-wrap: wrap;
}

.search-box {
    flex: 1;

    min-width: 230px;

    padding: 13px 16px;

    border:
        1px solid var(--border);

    border-radius: 14px;

    background: var(--surface);

    color: var(--text);

    outline: none;
}

.products {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(245px,1fr)
        );

    gap: 23px;
}

.product-card {
    overflow: hidden;

    border-radius: 26px;

    border:
        1px solid var(--border);

    background: var(--surface);

    box-shadow: var(--shadow);

    transition:
        transform .25s,
        box-shadow .25s;
}

.product-card:hover {
    transform:
        translateY(-9px)
        rotate(.2deg);

    box-shadow:
        0 30px 70px rgba(76,29,149,.2);
}

.product-image {
    height: 235px;

    display: flex;
    align-items: center;
    justify-content: center;

    overflow: hidden;

    background:
        linear-gradient(
            135deg,
            #ede9fe,
            #fce7f3,
            #dbeafe
        );
}

.product-image img {
    width: 100%;
    height: 100%;

    object-fit: cover;

    transition:
        transform .4s;
}

.product-card:hover
.product-image img {
    transform: scale(1.06);
}

.slipper {
    font-size: 90px;

    transform: rotate(-15deg);

    animation:
        slipperFloat 3s ease-in-out infinite;
}

@keyframes slipperFloat {

    0%,100% {
        transform:
            rotate(-15deg)
            translateY(0);
    }

    50% {
        transform:
            rotate(-9deg)
            translateY(-8px);
    }
}

.product-body {
    padding: 23px;
}

.product-body h3 {
    margin: 0 0 8px;

    font-size: 21px;
}

.description {
    min-height: 58px;

    color: var(--muted);

    line-height: 1.55;
}

.price {
    margin-top: 14px;

    font-size: 25px;

    font-weight: 1000;

    color: var(--purple);
}

.product-info {
    margin-top: 7px;

    color: var(--muted);

    font-size: 14px;
}

.stock {
    margin-top: 12px;

    font-size: 13px;

    font-weight: 950;
}

.good {
    color: #16a34a;
}

.low {
    color: #ca8a04;
}

.out {
    color: #dc2626;
}

/* FOOTER */

.footer {
    margin-top: 40px;

    padding:
        65px
        22px
        30px;

    color: #ded4e9;

    background:
        linear-gradient(
            135deg,
            #211036,
            #3b176d,
            #551b4f
        );
}

.footer-inner {
    max-width: 1200px;

    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(250px,1fr)
        );

    gap: 40px;
}

.footer h3 {
    color: white;
}

.footer p {
    line-height: 1.7;
}

.footer-bottom {
    max-width: 1200px;

    margin: 35px auto 0;

    padding-top: 20px;

    border-top:
        1px solid rgba(255,255,255,.14);

    font-size: 13px;
}

/* LOGIN */

.login-wrap {
    min-height: 80vh;

    display: flex;
    align-items: center;
    justify-content: center;

    padding: 50px 20px;
}

.login-card {
    width: 100%;
    max-width: 440px;

    padding: 35px;

    border-radius: 27px;

    border:
        1px solid var(--border);

    background: var(--surface);

    box-shadow: var(--shadow);
}

/* DASHBOARD */

.dashboard {
    padding: 45px 0 80px;
}

.stats {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(180px,1fr)
        );

    gap: 15px;

    margin: 30px 0;
}

.stat {
    padding: 24px;

    border:
        1px solid var(--border);

    border-radius: 22px;

    background: var(--surface);

    box-shadow: var(--shadow);
}

.stat-number {
    font-size: 35px;

    font-weight: 1000;

    color: var(--purple);
}

.stat-label {
    color: var(--muted);
}

.panel {
    padding: 27px;

    margin-bottom: 25px;

    border:
        1px solid var(--border);

    border-radius: 24px;

    background: var(--surface);

    box-shadow: var(--shadow);
}

.grid-form {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(180px,1fr)
        );

    gap: 15px;
}

.full {
    grid-column: 1 / -1;
}

.form-group {
    margin-bottom: 5px;
}

.form-group label {
    display: block;

    margin-bottom: 7px;

    font-weight: 850;
}

.form-group input,
.form-group textarea,
.form-group select {
    width: 100%;

    padding: 12px;

    border:
        1px solid var(--border);

    border-radius: 11px;

    background: var(--surface);

    color: var(--text);

    outline: none;
}

.form-group textarea {
    min-height: 90px;

    resize: vertical;
}

.product-editor {
    margin-top: 16px;

    padding: 21px;

    border-radius: 18px;

    border:
        1px solid var(--border);

    background:
        rgba(139,92,246,.04);
}

.table-wrap {
    overflow-x: auto;
}

table {
    width: 100%;

    min-width: 750px;

    border-collapse: collapse;
}

th,
td {
    padding: 12px;

    text-align: left;

    border-bottom:
        1px solid var(--border);

    font-size: 13px;
}

th {
    color: var(--purple);
}

.alert {
    max-width: 1200px;

    margin: 15px auto;

    padding: 13px 18px;

    border-radius: 13px;

    background: #ede9fe;

    color: #4c1d95;
}

body.dark .alert {
    background: #2c1d3e;
    color: #ddd6fe;
}

/* MOBILE */

@media(max-width: 850px) {

    .nav-inner {
        flex-direction: column;
    }

    .nav-links {
        justify-content: center;
    }

    .hero-box {
        min-height: 590px;

        padding: 40px 25px;
    }

    .hero h1 {
        font-size: 52px;
    }

    .hero-shoe {
        right: 4%;
        bottom: 15px;

        opacity: .28;

        font-size: 140px;
    }
}

</style>
"""


# ============================================================
# HOME HTML
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

<title>
    PADRON | Filipino Footwear
</title>

{{ style|safe }}

</head>

<body id="page">

<nav class="navbar">

<div class="nav-inner">

<a class="logo" href="/">
    PADRON<span>●</span>
</a>

<div class="nav-links">

<a href="#about">
    {{ t.about }}
</a>

<a href="#products">
    {{ t.products }}
</a>

<a href="#mission">
    {{ t.mission }}
</a>

<a href="#vision">
    {{ t.vision }}
</a>

<a href="#contact">
    {{ t.contact }}
</a>

<a href="/staff/login">
    {{ t.staff }}
</a>

<div class="controls">

<select
    class="language"
    onchange="changeLanguage(this.value)"
>

<option
    value="en"
    {% if language == "en" %}selected{% endif %}
>
🇬🇧 English
</option>

<option
    value="fil"
    {% if language == "fil" %}selected{% endif %}
>
🇵🇭 Filipino
</option>

<option
    value="ceb"
    {% if language == "ceb" %}selected{% endif %}
>
🟦 Cebuano
</option>

</select>

<button
    class="theme-btn"
    onclick="toggleTheme()"
    id="themeButton"
    title="{{ t.theme }}"
>
🌙
</button>

</div>

</div>

</div>

</nav>


{% with messages = get_flashed_messages() %}

{% for message in messages %}

<div class="alert">
    {{ message }}
</div>

{% endfor %}

{% endwith %}


<section class="hero">

<div class="container">

<div class="hero-box">

<div class="hero-content">

<div class="hero-badge">
    {{ t.hero_badge }}
</div>

<h1>
    {{ t.hero_title }}
</h1>

<p>
    {{ t.hero_text }}
</p>

<div class="hero-buttons">

<a
    class="btn btn-white"
    href="#products"
>
    {{ t.explore }} →
</a>

<a
    class="btn"
    href="#about"
    style="
        color:white;
        background:rgba(255,255,255,.14);
        border:1px solid rgba(255,255,255,.25);
    "
>
    {{ t.about }}
</a>

</div>

</div>

<div class="hero-shoe">
    👡
</div>

</div>

</div>

</section>


<section
    class="section"
    id="about"
>

<div class="container">

<h2 class="section-title">
    {{ t.about }}
</h2>

<p class="section-subtitle">
    A family tradition of footwear making rooted
    in Liliw, Laguna.
</p>

<div class="about-grid">

<div class="about-card">

<h3>
    {{ t.story }}
</h3>

<p>
    Golden Zapatillas Corporation is a
    family-owned business established in 2015,
    continuing a family tradition of manufacturing
    high-quality footwear in Liliw, Laguna.
</p>

<p>
    Our goal is to create pairs of shoes that
    showcase the creativity and craftsmanship of
    our artisans: artist painters, beadworkers,
    embroiderers, and shoemakers from Laguna.
</p>

</div>


<div class="about-card">

<h3>
    {{ t.materials }}
</h3>

<p>
    We use locally sourced materials like abaca
    and indigenous fabrics such as Ifugao fabric
    and Inabel to support local suppliers and
    create a Filipino touch in footwear that is
    world-class in quality and durability.
</p>

</div>


<div class="about-card">

<h3>
    {{ t.heritage }}
</h3>

<p>
    Padron is the brand name we are known for.
    The name means "pattern" in Spanish because
    every footwear design begins by creating a
    padron or pattern.
</p>

<p>
    We believe Padron will carry our family
    tradition forward for another 60 years or
    more in the footwear industry.
</p>

</div>

</div>

</div>

</section>


<section
    class="section"
    id="products"
>

<div class="container">

<h2 class="section-title">
    {{ t.products }}
</h2>

<p class="section-subtitle">
    Explore handmade mules, flats, platform
    espadrilles, wedge espadrilles, and the
    Estela interchangeable strap.
</p>

<div class="product-toolbar">

<input
    id="search"
    class="search-box"
    placeholder="🔎 Search footwear..."
    oninput="filterProducts()"
>

</div>

<div
    class="products"
    id="productGrid"
>

{% for product in products %}

<article
    class="product-card"
    data-name="{{ product['name']|lower }}"
>

<div class="product-image">

{% if product["image_url"] %}

<img
    src="{{ product['image_url'] }}"
    alt="{{ product['name'] }}"
    loading="lazy"
>

{% else %}

<div class="slipper">
    👡
</div>

{% endif %}

</div>

<div class="product-body">

<h3>
    {{ product["name"] }}
</h3>

<div class="description">
    {{ product["description"] }}
</div>

{% if product["price"] > 0 %}

<div class="price">
    ₱{{ "%.2f"|format(product["price"]) }}
</div>

{% endif %}

<div class="product-info">

<strong>{{ t.color }}:</strong>

{{ product["color"] or "Various" }}

</div>

<div class="product-info">

<strong>{{ t.sizes }}:</strong>

{{ product["sizes"] or "Various" }}

</div>


{% if product["stock"] <= 0 %}

<div class="stock out">
    {{ t.out_stock }}
</div>

{% elif product["stock"] <= 5 %}

<div class="stock low">
    {{ t.only_left.format(count=product["stock"]) }}
</div>

{% else %}

<div class="stock good">
    ✓ {{ t.in_stock }}
</div>

{% endif %}

</div>

</article>

{% endfor %}

</div>

</div>

</section>


<section
    class="section"
    id="mission"
>

<div class="container">

<div class="about-card">

<h2 class="section-title">
    {{ t.mission_title }}
</h2>

<p>
    To empower Filipino artisans, including
    shoemakers and women artisans skilled in
    handpainting, embroidery, and crochet, by
    creating sustainable, high-quality footwear
    that celebrates local heritage and
    craftsmanship.
</p>

<p>
    We strive to foster economic growth in
    Liliw while preserving our family's legacy
    of footwear making, established in 1963.
</p>

</div>

</div>

</section>


<section
    class="section"
    id="vision"
>

<div class="container">

<div class="about-card">

<h2 class="section-title">
    {{ t.vision_title }}
</h2>

<p>
    To be one of the leading pioneers in
    sustainable, handcrafted footwear,
    incorporating the expertise of shoemakers
    and women artisans skilled in handpainting,
    embroidery, and crochet.
</p>

<p>
    We aim to inspire a new generation of
    artisans, preserve our family's legacy,
    and position Liliw as a center of footwear
    excellence.
</p>

</div>

</div>

</section>


<footer
    class="footer"
    id="contact"
>

<div class="footer-inner">

<div>

<h3>
    PADRON
</h3>

<p>
    {{ t.footer }}
</p>

</div>


<div>

<h3>
    {{ t.contact_title }}
</h3>

<p>
    📍 {{ store_address }}
</p>

<p>
    📱 {{ store_phone }}
</p>

{% if store_email %}

<p>
    ✉️ {{ store_email }}
</p>

{% endif %}

</div>


<div>

<h3>
    {{ t.heritage }}
</h3>

<p>
    Family footwear tradition since 1963.
</p>

<p>
    Liliw, Laguna, Philippines 🇵🇭
</p>

</div>

</div>


<div class="footer-bottom">

© {{ year }} PADRON / Golden Zapatillas Corporation

<br><br>

All rights reserved.

</div>

</footer>


<script>

function changeLanguage(language) {

    const url =
        new URL(
            window.location.href
        );

    url.searchParams.set(
        "lang",
        language
    );

    window.location.href =
        url.toString();
}


function setTheme(theme) {

    const page =
        document.getElementById("page");

    const button =
        document.getElementById("themeButton");

    if (theme === "dark") {

        page.classList.add("dark");

        button.textContent = "☀️";

    } else {

        page.classList.remove("dark");

        button.textContent = "🌙";
    }

    localStorage.setItem(
        "padron-theme",
        theme
    );
}


function toggleTheme() {

    const current =
        localStorage.getItem(
            "padron-theme"
        ) || "light";

    setTheme(
        current === "dark"
            ? "light"
            : "dark"
    );
}


function filterProducts() {

    const search =
        document
            .getElementById("search")
            .value
            .toLowerCase();

    const cards =
        document.querySelectorAll(
            ".product-card"
        );

    cards.forEach(
        function(card) {

            const name =
                card.dataset.name;

            card.style.display =
                name.includes(search)
                    ? ""
                    : "none";
        }
    );
}


(function() {

    const saved =
        localStorage.getItem(
            "padron-theme"
        ) || "light";

    setTheme(saved);

})();

</script>

</body>

</html>
"""


# ============================================================
# LOGIN HTML
# ============================================================

LOGIN_HTML = """
<!doctype html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>
    Staff Login | PADRON
</title>

{{ style|safe }}

</head>

<body>

<nav class="navbar">

<div class="nav-inner">

<a class="logo" href="/">
    PADRON
</a>

<a href="/">
    ← Store
</a>

</div>

</nav>


<div class="login-wrap">

<div class="login-card">

<h1>
    🔐 Staff Login
</h1>

<p style="color:var(--muted)">
    Manage products and inventory.
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
# DASHBOARD HTML
# ============================================================

DASHBOARD_HTML = """
<!doctype html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>
    Staff Dashboard | PADRON
</title>

{{ style|safe }}

</head>

<body id="dashboardBody">

<nav class="navbar">

<div class="nav-inner">

<a class="logo" href="/">
    PADRON
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

<button
    class="theme-btn"
    onclick="toggleTheme()"
    id="themeButton"
>
🌙
</button>

</div>

</div>

</nav>


<main class="dashboard">

<div class="container">

<h1>
    Staff Dashboard
</h1>

<p style="color:var(--muted)">
    Manage products, inventory, and website analytics.
</p>


<div class="stats">

<div class="stat">

<div class="stat-number">
    {{ total_visitors }}
</div>

<div class="stat-label">
    Page Views
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
    Total Stock
</div>

</div>

</div>


<section class="panel">

<h2>
    ➕ Add Product
</h2>

<form
    method="POST"
    action="/staff/product/new"
>

<div class="grid-form">

<div class="form-group">

<label>
    Product Name
</label>

<input
    name="name"
    required
>

</div>

<div class="form-group">

<label>
    Price ₱
</label>

<input
    name="price"
    type="number"
    min="0"
    step="0.01"
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
>

</div>

<div class="form-group">

<label>
    Color
</label>

<input name="color">

</div>

<div class="form-group">

<label>
    Sizes
</label>

<input
    name="sizes"
    placeholder="36, 37, 38, 39, 40"
>

</div>

<div class="form-group">

<label>
    Image
</label>

<select name="image_url">

<option value="{{ image_0 }}">
    Image 0
</option>

<option value="{{ image_1 }}">
    Image 1
</option>

</select>

</div>

<div class="form-group full">

<label>
    Description
</label>

<textarea
    name="description"
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


<section class="panel">

<h2>
    📦 Manage Products
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
    Product Name
</label>

<input
    name="name"
    value="{{ product['name'] }}"
    required
>

</div>

<div class="form-group">

<label>
    Price ₱
</label>

<input
    name="price"
    type="number"
    min="0"
    step="0.01"
    value="{{ product['price'] }}"
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
    Image
</label>

<select name="image_url">

<option
    value="{{ image_0 }}"
    {% if product['image_url'] == image_0 %}
    selected
    {% endif %}
>
Image 0
</option>

<option
    value="{{ image_1 }}"
    {% if product['image_url'] == image_1 %}
    selected
    {% endif %}
>
Image 1
</option>

</select>

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

<div class="form-group full">

<label>
    Description
</label>

<textarea name="description">{{ product['description'] }}</textarea>

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
    onsubmit="return confirm('Delete this product?');"
>

<button
    class="btn"
    style="
        background:#fee2e2;
        color:#dc2626;
    "
>
    Delete Product
</button>

</form>

</div>

{% endfor %}

</section>


<section class="panel">

<h2>
    📊 Visitor Analytics
</h2>

<p style="color:var(--muted)">
    IP addresses are stored as one-way hashes
    rather than readable IP addresses.
</p>

<div class="table-wrap">

<table>

<thead>

<tr>
<th>ID</th>
<th>IP Hash</th>
<th>Device</th>
<th>Browser</th>
<th>Language</th>
<th>Referrer</th>
<th>Visited</th>
</tr>

</thead>

<tbody>

{% for visitor in visitors %}

<tr>

<td>
    #{{ visitor["id"] }}
</td>

<td>
    {{ visitor["ip_hash"] }}
</td>

<td>
    {{ visitor["device"] }}
</td>

<td>
    {{ visitor["browser"] }}
</td>

<td>
    {{ visitor["language"] }}
</td>

<td>
    {{ visitor["referrer"] or "-" }}
</td>

<td>
    {{ visitor["visited_at"] }}
</td>

</tr>

{% else %}

<tr>

<td colspan="7">
    No visitors yet.
</td>

</tr>

{% endfor %}

</tbody>

</table>

</div>

</section>

</div>

</main>


<script>

function setTheme(theme) {

    const body =
        document.getElementById(
            "dashboardBody"
        );

    const button =
        document.getElementById(
            "themeButton"
        );

    if (theme === "dark") {

        body.classList.add("dark");

        button.textContent = "☀️";

    } else {

        body.classList.remove("dark");

        button.textContent = "🌙";
    }

    localStorage.setItem(
        "padron-theme",
        theme
    );
}


function toggleTheme() {

    const current =
        localStorage.getItem(
            "padron-theme"
        ) || "light";

    setTheme(
        current === "dark"
            ? "light"
            : "dark"
    );
}


(function() {

    const saved =
        localStorage.getItem(
            "padron-theme"
        ) || "light";

    setTheme(saved);

})();

</script>

</body>

</html>
"""


# ============================================================
# COMMON TEMPLATE VARIABLES
# ============================================================

@app.context_processor
def inject_globals():

    return {
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "store_phone": STORE_PHONE,
        "store_email": STORE_EMAIL,
        "style": STYLE,
        "year": datetime.now().year,
        "image_0": IMAGE_0,
        "image_1": IMAGE_1,
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    language = current_language()

    record_visitor()

    connection = get_db()

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
        products=products,
        language=language,
        t=TRANSLATIONS[language]
    )


# ============================================================
# STAFF LOGIN
# ============================================================

@app.route(
    "/staff/login",
    methods=["GET", "POST"]
)
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

            return redirect(
                url_for("staff_dashboard")
            )

        flash("Incorrect staff password.")

    return render_template_string(
        LOGIN_HTML
    )


@app.route("/staff/logout")
def staff_logout():

    session.clear()

    return redirect("/")


# ============================================================
# STAFF DASHBOARD
# ============================================================

@app.route("/staff")
@staff_required
def staff_dashboard():

    connection = get_db()

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
        """
        SELECT COUNT(*)
        FROM visitors
        """
    ).fetchone()[0]

    product_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM products
        """
    ).fetchone()[0]

    total_stock = connection.execute(
        """
        SELECT COALESCE(SUM(stock), 0)
        FROM products
        """
    ).fetchone()[0]

    connection.close()

    return render_template_string(
        DASHBOARD_HTML,
        products=products,
        visitors=visitors,
        total_visitors=total_visitors,
        product_count=product_count,
        total_stock=total_stock
    )


# ============================================================
# CREATE PRODUCT
# ============================================================

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

    image_url = request.form.get(
        "image_url",
        IMAGE_0
    )

    if image_url not in (
        IMAGE_0,
        IMAGE_1
    ):
        image_url = IMAGE_0

    connection = get_db()

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

            image_url,

            datetime.now(
                timezone.utc
            ).isoformat()
        )
    )

    connection.commit()
    connection.close()

    flash("Product added successfully.")

    return redirect("/staff")


# ============================================================
# UPDATE PRODUCT
# ============================================================

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

    image_url = request.form.get(
        "image_url",
        IMAGE_0
    )

    if image_url not in (
        IMAGE_0,
        IMAGE_1
    ):
        image_url = IMAGE_0

    active = (
        1
        if request.form.get("active") == "1"
        else 0
    )

    connection = get_db()

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

            image_url,
            active,

            product_id
        )
    )

    connection.commit()
    connection.close()

    flash("Product updated successfully.")

    return redirect("/staff")


# ============================================================
# DELETE PRODUCT
# ============================================================

@app.route(
    "/staff/product/<int:product_id>/delete",
    methods=["POST"]
)
@staff_required
def delete_product(product_id):

    connection = get_db()

    connection.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    connection.commit()
    connection.close()

    flash("Product deleted.")

    return redirect("/staff")


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return """
    <h1>404</h1>
    <p>Page not found.</p>
    <a href="/">Return to PADRON</a>
    """, 404


@app.errorhandler(500)
def server_error(error):

    return """
    <h1>500</h1>
    <p>Something went wrong.</p>
    <a href="/">Return to PADRON</a>
    """, 500


# ============================================================
# INITIALIZE
# ============================================================

init_database()

update_default_images()


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

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
