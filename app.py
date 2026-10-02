import os
import sqlite3
from functools import wraps
from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string

app = Flask(__name__)

# ============================================================
# PADRON CONFIG
# ============================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "CHANGE_THIS_PADRON_SECRET_KEY"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "padron.db")

STORE_NAME = "PADRON"
STORE_ADDRESS = "268 A. Mabini Street, Liliw, Laguna"
STORE_PHONE = "0976 1296450"

STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "staff")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "padron2026")


# ============================================================
# DATABASE
# ============================================================

def db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():

    connection = db()

    connection.execute("""
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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            language TEXT,
            page TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    count = connection.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count == 0:

        products = [
            (
                "Handmade Mule",
                "Mules",
                "A handcrafted Filipino mule inspired by the creativity of Laguna artisans.",
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
                "A refined handmade flat designed with Filipino craftsmanship.",
                0,
                0,
                "35,36,37,38,39,40",
                "Earth",
                "Inabel",
                1
            ),
            (
                "Platform Espadrille",
                "Platform",
                "A contemporary platform silhouette with locally inspired details.",
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
                "A statement wedge celebrating the heritage and artistry of Liliw.",
                0,
                0,
                "35,36,37,38,39,40",
                "Brown",
                "Ifugao Fabric",
                0
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
                material,
                featured
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, products)

    connection.commit()
    connection.close()


init_database()


# ============================================================
# STAFF AUTH
# ============================================================

def staff_required(function):

    @wraps(function)
    def protected(*args, **kwargs):

        if not session.get("staff_logged_in"):
            return redirect(url_for("staff_login"))

        return function(*args, **kwargs)

    return protected


# ============================================================
# VISITOR ANALYTICS
# ============================================================

@app.before_request
def visitor_tracking():

    if request.path.startswith("/staff"):
        return

    if request.path.startswith("/api"):
        return

    try:

        connection = db()

        forwarded = request.headers.get(
            "X-Forwarded-For",
            ""
        )

        ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.remote_addr
        )

        connection.execute("""
            INSERT INTO visitors
            (
                ip,
                user_agent,
                language,
                page
            )
            VALUES (?, ?, ?, ?)
        """, (
            ip,
            request.headers.get("User-Agent", "")[:500],
            request.headers.get("Accept-Language", "")[:200],
            request.path[:200]
        ))

        connection.commit()
        connection.close()

    except Exception:
        pass


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    connection = db()

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY featured DESC, id DESC
    """).fetchall()

    connection.close()

    return render_template_string(
        HOME_PAGE,
        products=products,
        store_name=STORE_NAME,
        store_address=STORE_ADDRESS,
        store_phone=STORE_PHONE
    )


# ============================================================
# STAFF LOGIN
# ============================================================

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == STAFF_USERNAME
            and password == STAFF_PASSWORD
        ):

            session["staff_logged_in"] = True
            session["staff_username"] = username

            return redirect(
                url_for("staff_dashboard")
            )

        error = "Incorrect username or password."

    return render_template_string(
        LOGIN_PAGE,
        error=error
    )


@app.route("/staff/logout")
def staff_logout():

    session.clear()

    return redirect(url_for("home"))


# ============================================================
# STAFF DASHBOARD
# ============================================================

@app.route("/staff")
@staff_required
def staff_dashboard():

    connection = db()

    products = connection.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    visitors = connection.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 100
    """).fetchall()

    total_visitors = connection.execute(
        "SELECT COUNT(*) FROM visitors"
    ).fetchone()[0]

    total_stock = connection.execute(
        "SELECT COALESCE(SUM(stock), 0) FROM products"
    ).fetchone()[0]

    low_stock = connection.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE stock <= 5
    """).fetchone()[0]

    connection.close()

    return render_template_string(
        STAFF_PAGE,
        products=products,
        visitors=visitors,
        total_visitors=total_visitors,
        total_stock=total_stock,
        low_stock=low_stock
    )


# ============================================================
# PRODUCT API
# ============================================================

@app.route("/api/products", methods=["POST"])
@staff_required
def create_product():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    if not name:
        return jsonify({
            "success": False,
            "message": "Product name is required."
        }), 400

    try:

        price = float(
            data.get("price", 0)
        )

        stock = int(
            data.get("stock", 0)
        )

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid price or stock."
        }), 400

    connection = db()

    cursor = connection.execute("""
        INSERT INTO products
        (
            name,
            category,
            description,
            price,
            stock,
            sizes,
            color,
            material,
            featured
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        data.get("category", "Footwear"),
        data.get("description", ""),
        price,
        stock,
        data.get("sizes", ""),
        data.get("color", ""),
        data.get("material", ""),
        1 if data.get("featured") else 0
    ))

    connection.commit()

    product_id = cursor.lastrowid

    connection.close()

    return jsonify({
        "success": True,
        "id": product_id
    })


@app.route(
    "/api/products/<int:product_id>",
    methods=["PUT"]
)
@staff_required
def edit_product(product_id):

    data = request.get_json(silent=True) or {}

    try:

        price = float(
            data.get("price", 0)
        )

        stock = int(
            data.get("stock", 0)
        )

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid price or stock."
        }), 400

    connection = db()

    result = connection.execute("""
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
        data.get("category", "Footwear"),
        data.get("description", ""),
        price,
        stock,
        data.get("sizes", ""),
        data.get("color", ""),
        data.get("material", ""),
        1 if data.get("featured") else 0,
        product_id
    ))

    connection.commit()
    connection.close()

    if result.rowcount == 0:

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    return jsonify({
        "success": True
    })


