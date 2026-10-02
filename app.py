import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, render_template_string

app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "padron-change-this-secret")

# ============================================================
# PADRON
# ============================================================

STORE_NAME = "PADRON"
YEAR = 2015

LOGO_FILE = "Image0 (3).jpeg"

ADDRESS = "268 A. Mabini Street, Liliw, Laguna"
PHONE = "0976 1296450"

DB_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "padron.db"
)

# Change these in Render Environment Variables.
STAFF_USERNAME = os.environ.get("PADRON_ADMIN_USER", "staff")
STAFF_PASSWORD = os.environ.get("PADRON_ADMIN_PASSWORD", "change-me")


# ============================================================
# DATABASE
# ============================================================

def db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            description TEXT DEFAULT '',
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            sizes TEXT DEFAULT '',
            color TEXT DEFAULT '',
            material TEXT DEFAULT '',
            active INTEGER DEFAULT 1
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            language TEXT,
            path TEXT,
            created_at TEXT
        )
    """)

    total = connection.execute(
        "SELECT COUNT(*) AS count FROM products"
    ).fetchone()["count"]

    if total == 0:
        products = [
            (
                "Handmade Mule",
                "Mules",
                "Handcrafted footwear inspired by Filipino artistry.",
                0,
                0,
                "35, 36, 37, 38, 39, 40",
                "Natural",
                "Local materials"
            ),
            (
                "Classic Flat",
                "Flats",
                "Elegant handmade flats crafted with care by local artisans.",
                0,
                0,
                "35, 36, 37, 38, 39, 40",
                "Natural",
                "Abaca / Indigenous fabric"
            ),
            (
                "Platform Espadrille",
                "Platform",
                "A handcrafted platform style showcasing Laguna craftsmanship.",
                0,
                0,
                "35, 36, 37, 38, 39, 40",
                "Various",
                "Indigenous fabric"
            ),
            (
                "Wedge Espadrille",
                "Wedges",
                "Handcrafted wedge espadrilles inspired by Filipino heritage.",
                0,
                0,
                "35, 36, 37, 38, 39, 40",
                "Various",
                "Abaca / Inabel"
            ),
            (
                "Estela Interchangeable Strap",
                "Innovation",
                "A continuously evolving interchangeable strap concept.",
                0,
                0,
                "35, 36, 37, 38, 39, 40",
                "Various",
                "Local materials"
            )
        ]

        connection.executemany("""
            INSERT INTO products
            (
                name,
                category,
                description,
                price,
                stock,
                sizes,
                color,
                material
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, products)

    connection.commit()
    connection.close()


init_database()


# ============================================================
# AUTH
# ============================================================

def logged_in():
    return session.get("staff") is True


# ============================================================
# VISITOR ANALYTICS
# ============================================================