@app.route(
    "/api/products/<int:product_id>",
    methods=["DELETE"]
)
@staff_required
def remove_product(product_id):

    connection = db()

    result = connection.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    connection.commit()
    connection.close()

    if result.rowcount == 0:

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    return jsonify({
        "success": True
    })


@app.route(
    "/api/visitors/clear",
    methods=["POST"]
)
@staff_required
def clear_visitors():

    connection = db()

    connection.execute(
        "DELETE FROM visitors"
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True
    })


# ============================================================
# HOME PAGE
# ============================================================

HOME_PAGE = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>PADRON — Filipino Handcrafted Footwear</title>

<style>

@import url(
    'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap'
);

:root {

    --bg: #f5ede3;
    --cream: #fffaf4;
    --cream2: #ead9c7;

    --brown: #75452d;
    --brown2: #a86d49;

    --dark: #2e1c14;
    --muted: #806b5b;

    --gold: #c99b62;

    --border: rgba(91, 54, 35, .13);

    --shadow:
        0 25px 80px rgba(83, 50, 30, .12);

    --radius: 28px;
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {

    margin: 0;

    color: var(--dark);

    background:
        radial-gradient(
            circle at 10% 0%,
            rgba(211, 165, 113, .25),
            transparent 30%
        ),
        radial-gradient(
            circle at 90% 15%,
            rgba(169, 111, 76, .16),
            transparent 28%
        ),
        var(--bg);

    font-family: "DM Sans", sans-serif;

    text-align: center;

    transition:
        background .4s,
        color .4s;
}

body.dark {

    --bg: #1e1510;
    --cream: #2b1e17;
    --cream2: #3b291f;

    --dark: #fff2e4;
    --muted: #c9ae99;

    --brown: #d49a6e;
    --brown2: #e2b58e;

    --border: rgba(255,255,255,.1);

    --shadow:
        0 25px 80px rgba(0,0,0,.3);
}

a {
    color: inherit;
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

/* NAV */

.nav {

    position: sticky;

    top: 0;

    z-index: 100;

    backdrop-filter: blur(20px);

    background:
        color-mix(
            in srgb,
            var(--cream),
            transparent 13%
        );

    border-bottom:
        1px solid var(--border);
}

.nav-inner {

    max-width: 1250px;

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

    font-weight: 800;

    letter-spacing: 4px;

    white-space: nowrap;
}

.brand img {

    width: 44px;
    height: 44px;

    object-fit: contain;

    border-radius: 12px;
}

.nav-links {

    display: flex;

    align-items: center;

    justify-content: center;

    gap: 5px;

    flex-wrap: wrap;
}

.nav-link,
.nav-btn {

    border: 0;

    background: transparent;

    text-decoration: none;

    color: var(--dark);

    padding: 9px 13px;

    border-radius: 999px;

    transition: .25s;
}

.nav-link:hover,
.nav-btn:hover {

    background: var(--cream2);

    transform: translateY(-2px);
}

/* HERO */

.hero {

    min-height: 88vh;

    display: flex;

    align-items: center;

    justify-content: center;

    padding: 70px 20px 100px;

    position: relative;

    overflow: hidden;
}

.hero::before {

    content: "";

    position: absolute;

    width: 500px;
    height: 500px;

    border-radius: 50%;

    background:
        radial-gradient(
            circle,
            rgba(197, 143, 90, .18),
            transparent 70%
        );

    animation: pulse 7s infinite alternate;
}

@keyframes pulse {

    from {
        transform: scale(.8);
    }

    to {
        transform: scale(1.25);
    }
}

.hero-content {

    position: relative;

    max-width: 950px;

    margin: auto;
}

.hero-logo {

    width: 155px;
    height: 155px;

    object-fit: contain;

    filter:
        drop-shadow(
            0 18px 30px rgba(75,45,28,.2)
        );

    animation:
        float 5s ease-in-out infinite;
}

@keyframes float {

    0%,100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-13px);
    }
}

.eyebrow {

    display: inline-flex;

    align-items: center;

    gap: 8px;

    margin-top: 25px;

    padding: 9px 17px;

    border-radius: 999px;

    background: var(--cream);

    border: 1px solid var(--border);

    color: var(--brown);

    font-weight: 700;

    font-size: 13px;

    letter-spacing: 1px;

    box-shadow: var(--shadow);
}

.hero h1 {

    font-family:
        "Playfair Display",
        serif;

    font-size:
        clamp(65px, 12vw, 145px);

    line-height: .84;

    letter-spacing: -7px;

    margin: 25px 0 20px;

    background:
        linear-gradient(
            120deg,
            var(--dark),
            var(--brown2)
        );

    -webkit-background-clip: text;

    color: transparent;
}

.hero-text {

    max-width: 700px;

    margin: auto;

    color: var(--muted);

    line-height: 1.9;

    font-size: 18px;
}

.hero-buttons {

    margin-top: 32px;

    display: flex;

    justify-content: center;

    gap: 12px;

    flex-wrap: wrap;
}

.btn {

    display: inline-flex;

    align-items: center;

    justify-content: center;

    gap: 8px;

    border: 1px solid var(--border);

    border-radius: 999px;

    padding: 14px 23px;

    text-decoration: none;

    font-weight: 800;

    transition: .3s;
}

.btn:hover {

    transform:
        translateY(-5px)
        scale(1.025);
}

.primary {

    color: white;

    background:
        linear-gradient(
            135deg,
            var(--brown),
            var(--brown2)
        );

    box-shadow:
        0 14px 30px
        rgba(113, 68, 43, .2);
}

.secondary {

    background: var(--cream);

    color: var(--dark);
}

/* SECTION */

.section {

    padding: 105px 20px;
}

.section-inner {

    max-width: 1180px;

    margin: auto;
}

.section-tag {

    color: var(--brown);

    font-weight: 800;

    letter-spacing: 2px;

    text-transform: uppercase;

    font-size: 12px;
}

.section-title {

    font-family:
        "Playfair Display",
        serif;

    font-size:
        clamp(42px, 7vw, 75px);

    line-height: 1;

    margin: 12px 0 20px;

    letter-spacing: -2px;
}

.section-subtitle {

    max-width: 760px;

    margin: auto;

    color: var(--muted);

    line-height: 1.9;
}

/* STORY */

.story-grid {

    margin-top: 55px;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(240px, 1fr)
        );

    gap: 20px;
}

.story-card {

    padding: 34px;

    border:
        1px solid var(--border);

    border-radius: var(--radius);

    background: var(--cream);

    box-shadow: var(--shadow);

    transition: .35s;
}

.story-card:hover {

    transform:
        translateY(-10px)
        rotate(-.4deg);
}

.story-icon {

    width: 60px;
    height: 60px;

    margin: auto auto 20px;

    display: grid;

    place-items: center;

    border-radius: 20px;

    background: var(--cream2);

    font-size: 28px;
}

.story-card h3 {

    color: var(--brown);

    font-size: 21px;
}

.story-card p {

    color: var(--muted);

    line-height: 1.8;
}

/* PRODUCTS */

.products-section {

    background:
        linear-gradient(
            180deg,
            transparent,
            rgba(210,165,116,.1)
        );
}

.filters {

    margin: 45px auto;

    display: flex;

    justify-content: center;

    gap: 8px;

    flex-wrap: wrap;
}

.filter {

    border: 1px solid var(--border);

    background: var(--cream);

    color: var(--dark);

    border-radius: 999px;

    padding: 10px 17px;

    transition: .25s;
}

.filter.active,
.filter:hover {

    color: white;

    background: var(--brown);
}

.search {

    width: min(400px, 90%);

    margin: 0 auto 35px;

    display: block;

    border:
        1px solid var(--border);

    background: var(--cream);

    color: var(--dark);

    border-radius: 999px;

    padding: 14px 20px;

    outline: none;
}

.products {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(245px, 1fr)
        );

    gap: 24px;

    text-align: center;
}

.product {

    position: relative;

    overflow: hidden;

    padding: 18px;

    border:
        1px solid var(--border);

    border-radius: 32px;

    background: var(--cream);

    box-shadow: var(--shadow);

    transition:
        transform .4s,
        opacity .3s;
}

.product:hover {

    transform:
        translateY(-10px)
        rotate(-.6deg);
}

.product-art {

    height: 210px;

    display: grid;

    place-items: center;

    border-radius: 25px;

    background:
        radial-gradient(
            circle at 50% 40%,
            rgba(201,155,98,.45),
            transparent 28%
        ),
        linear-gradient(
            135deg,
            var(--cream2),
            transparent
        );

    font-size: 82px;
}

.product h3 {

    margin:
        22px 0 7px;

    font-family:
        "Playfair Display",
        serif;

    font-size: 25px;
}

.product p {

    color: var(--muted);

    line-height: 1.7;

    min-height: 60px;
}

.product-meta {

    display: flex;

    justify-content: center;

    gap: 7px;

    flex-wrap: wrap;
}

.pill {

    padding: 7px 11px;

    border-radius: 999px;

    background: var(--cream2);

    color: var(--muted);

    font-size: 12px;

    font-weight: 700;
}

.featured {

    position: absolute;

    top: 25px;

    left: 25px;

    z-index: 2;

    background: var(--brown);

    color: white;

    padding: 7px 11px;

    border-radius: 999px;

    font-size: 11px;

    font-weight: 800;
}

/* MISSION */

.mission {

    background: var(--cream2);
}

.quote {

    max-width: 900px;

    margin: 50px auto 0;

    font-family:
        "Playfair Display",
        serif;

    font-size:
        clamp(25px, 4vw, 42px);

    line-height: 1.4;

    color: var(--brown);
}

/* CONTACT */

.contact {

    padding: 100px 20px;

    background: var(--cream);
}

.contact-box {

    max-width: 850px;

    margin: auto;

    padding: 55px 30px;

    border:
        1px solid var(--border);

    border-radius: 35px;

    box-shadow: var(--shadow);
}

.contact-box h2 {

    font-family:
        "Playfair Display",
        serif;

    font-size: 55px;

    margin: 0 0 20px;
}

.contact-line {

    color: var(--muted);

    margin: 10px 0;
}

/* FOOTER */

footer {

    padding: 35px 20px;

    color: var(--muted);

    background: var(--cream);

    border-top:
        1px solid var(--border);
}