def track_visitor():
    try:
        forwarded = request.headers.get("X-Forwarded-For", "")

        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.remote_addr or "Unknown"

        agent = request.headers.get(
            "User-Agent",
            "Unknown"
        )

        language = request.headers.get(
            "Accept-Language",
            "Unknown"
        )

        connection = db()

        connection.execute("""
            INSERT INTO visitors
            (
                ip,
                user_agent,
                language,
                path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            ip,
            agent[:500],
            language[:200],
            request.path[:300],
            datetime.utcnow().isoformat(
                timespec="seconds"
            )
        ))

        connection.commit()
        connection.close()

    except Exception:
        pass


# ============================================================
# SHARED HTML
# ============================================================

BASE = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<meta
    name="theme-color"
    content="#6f4931"
>

<title>{{ title }} | PADRON</title>

<style>

:root {

    --bg: #fffaf5;
    --surface: #ffffff;
    --surface2: #f5e8db;

    --brown-950: #26170f;
    --brown-900: #382218;
    --brown-800: #4d3020;
    --brown-700: #66432e;
    --brown-600: #80583d;
    --brown-500: #a8734e;

    --gold: #d59a54;
    --cream: #fffaf5;

    --text: #382218;
    --muted: #765844;

    --border: rgba(102,67,46,.15);

    --shadow:
        0 20px 60px rgba(65,39,24,.13);

    --shadow2:
        0 35px 90px rgba(65,39,24,.19);
}

body.dark {

    --bg: #17100c;
    --surface: #241812;
    --surface2: #352319;

    --text: #fff2e6;
    --muted: #d1b6a0;

    --border: rgba(255,255,255,.10);

    --shadow:
        0 20px 60px rgba(0,0,0,.35);

    --shadow2:
        0 35px 90px rgba(0,0,0,.45);
}

* {
    box-sizing: border-box;
    scroll-behavior: smooth;
}

html {
    scroll-padding-top: 90px;
}

body {

    margin: 0;

    background:
        radial-gradient(
            circle at 10% 10%,
            rgba(213,154,84,.13),
            transparent 27%
        ),
        radial-gradient(
            circle at 90% 30%,
            rgba(128,88,61,.10),
            transparent 30%
        ),
        var(--bg);

    color: var(--text);

    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    text-align: center;

    overflow-x: hidden;

    transition:
        background .35s,
        color .35s;
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


/* ============================================================
   NAVIGATION
   ============================================================ */

.nav {

    position: fixed;

    z-index: 9999;

    top: 0;
    left: 0;

    width: 100%;

    background:
        rgba(255,250,245,.82);

    backdrop-filter: blur(20px);

    border-bottom:
        1px solid var(--border);

    transition: .3s;
}

.dark .nav {
    background:
        rgba(23,16,12,.84);
}

.nav.scrolled {
    box-shadow:
        0 10px 35px rgba(50,30,20,.10);
}

.nav-inner {

    max-width: 1300px;

    margin: auto;

    min-height: 72px;

    padding:
        10px 20px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 15px;
}

.brand {

    display: flex;

    align-items: center;

    gap: 10px;

    font-weight: 1000;

    letter-spacing: .16em;
}

.brand img {

    width: 44px;
    height: 44px;

    object-fit: contain;

    border-radius: 12px;
}

.nav-links {

    display: flex;

    justify-content: center;

    align-items: center;

    gap: 5px;

    flex-wrap: wrap;
}

.nav-links a {

    padding: 9px 12px;

    border-radius: 999px;

    font-size: .9rem;

    font-weight: 800;

    transition: .2s;
}

.nav-links a:hover {

    background:
        var(--surface2);

    transform:
        translateY(-2px);
}

.mode {

    border:
        1px solid var(--border);

    background:
        var(--surface);

    color:
        var(--text);

    padding:
        9px 13px;

    border-radius:
        999px;

    font-weight:
        900;
}


/* ============================================================
   HERO
   ============================================================ */

.hero {

    min-height: 100vh;

    display: grid;

    place-items: center;

    padding:
        150px 20px 80px;

    position: relative;

    overflow: hidden;
}

.hero-orb {

    position: absolute;

    border-radius: 50%;

    filter: blur(2px);

    pointer-events: none;
}

.orb1 {

    width: 500px;
    height: 500px;

    background:
        rgba(213,154,84,.12);

    left: -220px;
    top: 130px;
}

.orb2 {

    width: 600px;
    height: 600px;

    background:
        rgba(128,88,61,.10);

    right: -300px;
    bottom: -150px;
}

.hero-content {

    max-width: 1050px;

    position: relative;

    z-index: 2;
}

.logo {

    width:
        min(310px, 75vw);

    max-height:
        210px;

    object-fit:
        contain;

    filter:
        drop-shadow(
            0 25px 40px
            rgba(55,34,22,.20)
        );

    animation:
        floating 5s ease-in-out infinite;
}

@keyframes floating {

    0%, 100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-14px);
    }
}

.pill {

    display: inline-flex;

    align-items: center;

    gap: 7px;

    margin-top: 20px;

    padding:
        9px 15px;

    border-radius:
        999px;

    background:
        var(--surface2);

    color:
        var(--brown-700);

    font-weight:
        950;

    font-size:
        .75rem;

    letter-spacing:
        .12em;

    text-transform:
        uppercase;
}

.hero h1 {

    margin:
        22px 0 18px;

    font-size:
        clamp(4rem, 13vw, 10rem);

    line-height:
        .82;

    letter-spacing:
        -.08em;

    font-weight:
        1000;

    background:
        linear-gradient(
            135deg,
            var(--brown-950),
            var(--brown-500),
            var(--gold)
        );

    -webkit-background-clip:
        text;

    background-clip:
        text;

    color:
        transparent;
}

.hero p {

    max-width:
        760px;

    margin:
        0 auto 30px;

    color:
        var(--muted);

    line-height:
        1.85;

    font-size:
        clamp(1rem, 2vw, 1.25rem);
}

.actions {

    display:
        flex;

    justify-content:
        center;

    gap:
        12px;

    flex-wrap:
        wrap;
}

.btn {

    display:
        inline-flex;

    justify-content:
        center;

    align-items:
        center;

    gap:
        7px;

    border:
        0;

    border-radius:
        999px;

    padding:
        14px 23px;

    font-weight:
        950;

    transition:
        .25s;
}

.btn:hover {

    transform:
        translateY(-4px)
        scale(1.02);
}

.btn-primary {

    color:
        white;

    background:
        linear-gradient(
            135deg,
            var(--brown-800),
            var(--brown-500)
        );

    box-shadow:
        0 16px 35px
        rgba(77,48,32,.25);
}

.btn-secondary {

    color:
        var(--text);

    background:
        var(--surface2);

    border:
        1px solid var(--border);
}

.scroll-indicator {

    margin-top:
        50px;

    color:
        var(--muted);

    font-size:
        .8rem;

    animation:
        bounce 2s infinite;
}

@keyframes bounce {

    0%, 100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(8px);
    }
}


/* ============================================================
   SECTIONS
   ============================================================ */

.section {

    max-width:
        1200px;

    margin:
        auto;

    padding:
        100px 20px;
}

.section-title {

    margin:
        10px 0 14px;

    font-size:
        clamp(2.2rem, 6vw, 4.5rem);

    letter-spacing:
        -.055em;

    line-height:
        1;
}

.section-subtitle {

    max-width:
        750px;

    margin:
        0 auto 45px;

    color:
        var(--muted);

    line-height:
        1.8;
}

.reveal {

    opacity:
        0;

    transform:
        translateY(35px);

    transition:
        opacity .8s ease,
        transform .8s ease;
}

.reveal.visible {

    opacity:
        1;

    transform:
        translateY(0);
}


/* ============================================================
   ABOUT
   ============================================================ */

.about {

    max-width:
        950px;

    margin:
        auto;

    padding:
        45px;

    border-radius:
        35px;

    background:
        linear-gradient(
            135deg,
            rgba(155,107,71,.12),
            rgba(213,154,82,.07)
        );

    border:
        1px solid var(--border);

    box-shadow:
        var(--shadow);
}

.about p {

    color:
        var(--muted);

    line-height:
        1.9;
}


/* ============================================================
   FEATURE CARDS
   ============================================================ */

.grid {

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px, 1fr)
        );

    gap:
        20px;
}

.card {

    background:
        var(--surface);

    border:
        1px solid var(--border);

    border-radius:
        28px;

    padding:
        30px;

    box-shadow:
        var(--shadow);

    transition:
        .3s;

    position:
        relative;

    overflow:
        hidden;
}

.card:hover {

    transform:
        translateY(-10px);

    box-shadow:
        var(--shadow2);
}

.card::before {

    content:
        "";

    position:
        absolute;

    width:
        170px;

    height:
        170px;

    border-radius:
        50%;

    right:
        -80px;

    top:
        -80px;

    background:
        rgba(213,154,84,.10);
}

.icon {

    width:
        72px;

    height:
        72px;

    display:
        grid;

    place-items:
        center;

    margin:
        auto;

    border-radius:
        23px;

    background:
        var(--surface2);

    font-size:
        1.9rem;

    transition:
        .3s;
}

.card:hover .icon {

    transform:
        rotate(-6deg)
        scale(1.1);
}

.card h3 {

    margin:
        18px 0 8px;

    font-size:
        1.25rem;
}

.card p {

    color:
        var(--muted);

    line-height:
        1.7;
}


/* ============================================================
   PRODUCTS
   ============================================================ */

.product-toolbar {

    display:
        flex;

    justify-content:
        center;

    align-items:
        center;

    gap:
        10px;

    flex-wrap:
        wrap;

    margin:
        30px auto 35px;
}

.search {

    width:
        min(450px, 90vw);

    padding:
        14px 18px;

    border-radius:
        999px;

    border:
        1px solid var(--border);

    outline:
        none;

    background:
        var(--surface);

    color:
        var(--text);

    box-shadow:
        var(--shadow);
}

.filter {

    border:
        1px solid var(--border);

    background:
        var(--surface);

    color:
        var(--text);

    padding:
        11px 15px;

    border-radius:
        999px;

    font-weight:
        850;
}

.product-card {

    cursor:
        pointer;

    min-height:
        310px;

    display:
        flex;

    flex-direction:
        column;

    justify-content:
        center;
}

.product-card.hidden {

    display:
        none;
}

.product-icon {

    font-size:
        4rem;

    margin-bottom:
        10px;

    transition:
        .3s;
}

.product-card:hover .product-icon {

    transform:
        translateY(-8px)
        rotate(-5deg)
        scale(1.1);
}

.tag {

    display:
        inline-flex;

    align-self:
        center;

    padding:
        6px 11px;

    border-radius:
        999px;

    background:
        var(--surface2);

    color:
        var(--brown-600);

    font-size:
        .7rem;

    font-weight:
        950;

    text-transform:
        uppercase;

    letter-spacing:
        .08em;
}

.product-price {

    margin-top:
        13px;

    color:
        var(--brown-500);

    font-weight:
        1000;

    font-size:
        1.15rem;
}

.stock-badge {

    margin:
        12px auto 0;

    display:
        inline-block;

    font-size:
        .75rem;

    font-weight:
        900;

    padding:
        6px 10px;

    border-radius:
        999px;

    background:
        var(--surface2);
}


/* ============================================================
   MODAL
   ============================================================ */

.modal {

    position:
        fixed;

    inset:
        0;

    z-index:
        20000;

    display:
        none;

    place-items:
        center;

    padding:
        20px;

    background:
        rgba(20,12,8,.70);

    backdrop-filter:
        blur(10px);
}

.modal.open {

    display:
        grid;
}

.modal-box {

    width:
        min(600px, 96vw);

    max-height:
        90vh;

    overflow:
        auto;

    padding:
        35px;

    border-radius:
        30px;

    background:
        var(--surface);

    color:
        var(--text);

    box-shadow:
        0 40px 120px
        rgba(0,0,0,.35);

    animation:
        modalIn .3s ease;
}

@keyframes modalIn {

    from {
        opacity: 0;
        transform: scale(.9) translateY(20px);
    }

    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

.close {

    float:
        right;

    border:
        0;

    background:
        var(--surface2);

    color:
        var(--text);

    width:
        40px;

    height:
        40px;

    border-radius:
        50%;

    font-size:
        1.2rem;
}


/* ============================================================
   CONTACT
   ============================================================ */

.contact {

    max-width:
        none;

    padding:
        90px 20px 25px;

    background:
        var(--brown-900);

    color:
        #fff7ef;
}

.contact p {

    color:
        #d7bca5;

    line-height:
        1.8;
}

.footer {

    max-width:
        900px;

    margin:
        70px auto 0;

    padding:
        25px 10px 10px;

    border-top:
        1px solid rgba(255,255,255,.13);

    color:
        #c8ab93;

    font-size:
        .9rem;
}


/* ============================================================
   STAFF
   ============================================================ */

.staff {

    max-width:
        1250px;

    margin:
        120px auto 70px;

    padding:
        20px;
}

.staff-header {

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

    gap:
        15px;

    flex-wrap:
        wrap;

    margin-bottom:
        25px;
}

.stats {

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(170px, 1fr)
        );

    gap:
        15px;

    margin-bottom:
        25px;
}

.stat {

    padding:
        25px;

    border-radius:
        24px;

    background:
        var(--surface);

    border:
        1px solid var(--border);

    box-shadow:
        var(--shadow);
}

.stat-number {

    font-size:
        2.5rem;

    font-weight:
        1000;

    color:
        var(--brown-500);
}

.table-wrap {

    overflow-x:
        auto;

    border-radius:
        20px;

    border:
        1px solid var(--border);
}

table {

    width:
        100%;

    border-collapse:
        collapse;

    background:
        var(--surface);
}

th,
td {

    padding:
        12px;

    border-bottom:
        1px solid var(--border);

    text-align:
        center;

    vertical-align:
        middle;
}

th {

    background:
        var(--surface2);

    font-weight:
        950;
}

input,
textarea,
select {

    width:
        100%;

    border:
        1px solid var(--border);

    background:
        var(--surface);

    color:
        var(--text);

    padding:
        10px;

    border-radius:
        10px;

    outline:
        none;
}

textarea {

    min-height:
        100px;
}

.form-grid {

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(180px, 1fr)
        );

    gap:
        15px;
}

label {

    display:
        block;

    margin-bottom:
        6px;

    font-weight:
        850;
}


/* ============================================================
   LOGIN
   ============================================================ */

.login {

    min-height:
        100vh;

    display:
        grid;

    place-items:
        center;

    padding:
        120px 20px 60px;
}

.login-box {

    width:
        min(480px, 95vw);

    padding:
        40px;

    border-radius:
        30px;

    background:
        var(--surface);

    border:
        1px solid var(--border);

    box-shadow:
        var(--shadow2);
}

.alert {

    margin:
        15px 0;

    padding:
        12px;

    border-radius:
        12px;

    background:
        #f4d0cc;

    color:
        #7b211a;

    font-weight:
        800;
}


/* ============================================================
   MOBILE
   ============================================================ */

@media (max-width: 780px) {

    .nav-inner {

        flex-direction:
            column;

        padding:
            10px;
    }

    .nav-links {

        display:
            none;
    }

    .hero {

        padding-top:
            80px;
    }

    .about {

        padding:
            28px 20px;
    }

    .section {

        padding:
            75px 16px;
    }

    .staff {

        margin-top:
            50px;
    }
}

</style>

</head>

<body>

<nav class="nav" id="navbar">

<div class="nav-inner">

<a class="brand" href="{{ url_for('index') }}">

<img
    src="{{ url_for('static', filename=logo_file) }}"
    alt="PADRON logo"
    onerror="this.style.display='none'"
>

<span>PADRON</span>

</a>


<div class="nav-links">

<a href="{{ url_for('index') }}#about">
About
</a>

<a href="{{ url_for('index') }}#products">
Products
</a>

<a href="{{ url_for('index') }}#mission">
Mission
</a>

<a href="{{ url_for('index') }}#vision">
Vision
</a>

<a href="{{ url_for('index') }}#contact">
Contact
</a>

{% if staff %}
<a href="{{ url_for('staff_dashboard') }}">
Staff
</a>
{% endif %}

</div>


<button
    class="mode"
    id="modeButton"
    onclick="toggleMode()"
>
🌙 Dark
</button>

</div>

</nav>


{{ content|safe }}


<script>

/* ============================================================
   DARK MODE
   ============================================================ */

function toggleMode() {

    document.body.classList.toggle("dark");

    const dark =
        document.body.classList.contains("dark");

    localStorage.setItem(
        "padron-mode",
        dark ? "dark" : "light"
    );

    document.getElementById(
        "modeButton"
    ).innerText =
        dark ? "☀️ Bright" : "🌙 Dark";
}


if (
    localStorage.getItem("padron-mode")
    === "dark"
) {

    document.body.classList.add("dark");

    const button =
        document.getElementById("modeButton");

    if (button) {
        button.innerText = "☀️ Bright";
    }
}


/* ============================================================
   NAVBAR SCROLL
   ============================================================ */

window.addEventListener("scroll", function() {

    const nav =
        document.getElementById("navbar");

    if (!nav) return;

    nav.classList.toggle(
        "scrolled",
        window.scrollY > 20
    );

});


/* ============================================================
   SCROLL REVEAL
   ============================================================ */

const revealObserver =
    new IntersectionObserver(
        function(entries) {

            entries.forEach(function(entry) {

                if (entry.isIntersecting) {

                    entry.target.classList.add(
                        "visible"
                    );

                }

            });

        },
        {
            threshold: .12
        }
    );


document
    .querySelectorAll(".reveal")
    .forEach(function(element) {

        revealObserver.observe(element);

    });


/* ============================================================
   PRODUCT SEARCH
   ============================================================ */

function filterProducts() {

    const search =
        (
            document.getElementById(
                "productSearch"
            )?.value || ""
        ).toLowerCase();

    const category =
        document.getElementById(
            "categoryFilter"
        )?.value || "all";


    document
        .querySelectorAll(".product-card")
        .forEach(function(card) {

            const name =
                card.dataset.name || "";

            const productCategory =
                card.dataset.category || "";

            const matchesSearch =
                name.includes(search);

            const matchesCategory =
                category === "all"
                ||
                productCategory === category;

            if (
                matchesSearch
                &&
                matchesCategory
            ) {

                card.classList.remove(
                    "hidden"
                );

            } else {

                card.classList.add(
                    "hidden"
                );

            }

        });
}


/* ============================================================
   PRODUCT MODAL
   ============================================================ */

function openProduct(card) {

    const modal =
        document.getElementById(
            "productModal"
        );

    if (!modal) return;

    document.getElementById(
        "modalName"
    ).innerText =
        card.dataset.name;

    document.getElementById(
        "modalCategory"
    ).innerText =
        card.dataset.category;

    document.getElementById(
        "modalDescription"
    ).innerText =
        card.dataset.description;

    document.getElementById(
        "modalSizes"
    ).innerText =
        card.dataset.sizes || "Contact PADRON";

    document.getElementById(
        "modalMaterial"
    ).innerText =
        card.dataset.material || "Local materials";

    document.getElementById(
        "modalColor"
    ).innerText =
        card.dataset.color || "Various";

    document.getElementById(
        "modalPrice"
    ).innerText =
        card.dataset.price;

    document.getElementById(
        "modalStock"
    ).innerText =
        card.dataset.stock;

    modal.classList.add("open");
}


function closeProduct() {

    const modal =
        document.getElementById(
            "productModal"
        );

    if (modal) {
        modal.classList.remove(
            "open"
        );
    }
}


document.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Escape") {
            closeProduct();
        }

    }
);

</script>

</body>
</html>
"""


# ============================================================
# HOME CONTENT
# ============================================================

HOME = r"""

<section class="hero">

<div class="hero-orb orb1"></div>
<div class="hero-orb orb2"></div>

<div class="hero-content">

<img
    class="logo"
    src="{{ url_for('static', filename=logo_file) }}"
    alt="PADRON logo"
    onerror="this.style.display='none'"
>

<div class="pill">
🇵🇭 Liliw, Laguna • Since 2015
</div>

<h1>PADRON</h1>

<p>
Handcrafted Filipino footwear shaped by heritage,
creativity, sustainability, and the hands of local artisans.
</p>

<div class="actions">

<a
    href="#products"
    class="btn btn-primary"
>
Explore Collection ↓
</a>

<a
    href="#about"
    class="btn btn-secondary"
>
Discover Our Story
</a>

</div>

<div class="scroll-indicator">
↓ Scroll to explore
</div>

</div>

</section>


<section
    class="section reveal"
    id="about"
>

<div class="pill">
ABOUT US
</div>

<h2 class="section-title">
A Filipino Story in Every Pair
</h2>

<div class="about">

<p>
Golden Zapatillas Corporation is a family-owned business
established in <strong>2015</strong>, continuing a family
tradition of manufacturing high-quality footwear in
Liliw, Laguna.
</p>

<p>
Our main goal is to create pairs of shoes that showcase
the creativity and craftsmanship of our artisans:
artist painters, beadworkers, embroiderers, and
shoemakers from Laguna.
</p>

<p>
We use locally sourced materials like abaca and indigenous
fabrics such as Ifugao fabric and Inabel to support our
local suppliers and create a Filipino touch in footwear
that is world-class in quality and durability.
</p>

<p>
Padron is the brand name we're known for. The name means
<strong>"pattern"</strong> in Spanish because every footwear
design starts by creating a padron or pattern.
</p>

</div>

</section>


<section
    class="section reveal"
    id="products"
>

<div class="pill">
OUR PRODUCTS
</div>

<h2 class="section-title">
Crafted With Character
</h2>

<p class="section-subtitle">
Explore handmade footwear inspired by Filipino heritage
and Laguna craftsmanship.
</p>


<div class="product-toolbar">

<input
    class="search"
    id="productSearch"
    oninput="filterProducts()"
    placeholder="🔎 Search footwear..."
>

<select
    class="filter"
    id="categoryFilter"
    onchange="filterProducts()"
>

<option value="all">
All styles
</option>

{% for category in categories %}

<option value="{{ category }}">
{{ category }}
</option>

{% endfor %}

</select>

</div>


<div class="grid">

{% for product in products %}

<div
    class="card product-card reveal"
    data-name="{{ product['name']|lower }}"
    data-category="{{ product['category'] }}"
    data-description="{{ product['description'] }}"
    data-sizes="{{ product['sizes'] }}"
    data-material="{{ product['material'] }}"
    data-color="{{ product['color'] }}"
    data-price="{% if product['price'] > 0 %}₱{{ '%.2f'|format(product['price']) }}{% else %}Contact PADRON{% endif %}"
    data-stock="{% if product['stock'] > 0 %}{{ product['stock'] }} available{% else %}Contact store for availability{% endif %}"
    onclick="openProduct(this)"
>

<div class="product-icon">

{% if "Mule" in product["name"] %}
👡
{% elif "Flat" in product["name"] %}
🥿
{% elif "Platform" in product["name"] %}
👠
{% elif "Wedge" in product["name"] %}
👡
{% else %}
✨
{% endif %}

</div>

<span class="tag">
{{ product["category"] or "Footwear" }}
</span>

<h3>
{{ product["name"] }}
</h3>

<p>
{{ product["description"] }}
</p>

<div class="product-price">

{% if product["price"] > 0 %}

₱{{ "%.2f"|format(product["price"]) }}

{% else %}

Price available in store

{% endif %}

</div>

<div class="stock-badge">

{% if product["stock"] > 0 %}

{{ product["stock"] }} in stock

{% else %}

Check availability

{% endif %}

</div>

</div>

{% endfor %}

</div>

</section>


<section
    class="section reveal"
    id="mission"
>

<div class="pill">
MISSION
</div>

<h2 class="section-title">
Empowering Filipino Artisans
</h2>

<div class="about">

<p>
To empower Filipino artisans, including shoemakers,
women artisans skilled in handpainting, embroidery,
and crochet, by creating sustainable, high-quality
footwear that celebrates local heritage and craftsmanship.
</p>

<p>
We aim to foster economic growth in Liliw while preserving
our family's legacy of footwear making, established in
<strong>1963</strong>.
</p>

</div>

</section>


<section
    class="section reveal"
    id="vision"
>

<div class="pill">
VISION
</div>

<h2 class="section-title">
A Future Built on Craftsmanship
</h2>

<div class="about">

<p>
To be one of the leading pioneers in sustainable,
handcrafted footwear, incorporating the expertise of
shoemakers and women artisans skilled in handpainting,
embroidery, and crochet.
</p>

<p>
We envision inspiring a new generation of artisans,
preserving our family's legacy, and positioning Liliw
as a center of footwear excellence.
</p>

</div>

</section>


<section class="section reveal">

<div class="about">

<h2 class="section-title">
Made in Laguna.
Made by Filipino hands.
</h2>

<p>
Every design starts with a pattern.
Every pair carries a story.
</p>

</div>

</section>


<section
    class="contact"
    id="contact"
>

<div>

<div class="pill">
CONTACT
</div>

<h2 class="section-title">
PADRON
</h2>

<p>
📍 {{ address }}
</p>

<p>
📱 {{ phone }}
</p>

<p>
🇵🇭 Liliw, Laguna, Philippines
</p>

<div class="footer">

PADRON • Handcrafted Filipino Footwear

<br><br>

Established 2015

<br><br>

By JHR

</div>

</div>

</section>


<div
    class="modal"
    id="productModal"
    onclick="if(event.target === this) closeProduct()"
>

<div class="modal-box">

<button
    class="close"
    onclick="closeProduct()"
>
×
</button>

<div class="product-icon">
👡
</div>

<div class="tag" id="modalCategory">
Footwear
</div>

<h2 id="modalName">
Product
</h2>

<p id="modalDescription">
Description
</p>

<hr>

<p>
<strong>Sizes:</strong>
<span id="modalSizes"></span>
</p>

<p>
<strong>Material:</strong>
<span id="modalMaterial"></span>
</p>

<p>
<strong>Color:</strong>
<span id="modalColor"></span>
</p>

<p>
<strong>Price:</strong>
<span id="modalPrice"></span>
</p>

<p>
<strong>Availability:</strong>
<span id="modalStock"></span>
</p>

<br>

<a
    href="#contact"
    class="btn btn-primary"
    onclick="closeProduct()"
>
Contact PADRON
</a>

</div>

</div>

"""


# ============================================================
# HOME ROUTE
# ============================================================

@app.route("/")
def index():

    track_visitor()

    connection = db()

    products = connection.execute("""
        SELECT *
        FROM products
        WHERE active = 1
        ORDER BY id ASC
    """).fetchall()

    categories = connection.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE active = 1
        AND category != ''
        ORDER BY category ASC
    """).fetchall()

    connection.close()

    categories = [
        row["category"]
        for row in categories
    ]

    page = BASE.replace(
        "{{ content|safe }}",
        HOME
    )

    return render_template_string(
        page,
        title="Handcrafted Filipino Footwear",
        logo_file=LOGO_FILE,
        address=ADDRESS,
        phone=PHONE,
        products=products,
        categories=categories,
        staff=logged_in()
    )


# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN = r"""

<div class="login">

<div class="login-box">

<img
    src="{{ url_for('static', filename=logo_file) }}"
    alt="PADRON"
    style="
        width:150px;
        height:110px;
        object-fit:contain;
    "
    onerror="this.style.display='none'"
>

<div class="pill">
PRIVATE STAFF AREA
</div>

<h1>
Staff Login
</h1>

{% if error %}

<div class="alert">
{{ error }}
</div>

{% endif %}

<form method="POST">

<label>
Username
</label>

<input
    name="username"
    autocomplete="username"
    required
>

<br><br>

<label>
Password
</label>

<input
    type="password"
    name="password"
    autocomplete="current-password"
    required
>

<br><br>

<button
    class="btn btn-primary"
    type="submit"
>
Enter Dashboard
</button>

</form>

<br>

<a
    class="btn btn-secondary"
    href="{{ url_for('index') }}"
>
← Back to PADRON
</a>

</div>

</div>

"""


@app.route(
    "/staff/login",
    methods=["GET", "POST"]
)
def staff_login():

    if logged_in():
        return redirect(
            url_for("staff_dashboard")
        )

    error = None

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
            and
            password == STAFF_PASSWORD
        ):

            session["staff"] = True

            return redirect(
                url_for("staff_dashboard")
            )

        error = "Incorrect username or password."

    page = BASE.replace(
        "{{ content|safe }}",
        LOGIN
    )

    return render_template_string(
        page,
        title="Staff Login",
        logo_file=LOGO_FILE,
        staff=False,
        error=error
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

DASHBOARD = r"""

<div class="staff">

<div class="staff-header">

<div>

<div class="pill">
PADRON MANAGEMENT
</div>

<h1 class="section-title">
Staff Dashboard
</h1>

<p style="color:var(--muted)">
Manage products, stock and website activity.
</p>

</div>

<div>

<a
    href="{{ url_for('index') }}"
    class="btn btn-secondary"
>
View Store
</a>

<a
    href="{{ url_for('staff_logout') }}"
    class="btn btn-primary"
>
Logout
</a>

</div>

</div>


<div class="stats">

<div class="stat">

<div class="stat-number">
{{ total_views }}
</div>

Total Views

</div>


<div class="stat">

<div class="stat-number">
{{ unique_ips }}
</div>

Unique IPs

</div>


<div class="stat">

<div class="stat-number">
{{ product_count }}
</div>

Products

</div>


<div class="stat">

<div class="stat-number">
{{ total_stock }}
</div>

Total Stock

</div>

</div>


<div class="card">

<h2>
➕ Add Product
</h2>

<form
    method="POST"
    action="{{ url_for('add_product') }}"
>

<div class="form-grid">

<div>
<label>
Product Name
</label>

<input
    name="name"
    required
>
</div>


<div>
<label>
Category
</label>

<input
    name="category"
>
</div>


<div>
<label>
Price
</label>

<input
    type="number"
    min="0"
    step="0.01"
    name="price"
    value="0"
>
</div>


<div>
<label>
Stock
</label>

<input
    type="number"
    min="0"
    name="stock"
    value="0"
>
</div>


<div>
<label>
Sizes
</label>

<input
    name="sizes"
    placeholder="35, 36, 37..."
>
</div>


<div>
<label>
Color
</label>

<input
    name="color"
>
</div>


<div>
<label>
Material
</label>

<input
    name="material"
>
</div>

</div>

<br>

<label>
Description
</label>

<textarea
    name="description"
></textarea>

<br><br>

<button
    class="btn btn-primary"
>
Add Product
</button>

</form>

</div>


<br>


<div class="card">

<h2>
📦 Inventory
</h2>

<div class="table-wrap">

<table>

<thead>

<tr>

<th>
Product
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
Sizes
</th>

<th>
Color
</th>

<th>
Material
</th>

<th>
Save
</th>

</tr>

</thead>

<tbody>

{% for product in products %}

<tr>

<form
    method="POST"
    action="{{ url_for(
        'update_product',
        product_id=product['id']
    ) }}"