.by {

    margin-top: 8px;

    font-size: 12px;

    letter-spacing: 2px;
}

/* REVEAL */

.reveal {

    opacity: 0;

    transform: translateY(25px);

    transition:
        opacity .8s,
        transform .8s;
}

.reveal.visible {

    opacity: 1;

    transform: translateY(0);
}

/* TOAST */

#toast {

    position: fixed;

    z-index: 1000;

    bottom: 25px;

    left: 50%;

    transform:
        translate(-50%, 100px);

    background: var(--dark);

    color: var(--bg);

    padding: 13px 20px;

    border-radius: 999px;

    transition: .35s;

    box-shadow: var(--shadow);
}

#toast.show {

    transform:
        translate(-50%, 0);
}

/* MOBILE */

@media(max-width: 760px) {

    .nav-inner {

        flex-direction: column;

    }

    .nav-links {

        width: 100%;
    }

    .hero {

        min-height: 75vh;

        padding-top: 50px;
    }

    .hero h1 {

        letter-spacing: -4px;
    }

    .section {

        padding: 75px 18px;
    }

}

</style>

</head>


<body>


<!-- NAV -->

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

<a
    class="nav-link"
    href="#about"
    data-en="About"
    data-fil="Tungkol"
>
About
</a>

<a
    class="nav-link"
    href="#products"
    data-en="Collection"
    data-fil="Koleksyon"
>
Collection
</a>

<a
    class="nav-link"
    href="#mission"
    data-en="Our Vision"
    data-fil="Ating Bisyon"
>
Our Vision
</a>

<a
    class="nav-link"
    href="#contact"
    data-en="Contact"
    data-fil="Kontak"
>
Contact
</a>

<a
    class="nav-link"
    href="/staff/login"
>
Staff
</a>

<button
    class="nav-btn"
    onclick="toggleLanguage()"
    id="languageButton"
>
🇵🇭 Filipino
</button>

<button
    class="nav-btn"
    onclick="toggleDark()"
    id="themeButton"
>
🌙
</button>

</div>

</div>

</nav>


<!-- HERO -->

<section class="hero">

<div class="hero-content reveal">

<img
    class="hero-logo"
    src="{{ url_for('static', filename='Image0 (3).jpeg') }}"
    onerror="this.style.display='none'"
    alt="PADRON"
>

<div
    class="eyebrow"
    data-en="✦ Handcrafted in Liliw, Laguna"
    data-fil="✦ Gawang-kamay sa Liliw, Laguna"
>
✦ Handcrafted in Liliw, Laguna
</div>

<h1>PADRON</h1>

<p
    class="hero-text"
    data-en="Where Filipino heritage meets contemporary footwear. Crafted with creativity, patience and the hands of local artisans."
    data-fil="Kung saan nagsasama ang kulturang Pilipino at makabagong footwear. Ginawa nang may pagkamalikhain, tiyaga at husay ng mga lokal na artisan."
>
Where Filipino heritage meets contemporary footwear.
Crafted with creativity, patience and the hands of local artisans.
</p>

<div class="hero-buttons">

<a
    href="#products"
    class="btn primary"
    data-en="Explore Collection ↓"
    data-fil="Tingnan ang Koleksyon ↓"
>
Explore Collection ↓
</a>

<a
    href="#about"
    class="btn secondary"
    data-en="Discover PADRON"
    data-fil="Tuklasin ang PADRON"
>
Discover PADRON
</a>

</div>

</div>

</section>


<!-- ABOUT -->

<section
    class="section reveal"
    id="about"
>

<div class="section-inner">

<div
    class="section-tag"
    data-en="Our Story"
    data-fil="Ang Aming Kuwento"
>
Our Story
</div>

<h2
    class="section-title"
    data-en="Made with meaning."
    data-fil="Ginawa nang may kahulugan."
>
Made with meaning.
</h2>

<p
    class="section-subtitle"
>
Golden Zapatillas Corporation is a family-owned business
established in <strong>2015</strong>, continuing a family
tradition of manufacturing high-quality footwear in
Liliw, Laguna.

<br><br>

Our artisans include artist painters, beadworkers,
embroiderers and shoemakers. We use locally sourced
materials such as abaca, Ifugao fabric and Inabel to
support Filipino suppliers and create footwear with a
distinct Filipino touch.
</p>


<div class="story-grid">

<div class="story-card">

<div class="story-icon">
🎨
</div>

<h3
    data-en="Artistry"
    data-fil="Sining"
>
Artistry
</h3>

<p
    data-en="Every piece reflects the creativity and skill of Filipino artisans."
    data-fil="Bawat piraso ay sumasalamin sa pagkamalikhain at husay ng mga Pilipinong artisan."
>
Every piece reflects the creativity and skill of Filipino artisans.
</p>

</div>


<div class="story-card">

<div class="story-icon">
🌿
</div>

<h3
    data-en="Local Materials"
    data-fil="Lokal na Materyales"
>
Local Materials
</h3>

<p>
Abaca, Ifugao fabric and Inabel connect every design
to Filipino communities and traditions.
</p>

</div>


<div class="story-card">

<div class="story-icon">
🧵
</div>

<h3
    data-en="Craftsmanship"
    data-fil="Pagkakayari"
>
Craftsmanship
</h3>

<p>
From pattern to finished footwear, every stage is
shaped by human hands and experience.
</p>

</div>


<div class="story-card">

<div class="story-icon">
✨
</div>

<h3>
PADRON
</h3>

<p>
"Padron" means "pattern" in Spanish — the beginning
of every footwear design.
</p>

</div>

</div>

</div>

</section>


<!-- PRODUCTS -->

<section
    class="section products-section reveal"
    id="products"
>

<div class="section-inner">

<div class="section-tag">
PADRON COLLECTION
</div>

<h2
    class="section-title"
    data-en="Crafted to be remembered."
    data-fil="Ginawang hindi malilimutan."
>
Crafted to be remembered.
</h2>

<p
    class="section-subtitle"
    data-en="Explore our handcrafted footwear categories."
    data-fil="Tuklasin ang aming mga handcrafted footwear."
>
Explore our handcrafted footwear categories.
</p>


<input
    id="search"
    class="search"
    type="search"
    placeholder="Search the collection..."
    oninput="filterProducts()"
>


<div class="filters">

<button
    class="filter active"
    onclick="setFilter('all', this)"
>
All
</button>

<button
    class="filter"
    onclick="setFilter('Mules', this)"
>
Mules
</button>

<button
    class="filter"
    onclick="setFilter('Flats', this)"
>
Flats
</button>

<button
    class="filter"
    onclick="setFilter('Platform', this)"
>
Platform
</button>

<button
    class="filter"
    onclick="setFilter('Wedges', this)"
>
Wedges
</button>

</div>


<div class="products" id="productsGrid">

{% for product in products %}

<article
    class="product"
    data-category="{{ product.category }}"
    data-name="{{ product.name|lower }}"
>

{% if product.featured %}

<div class="featured">
FEATURED
</div>

{% endif %}


<div class="product-art">

{% if "wedge" in product.name.lower() %}
👡
{% elif "flat" in product.name.lower() %}
🥿
{% elif "mule" in product.name.lower() %}
🩴
{% else %}
👞
{% endif %}

</div>


<h3>
{{ product.name }}
</h3>


<p>
{{ product.description }}
</p>


<div class="product-meta">

<span class="pill">
{{ product.category }}
</span>

{% if product.material %}

<span class="pill">
{{ product.material }}
</span>

{% endif %}

{% if product.color %}

<span class="pill">
{{ product.color }}
</span>

{% endif %}

</div>

</article>

{% endfor %}

</div>

</div>

</section>


<!-- MISSION -->

<section
    class="section mission reveal"
    id="mission"
>

<div class="section-inner">

<div class="section-tag">
OUR PURPOSE
</div>

<h2
    class="section-title"
    data-en="Our Mission"
    data-fil="Aming Misyon"
>
Our Mission
</h2>

<p class="section-subtitle">

To empower Filipino artisans, including shoemakers
and women artisans skilled in handpainting,
embroidery and crochet, by creating sustainable,
high-quality footwear that celebrates local heritage
and craftsmanship.

<br><br>

We strive to foster economic growth in Liliw and
preserve our family's footwear-making legacy
established in <strong>1963</strong>.

</p>


<div class="quote">

“Preserving heritage.
Empowering artisans.
Creating the future of Filipino footwear.”

</div>


<br><br>


<div class="section-tag">
OUR VISION
</div>

<h2
    class="section-title"
    data-en="A future made by hand."
    data-fil="Kinabukasang gawa ng kamay."
>
A future made by hand.
</h2>

<p class="section-subtitle">

To be one of the leading pioneers in sustainable,
handcrafted footwear while inspiring a new generation
of artisans and positioning Liliw as a center of
footwear excellence.

</p>

</div>

</section>


<!-- CONTACT -->

<section
    class="contact reveal"
    id="contact"
>

<div class="contact-box">

<div class="section-tag">
VISIT PADRON
</div>

<h2>
PADRON
</h2>

<p class="contact-line">
📍 {{ store_address }}
</p>

<p class="contact-line">
📱 {{ store_phone }}
</p>

<p class="contact-line">
🇵🇭 Liliw, Laguna, Philippines
</p>

<br>

<a
    class="btn primary"
    href="https://www.google.com/maps/search/?api=1&query=268+A.+Mabini+Street,+Liliw,+Laguna"
    target="_blank"
    rel="noopener"
>
📍 Open in Maps
</a>

</div>

</section>


<!-- FOOTER -->

<footer>

<strong>PADRON</strong>

<div class="by">
By JHR
</div>

</footer>


<div id="toast"></div>


<script>

/* =========================================================
   LANGUAGE
========================================================= */

let language =
    localStorage.getItem("padron-language")
    || "en";


function updateLanguage() {

    document
        .querySelectorAll("[data-en]")
        .forEach(element => {

            element.textContent =
                language === "fil"
                ? element.dataset.fil
                : element.dataset.en;

        });


    document.getElementById(
        "languageButton"
    ).textContent =
        language === "fil"
        ? "🇺🇸 English"
        : "🇵🇭 Filipino";


    localStorage.setItem(
        "padron-language",
        language
    );
}


function toggleLanguage() {

    language =
        language === "en"
        ? "fil"
        : "en";

    updateLanguage();

    showToast(
        language === "fil"
        ? "Filipino selected 🇵🇭"
        : "English selected 🇺🇸"
    );
}


/* =========================================================
   DARK MODE
========================================================= */

let dark =
    localStorage.getItem("padron-dark")
    === "true";