>

<td>

<input
    name="name"
    value="{{ product['name'] }}"
    required
>

</td>


<td>

<input
    name="category"
    value="{{ product['category'] }}"
>

</td>


<td>

<input
    type="number"
    min="0"
    step="0.01"
    name="price"
    value="{{ product['price'] }}"
>

</td>


<td>

<input
    type="number"
    min="0"
    name="stock"
    value="{{ product['stock'] }}"
>

</td>


<td>

<input
    name="sizes"
    value="{{ product['sizes'] }}"
>

</td>


<td>

<input
    name="color"
    value="{{ product['color'] }}"
>

</td>


<td>

<input
    name="material"
    value="{{ product['material'] }}"
>

</td>


<td>

<button
    class="btn btn-primary"
    type="submit"
>
Save
</button>

</td>

</form>

</tr>

{% endfor %}

</tbody>

</table>

</div>

</div>


<br>


<div class="card">

<h2>
👁 Visitor Activity
</h2>

<p style="color:var(--muted)">
Recent visitor information available to staff.
</p>

<div class="table-wrap">

<table>

<thead>

<tr>

<th>
IP
</th>

<th>
Device / Browser
</th>

<th>
Language
</th>

<th>
Page
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
{{ visitor["ip"] }}
</td>

<td style="max-width:350px">
{{ visitor["user_agent"] }}
</td>