function updateTheme() {

    document.body.classList.toggle(
        "dark",
        dark
    );

    document.getElementById(
        "themeButton"
    ).textContent =
        dark
        ? "☀️"
        : "🌙";

    localStorage.setItem(
        "padron-dark",
        dark
    );
}


function toggleDark() {

    dark = !dark;

    updateTheme();

    showToast(
        dark
        ? "Dark mode enabled"
        : "Light mode enabled"
    );
}


/* =========================================================
   PRODUCT FILTER
========================================================= */

let currentFilter = "all";


function setFilter(
    filter,
    button
) {

    currentFilter = filter;

    document
        .querySelectorAll(".filter")
        .forEach(
            item =>
                item.classList.remove("active")
        );

    button.classList.add("active");

    filterProducts();
}


function filterProducts() {

    const search =
        document
            .getElementById("search")
            .value
            .toLowerCase()
            .trim();


    document
        .querySelectorAll(".product")
        .forEach(product => {

            const category =
                product.dataset.category;

            const name =
                product.dataset.name;


            const categoryMatch =
                currentFilter === "all"
                ||
                category === currentFilter;


            const searchMatch =
                !search
                ||
                name.includes(search)
                ||
                category.toLowerCase()
                    .includes(search);


            if (
                categoryMatch
                &&
                searchMatch
            ) {

                product.style.display = "";

                setTimeout(() => {
                    product.style.opacity = "1";
                }, 10);

            } else {

                product.style.opacity = "0";

                setTimeout(() => {
                    product.style.display = "none";
                }, 180);

            }

        });
}


/* =========================================================
   TOAST
========================================================= */

function showToast(message) {

    const toast =
        document.getElementById("toast");

    toast.textContent = message;

    toast.classList.add("show");

    setTimeout(
        () => toast.classList.remove("show"),
        2200
    );
}


/* =========================================================
   SCROLL ANIMATIONS
========================================================= */