<td>
{{ visitor["language"] }}
</td>

<td>
{{ visitor["path"] }}
</td>

<td>
{{ visitor["created_at"] }}
</td>

</tr>

{% endfor %}

</tbody>

</table>

</div>

</div>

</div>

"""


@app.route("/staff")
def staff_dashboard():

    if not logged_in():
        return redirect(
            url_for("staff_login")
        )

    connection = db()

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY id ASC
    """).fetchall()

    visitors = connection.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 200
    """).fetchall()

    total_views = connection.execute("""
        SELECT COUNT(*) AS total
        FROM visitors
    """).fetchone()["total"]

    unique_ips = connection.execute("""
        SELECT COUNT(DISTINCT ip) AS total
        FROM visitors
    """).fetchone()["total"]

    product_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM products
    """).fetchone()["total"]

    total_stock = connection.execute("""
        SELECT COALESCE(SUM(stock), 0) AS total
        FROM products
    """).fetchone()["total"]

    connection.close()

    page = BASE.replace(
        "{{ content|safe }}",
        DASHBOARD
    )

    return render_template_string(
        page,
        title="Staff Dashboard",
        logo_file=LOGO_FILE,
        staff=True,
        products=products,
        visitors=visitors,
        total_views=total_views,
        unique_ips=unique_ips,
        product_count=product_count,
        total_stock=total_stock
    )