const observer =
    new IntersectionObserver(
        entries => {

            entries.forEach(entry => {

                if (
                    entry.isIntersecting
                ) {

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
    .forEach(
        element =>
            observer.observe(element)
    );


/* =========================================================
   INITIALIZATION
========================================================= */

updateTheme();

updateLanguage();

</script>

</body>

</html>
"""


# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN_PAGE = r"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>PADRON Staff</title>

<style>

@import url(
    'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap'
);

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    min-height: 100vh;

    display: grid;

    place-items: center;

    padding: 20px;

    font-family: "DM Sans", sans-serif;

    color: #2e1c14;

    background:
        radial-gradient(
            circle at 15% 15%,
            #e6c5a3,
            transparent 30%
        ),
        radial-gradient(
            circle at 85% 85%,
            #c9966e,
            transparent 30%
        ),
        #f5ede3;
}

.login {

    width: min(430px, 100%);

    padding: 45px;

    text-align: center;

    background: #fffaf4;

    border:
        1px solid
        rgba(80,50,30,.12);

    border-radius: 35px;

    box-shadow:
        0 30px 90px
        rgba(70,40,20,.2);
}

.logo {

    width: 100px;
    height: 100px;

    object-fit: contain;

    border-radius: 20px;
}

h1 {

    font-family:
        "Playfair Display",
        serif;

    font-size: 48px;

    margin:
        15px 0 5px;
}

p {

    color: #806b5b;
}

input {

    width: 100%;

    padding: 15px;

    margin: 7px 0;

    border:
        1px solid
        #dfc9b5;

    border-radius: 15px;

    outline: none;

    background: white;
}

button {

    width: 100%;

    padding: 15px;

    margin-top: 12px;

    border: 0;

    border-radius: 999px;

    color: white;

    background:
        linear-gradient(
            135deg,
            #75452d,
            #a86d49
        );

    font-weight: 800;

    cursor: pointer;
}

.error {

    margin-bottom: 15px;

    padding: 11px;

    color: #8e3328;

    background: #f5d5ce;

    border-radius: 13px;
}

.back {

    display: block;

    margin-top: 22px;

    color: #75452d;

    text-decoration: none;

    font-weight: 700;
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

<div class="error">
{{ error }}
</div>

{% endif %}

<form method="POST">

<input
    name="username"
    type="text"
    placeholder="Username"
    autocomplete="username"
    required
>

<input
    name="password"
    type="password"
    placeholder="Password"
    autocomplete="current-password"
    required
>

<button>
Enter Staff Portal
</button>

</form>

<a
    class="back"
    href="/"
>
← Return to PADRON
</a>

</div>

</body>

</html>
"""


# ============================================================
# STAFF PAGE
# ============================================================

STAFF_PAGE = r"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>PADRON Staff Dashboard</title>

<style>

@import url(
    'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap'
);

:root {

    --bg:#f5ede3;
    --card:#fffaf4;
    --card2:#ead9c7;
    --text:#2e1c14;
    --muted:#806b5b;
    --brown:#75452d;
    --brown2:#a86d49;
    --red:#a33d32;
    --green:#477651;
    --border:rgba(70,40,20,.12);
}

* {
    box-sizing:border-box;
}

body {

    margin:0;

    color:var(--text);

    background:
        radial-gradient(
            circle at 5% 5%,
            #e7c8a8,
            transparent 25%
        ),
        var(--bg);

    font-family:"DM Sans",sans-serif;
}

header {

    position:sticky;

    top:0;

    z-index:10;

    background:
        rgba(255,250,244,.9);

    backdrop-filter:blur(18px);

    border-bottom:
        1px solid var(--border);
}

.header {

    max-width:1250px;

    margin:auto;

    padding:16px 20px;

    display:flex;

    justify-content:space-between;

    align-items:center;

    gap:15px;
}

.logo {

    font-weight:900;

    letter-spacing:4px;
}

.actions {

    display:flex;

    gap:8px;

    flex-wrap:wrap;
}

.btn {

    border:0;

    padding:11px 17px;

    border-radius:999px;

    background:var(--card2);

    color:var(--text);

    text-decoration:none;

    font-weight:700;

    cursor:pointer;
}

.primary {

    color:white;

    background:
        linear-gradient(
            135deg,
            var(--brown),
            var(--brown2)
        );
}

.danger {

    color:white;

    background:var(--red);
}

.container {

    max-width:1250px;

    margin:auto;

    padding:45px 20px 90px;
}

h1 {

    font-family:
        "Playfair Display",
        serif;

    font-size:55px;

    margin:
        0 0 5px;
}

.subtitle {

    color:var(--muted);
}

.stats {

    display:grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(200px,1fr)
        );

    gap:16px;

    margin:35px 0;
}

.stat {

    background:var(--card);

    border:
        1px solid var(--border);

    border-radius:25px;

    padding:25px;

    box-shadow:
        0 15px 40px
        rgba(80,50,30,.07);
}

.stat-number {

    margin-top:8px;

    font-size:42px;

    font-weight:900;

    color:var(--brown);
}

.card {

    margin-top:25px;

    padding:25px;

    background:var(--card);

    border:
        1px solid var(--border);

    border-radius:28px;

    overflow:hidden;
}

.card h2 {

    font-family:
        "Playfair Display",
        serif;

    font-size:30px;

    margin-top:0;
}

.table-wrap {

    overflow:auto;

    margin-top:20px;
}

table {

    width:100%;

    min-width:950px;

    border-collapse:collapse;
}

th,
td {

    padding:13px 10px;

    border-bottom:
        1px solid var(--border);

    text-align:left;
}

th {

    color:var(--brown);

    font-size:13px;
}

input,
select,
textarea {

    width:100%;

    padding:10px;

    border:
        1px solid var(--border);

    border-radius:10px;

    background:white;

    color:#2e1c14;

    outline:none;
}

textarea {

    min-height:75px;

    resize:vertical;
}

.add-form {

    display:none;

    margin-top:25px;

    padding:20px;

    border-radius:20px;

    background:var(--card2);
}

.add-form.open {

    display:block;
}

.form-grid {

    display:grid;

    grid-template-columns:
        repeat(2,1fr);

    gap:15px;
}

.full {

    grid-column:1/-1;
}

.label {

    display:block;

    margin-bottom:5px;

    font-size:13px;

    font-weight:700;
}

.visitors {

    max-height:500px;

    overflow:auto;
}

.small {

    color:var(--muted);

    font-size:12px;
}

@media(max-width:700px) {

    .header {

        flex-direction:column;
    }

    h1 {

        font-size:42px;
    }

    .form-grid {

        grid-template-columns:1fr;
    }

    .full {

        grid-column:auto;
    }

}

</style>

</head>

<body>

<header>

<div class="header">

<div class="logo">
PADRON · STAFF
</div>

<div class="actions">

<a
    class="btn"
    href="/"
>
View Store
</a>

<a
    class="btn danger"
    href="/staff/logout"
>
Logout
</a>

</div>

</div>

</header>


<main class="container">

<h1>Dashboard</h1>

<p class="subtitle">
Welcome back. Manage the PADRON collection from here.
</p>


<div class="stats">

<div class="stat">

<div class="small">
VISITOR RECORDS
</div>

<div class="stat-number">
{{ total_visitors }}
</div>

</div>


<div class="stat">

<div class="small">
TOTAL STOCK
</div>

<div class="stat-number">
{{ total_stock }}
</div>

</div>


<div class="stat">

<div class="small">
PRODUCTS
</div>

<div class="stat-number">
{{ products|length }}
</div>

</div>


<div class="stat">

<div class="small">
LOW STOCK
</div>

<div class="stat-number">
{{ low_stock }}
</div>

</div>

</div>


<!-- PRODUCTS -->

<section class="card">

<h2>Product Collection</h2>

<button
    class="btn primary"
    onclick="toggleAdd()"
>
＋ Add New Product
</button>


<div
    id="addForm"
    class="add-form"
>

<div class="form-grid">

<div>

<label class="label">
Product Name
</label>

<input id="new-name">

</div>


<div>

<label class="label">
Category
</label>

<input
    id="new-category"
    value="Footwear"
>

</div>


<div>

<label class="label">
Price
</label>

<input
    id="new-price"
    type="number"
    step="0.01"
    value="0"
>

</div>


<div>

<label class="label">
Stock
</label>

<input
    id="new-stock"
    type="number"
    value="0"
>

</div>


<div>

<label class="label">
Sizes
</label>

<input
    id="new-sizes"
    placeholder="35,36,37,38,39,40"
>

</div>


<div>

<label class="label">
Material
</label>

<input
    id="new-material"
    placeholder="Abaca"
>

</div>


<div>

<label class="label">
Color
</label>

<input id="new-color">

</div>


<div>

<label class="label">
Featured
</label>

<select id="new-featured">

<option value="0">
No
</option>

<option value="1">
Yes
</option>

</select>

</div>


<div class="full">

<label class="label">
Description
</label>

<textarea
    id="new-description"
></textarea>

</div>

</div>


<br>

<button
    class="btn primary"
    onclick="addProduct()"
>
Save Product
</button>

</div>


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
Sizes
</th>

<th>
Material
</th>

<th>
Featured
</th>

<th>
Actions
</th>

</tr>

</thead>


<tbody>

{% for p in products %}

<tr data-id="{{ p.id }}">

<td>

<input
    class="name"
    value="{{ p.name }}"
>

</td>


<td>

<input
    class="category"
    value="{{ p.category }}"
>

</td>


<td>

<input
    class="price"
    type="number"
    step="0.01"
    value="{{ p.price }}"
>

</td>


<td>

<input
    class="stock"
    type="number"
    value="{{ p.stock }}"
>

</td>


<td>

<input
    class="sizes"
    value="{{ p.sizes }}"
>

</td>


<td>

<input
    class="material"
    value="{{ p.material }}"
>

</td>


<td>

<select class="featured">

<option
    value="0"
    {% if not p.featured %}
    selected
    {% endif %}
>
No
</option>

<option
    value="1"
    {% if p.featured %}
    selected
    {% endif %}
>
Yes
</option>

</select>

</td>


<td>

<button
    class="btn primary"
    onclick="saveProduct({{ p.id }})"
>
Save
</button>

<button
    class="btn danger"
    onclick="deleteProduct({{ p.id }})"
>
Delete
</button>

</td>

</tr>

{% endfor %}

</tbody>

</table>

</div>

</section>


<!-- VISITORS -->

<section class="card">

<h2>
Visitor Activity
</h2>

<p class="small">

This dashboard stores basic server-side traffic information
for operational analytics. Avoid using it to identify individual
visitors without an appropriate legal basis or notice.

</p>

<button
    class="btn danger"
    onclick="clearVisitors()"
>
Clear Visitor Records
</button>


<div class="visitors">

<table>

<thead>

<tr>

<th>
Time
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

</tr>

</thead>


<tbody>

{% for visitor in visitors %}

<tr>

<td>
{{ visitor.created_at }}
</td>

<td>
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

function toggleAdd() {

    document
        .getElementById("addForm")
        .classList.toggle("open");

}


async function addProduct() {

    const data = {

        name:
            document.getElementById(
                "new-name"
            ).value,

        category:
            document.getElementById(
                "new-category"
            ).value,

        price:
            document.getElementById(
                "new-price"
            ).value,

        stock:
            document.getElementById(
                "new-stock"
            ).value,

        sizes:
            document.getElementById(
                "new-sizes"
            ).value,

        material:
            document.getElementById(
                "new-material"
            ).value,

        color:
            document.getElementById(
                "new-color"
            ).value,

        featured:
            document.getElementById(
                "new-featured"
            ).value === "1",

        description:
            document.getElementById(
                "new-description"
            ).value

    };


    const response =
        await fetch(
            "/api/products",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body:
                    JSON.stringify(data)
            }
        );


    const result =
        await response.json();


    if (result.success) {

        location.reload();

    } else {

        alert(
            result.message
            || "Unable to add product."
        );

    }

}


async function saveProduct(id) {

    const row =
        document.querySelector(
            'tr[data-id="' + id + '"]'
        );


    const data = {

        name:
            row.querySelector(
                ".name"
            ).value,

        category:
            row.querySelector(
                ".category"
            ).value,

        price:
            row.querySelector(
                ".price"
            ).value,

        stock:
            row.querySelector(
                ".stock"
            ).value,

        sizes:
            row.querySelector(
                ".sizes"
            ).value,

        material:
            row.querySelector(
                ".material"
            ).value,

        featured:
            row.querySelector(
                ".featured"
            ).value === "1"

    };


    const response =
        await fetch(
            "/api/products/" + id,
            {
                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body:
                    JSON.stringify(data)
            }
        );


    const result =
        await response.json();


    if (result.success) {

        alert(
            "Product updated successfully."
        );

    } else {

        alert(
            result.message
            || "Update failed."
        );

    }

}


async function deleteProduct(id) {

    if (
        !confirm(
            "Delete this product permanently?"
        )
    ) {

        return;

    }


    const response =
        await fetch(
            "/api/products/" + id,
            {
                method: "DELETE"
            }
        );


    const result =
        await response.json();


    if (result.success) {

        location.reload();

    } else {

        alert(
            result.message
            || "Delete failed."
        );

    }

}


async function clearVisitors() {

    if (
        !confirm(
            "Clear all visitor records?"
        )
    ) {

        return;

    }


    const response =
        await fetch(
            "/api/visitors/clear",
            {
                method: "POST"
            }
        );


    const result =
        await response.json();


    if (result.success) {

        location.reload();

    }

}

</script>

</body>

</html>
"""


# ============================================================
# ERRORS
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return """
    <div style="
        font-family:Arial;
        text-align:center;
        padding:100px;
    ">
        <h1>404</h1>
        <p>That page doesn't exist.</p>
        <a href="/">Return to PADRON</a>
    </div>
    """, 404


# ============================================================
# LOCAL / RENDER START
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