# ============================================================
# ADD PRODUCT
# ============================================================

@app.route(
    "/staff/product/add",
    methods=["POST"]
)
def add_product():

    if not logged_in():
        return redirect(
            url_for("staff_login")
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    if not name:
        return redirect(
            url_for("staff_dashboard")
        )

    try:
        price = max(
            0,
            float(
                request.form.get(
                    "price",
                    "0"
                )
            )
        )
    except ValueError:
        price = 0

    try:
        stock = max(
            0,
            int(
                request.form.get(
                    "stock",
                    "0"
                )
            )
        )
    except ValueError:
        stock = 0

    connection = db()

    connection.execute("""
        INSERT INTO products
        (
            name,
            category,
            description,
            price,
            stock,
            sizes,
            color,
            material
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        request.form.get(
            "category",
            ""
        ).strip(),
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
            "material",
            ""
        ).strip()
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("staff_dashboard")
    )


# ============================================================
# UPDATE PRODUCT
# ============================================================

@app.route(
    "/staff/product/<int:product_id>/update",
    methods=["POST"]
)
def update_product(product_id):

    if not logged_in():
        return redirect(
            url_for("staff_login")
        )

    try:
        price = max(
            0,
            float(
                request.form.get(
                    "price",
                    "0"
                )
            )
        )
    except ValueError:
        price = 0

    try:
        stock = max(
            0,
            int(
                request.form.get(
                    "stock",
                    "0"
                )
            )
        )
    except ValueError:
        stock = 0

    connection = db()

    connection.execute("""
        UPDATE products
        SET
            name = ?,
            category = ?,
            price = ?,
            stock = ?,
            sizes = ?,
            color = ?,
            material = ?
        WHERE id = ?
    """, (
        request.form.get(
            "name",
            ""
        ).strip(),

        request.form.get(
            "category",
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
            "material",
            ""
        ).strip(),

        product_id
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("staff_dashboard")
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "store": STORE_NAME,
        "year": YEAR
    }


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return redirect(
        url_for("index")
    )


# ============================================================
# START
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
        debug=False
    )
