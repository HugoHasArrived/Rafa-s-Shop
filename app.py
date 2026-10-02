import os
import sqlite3
from datetime import datetime
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    render_template_string,
    jsonify,
)

app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

# ============================================================
# PADRON - Filipino Footwear
# Self-contained Flask application
# ============================================================

STORE_NAME = "PADRON"
LOGO_FILE = "Image0 (3).jpeg"
DB_FILE = os.path.join(os.path.dirname(__file__), "padron.db")

ADMIN_USER = os.environ.get("PADRON_ADMIN_USER", "staff")
ADMIN_PASSWORD = os.environ.get("PADRON_ADMIN_PASSWORD", "change-me")

ADDRESS = "268 A. Mabini Street, Liliw, Laguna"
PHONE = "0976 1296450"

ABOUT = """
Golden Zapatillas Corporation is a family-owned business established in 2015,
continuing a family tradition of manufacturing high-quality footwear in Liliw, Laguna.

Our main goal is to create pairs of shoes that showcase the creativity and craftsmanship
of our artisans: artist painters, beadworkers, embroiderers, and shoemakers from Laguna.

We use locally sourced materials like abaca and indigenous fabrics such as Ifugao fabric
and Inabel to support our local suppliers and create a Filipino touch in footwear that is
world-class in quality and durability.

Padron is the brand name we're known for. We chose this name, which means "pattern"
in Spanish, because every footwear design starts in creating a padron/pattern.

With our humble beginnings in mind, we strive to create footwear designs that are
world-class in quality.
"""

PRODUCTS_TEXT = """
Padron is committed to quality, heritage, sustainability, and women empowerment,
evident in the design and craftsmanship of every footwear piece we create.

We offer selections of handmade mules, flats, platform, and wedge espadrilles that
showcase the skills of Laguna artisans.

We use materials like abaca, Ifugao fabric and Inabel to support our local suppliers.

We continually innovate designs, and our latest creation is the Estela interchangeable
strap. The Estela interchangeable strap is a product of our continuous innovation through
the assistance of the Department of Trade and Industry - One Town, One Product
(DTI-OTOP) program and is currently undergoing IPOPHIL patent approval.
"""

MISSION = """
To empower Filipino artisans, including shoemakers, women artisans skilled in
handpainting, embroidery, and crochet, by creating sustainable, high-quality footwear
that celebrates local heritage and craftsmanship, fostering economic growth in Liliw
and preserving our family's legacy of footwear making, established in 1963.
"""

VISION = """
To be one of the leading pioneers in sustainable, handcrafted footwear, incorporating
the expertise of shoemakers and women artisans skilled in handpainting, embroidery,
and crochet, inspiring a new generation of artisans, preserving our family's legacy,
and positioning Liliw as a center of footwear excellence.
"""


# ============================================================
# DATABASE
# ============================================================

def get_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    db = get_db()

    db.execute("""
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

    db.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            language TEXT,
            path TEXT,
            created_at TEXT
        )
    """)

    count = db.execute(
        "SELECT COUNT(*) AS total FROM products"
    ).fetchone()["total"]

    if count == 0:
        starter_products = [
            (
                "Handmade Mule",
                "Mules",
                "Handcrafted Filipino footwear made with attention to detail.",
                0,
                0,
                "35,36,37,38,39,40",
                "Natural",
                "Local materials",
            ),
            (
                "Classic Flat",
                "Flats",
                "Simple and elegant handmade flats.",
                0,
                0,
                "35,36,37,38,39,40",
                "Natural",
                "Abaca / Indigenous fabric",
            ),
            (
                "Platform Espadrille",
                "Platform",
                "A handcrafted platform style inspired by Filipino artistry.",
                0,
                0,
                "35,36,37,38,39,40",
                "Various",
                "Indigenous fabric",
            ),
            (
                "Wedge Espadrille",
                "Wedges",
                "Handcrafted wedge espadrilles showcasing Laguna craftsmanship.",
                0,
                0,
                "35,36,37,38,39,40",
                "Various",
                "Abaca / Inabel",
            ),
            (
                "Estela Interchangeable Strap",
                "Innovation",
                "An interchangeable strap design created through continuous innovation.",
                0,
                0,
                "35,36,37,38,39,40",
                "Various",
                "Local materials",
            ),
        ]

        db.executemany("""
            INSERT INTO products
            (name, category, description, price, stock, sizes, color, material)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, starter_products)

    db.commit()
    db.close()


init_db()


# ============================================================
# VISITOR TRACKING
# ============================================================

def record_visitor():
    try:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.remote_addr or "Unknown"

        # Privacy-conscious: only store information necessary for
        # the staff analytics page.
        user_agent = request.headers.get("User-Agent", "Unknown")
        language = request.headers.get("Accept-Language", "Unknown")

        db = get_db()
        db.execute("""
            INSERT INTO visitors
            (ip, user_agent, language, path, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            ip,
            user_agent[:500],
            language[:200],
            request.path[:300],
            datetime.utcnow().isoformat(timespec="seconds"),
        ))
        db.commit()
        db.close()

    except Exception:
        pass


# ============================================================
# LOGIN HELPERS
# ============================================================

def staff_logged_in():
    return session.get("staff_logged_in") is True


# ============================================================
# MAIN HTML
# ============================================================

PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>{{ title }} | PADRON</title>

<style>
:root {
    --brown-950: #24150f;
    --brown-900: #382219;
    --brown-800: #4b2e20;
    --brown-700: #62402d;
    --brown-600: #795239;
    --brown-500: #9b6b47;
    --brown-400: #bd8b62;
    --brown-300: #d7ad86;
    --brown-200: #ead3bd;
    --brown-100: #f5e9dc;
    --cream: #fffaf4;
    --white: #ffffff;
    --gold: #d59a52;
    --shadow: 0 20px 60px rgba(62, 36, 20, .14);
}

* {
    box-sizing: border-box;
    scroll-behavior: smooth;
}

body {
    margin: 0;
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    background:
        radial-gradient(circle at 15% 10%, rgba(213,154,82,.14), transparent 25%),
        radial-gradient(circle at 90% 30%, rgba(155,107,71,.12), transparent 28%),
        var(--cream);
    color: var(--brown-900);
    text-align: center;
    overflow-x: hidden;
}

body.dark {
    --cream: #17100c;
    --white: #251914;
    --brown-100: #33231a;
    --brown-200: #4a3224;
    --brown-300: #694a35;
    --brown-900: #f7eadc;
    --brown-800: #ead6c4;
    --brown-700: #d7bca5;
    --brown-500: #d19a6b;
    --brown-400: #e1b487;
    background:
        radial-gradient(circle at 15% 10%, rgba(213,154,82,.10), transparent 25%),
        #17100c;
    color: #f7eadc;
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

.nav {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    z-index: 1000;
    backdrop-filter: blur(18px);
    background: rgba(255,250,244,.82);
    border-bottom: 1px solid rgba(121,82,57,.12);
}

.dark .nav {
    background: rgba(23,16,12,.84);
}

.nav-inner {
    max-width: 1250px;
    margin: auto;
    padding: 13px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 950;
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
    align-items: center;
    justify-content: center;
    gap: 7px;
    flex-wrap: wrap;
}

.nav-links a,
.nav-button {
    border: 0;
    background: transparent;
    padding: 9px 12px;
    border-radius: 999px;
    color: inherit;
    font-weight: 750;
    transition: .2s;
}

.nav-links a:hover,
.nav-button:hover {
    background: var(--brown-100);
    transform: translateY(-2px);
}

.mode {
    border: 1px solid var(--brown-200);
    background: var(--white);
    color: inherit;
    padding: 9px 13px;
    border-radius: 999px;
    font-weight: 800;
}

.hero {
    min-height: 92vh;
    padding: 150px 20px 80px;
    display: grid;
    place-items: center;
    position: relative;
    isolation: isolate;
}

.hero::before,
.hero::after {
    content: "";
    position: absolute;
    border-radius: 50%;
    filter: blur(5px);
    z-index: -1;
}

.hero::before {
    width: 420px;
    height: 420px;
    background: rgba(213,154,82,.16);
    top: 100px;
    left: -160px;
}

.hero::after {
    width: 500px;
    height: 500px;
    background: rgba(155,107,71,.12);
    right: -220px;
    bottom: -100px;
}

.hero-card {
    max-width: 1000px;
    padding: 45px 25px;
}

.logo {
    width: min(260px, 70vw);
    max-height: 190px;
    object-fit: contain;
    margin-bottom: 25px;
    filter: drop-shadow(0 20px 35px rgba(61,38,23,.18));
    animation: float 5s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-12px); }
}

.kicker {
    display: inline-block;
    padding: 8px 15px;
    border-radius: 999px;
    background: var(--brown-100);
    color: var(--brown-700);
    font-weight: 900;
    letter-spacing: .12em;
    text-transform: uppercase;
    font-size: .75rem;
}

h1 {
    font-size: clamp(3rem, 9vw, 7.2rem);
    line-height: .92;
    margin: 22px 0;
    letter-spacing: -.07em;
    color: var(--brown-900);
}

.hero p {
    max-width: 720px;
    margin: 0 auto 28px;
    font-size: clamp(1rem, 2vw, 1.25rem);
    line-height: 1.8;
    color: var(--brown-700);
}

.actions {
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
}

.btn {
    border: 0;
    border-radius: 999px;
    padding: 14px 23px;
    font-weight: 900;
    transition: .25s;
}

.btn-primary {
    color: white;
    background: linear-gradient(135deg, var(--brown-800), var(--brown-500));
    box-shadow: 0 14px 30px rgba(75,46,32,.25);
}

.btn-secondary {
    color: var(--brown-800);
    background: var(--brown-100);
}

.btn:hover {
    transform: translateY(-4px) scale(1.02);
}

.section {
    max-width: 1180px;
    margin: auto;
    padding: 95px 20px;
}

.section-title {
    font-size: clamp(2rem, 5vw, 4rem);
    letter-spacing: -.045em;
    margin: 0 0 14px;
}

.section-subtitle {
    max-width: 720px;
    margin: 0 auto 45px;
    color: var(--brown-700);
    line-height: 1.8;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 20px;
}

.card {
    background: rgba(255,255,255,.72);
    border: 1px solid rgba(121,82,57,.12);
    border-radius: 28px;
    padding: 30px;
    box-shadow: var(--shadow);
    transition: .3s;
}

.dark .card {
    background: rgba(37,25,20,.85);
}

.card:hover {
    transform: translateY(-9px);
    box-shadow: 0 28px 70px rgba(62,36,20,.20);
}

.icon {
    width: 65px;
    height: 65px;
    display: grid;
    place-items: center;
    margin: 0 auto 18px;
    border-radius: 20px;
    background: var(--brown-100);
    font-size: 1.7rem;
}

.card h3 {
    margin: 8px 0;
    font-size: 1.25rem;
}

.card p {
    color: var(--brown-700);
    line-height: 1.7;
}

.product {
    position: relative;
    overflow: hidden;
}

.product::before {
    content: "";
    position: absolute;
    width: 180px;
    height: 180px;
    background: rgba(213,154,82,.11);
    border-radius: 50%;
    top: -90px;
    right: -90px;
}

.product-tag {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: var(--brown-100);
    font-size: .72rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .08em;
}

.price {
    color: var(--brown-600);
    font-weight: 950;
    font-size: 1.3rem;
    margin-top: 18px;
}

.stock {
    margin-top: 8px;
    color: var(--brown-700);
    font-weight: 700;
}

.about-box {
    max-width: 900px;
    margin: auto;
    padding: 45px;
    border-radius: 35px;
    background:
        linear-gradient(135deg, rgba(155,107,71,.13), rgba(213,154,82,.08));
    border: 1px solid var(--brown-200);
}

.about-box p {
    line-height: 1.9;
    color: var(--brown-700);
}

.quote {
    font-size: clamp(1.4rem, 3vw, 2.5rem);
    line-height: 1.35;
    font-weight: 900;
    max-width: 900px;
    margin: auto;
}

.contact {
    background: var(--brown-900);
    color: var(--cream);
    max-width: none;
    padding: 80px 20px 25px;
}

.contact p {
    color: var(--brown-300);
    line-height: 1.8;
}

.contact-inner {
    max-width: 900px;
    margin: auto;
}

.footer {
    margin-top: 70px;
    padding-top: 20px;
    border-top: 1px solid rgba(255,255,255,.12);
    color: var(--brown-300);
    font-size: .9rem;
}

.reveal {
    opacity: 0;
    transform: translateY(25px);
    transition: opacity .7s ease, transform .7s ease;
}

.reveal.visible {
    opacity: 1;
    transform: translateY(0);
}

.staff-panel {
    max-width: 1150px;
    margin: 130px auto 80px;
    padding: 20px;
}

.staff-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
    margin-bottom: 25px;
}

.table-wrap {
    overflow-x: auto;
    border-radius: 22px;
    border: 1px solid var(--brown-200);
}

table {
    width: 100%;
    border-collapse: collapse;
    background: var(--white);
}

th,
td {
    padding: 14px;
    border-bottom: 1px solid var(--brown-200);
    text-align: center;
}

th {
    background: var(--brown-100);
    font-weight: 900;
}

input,
textarea,
select {
    width: 100%;
    border: 1px solid var(--brown-200);
    border-radius: 12px;
    padding: 11px;
    background: var(--white);
    color: inherit;
    outline: none;
}

textarea {
    min-height: 100px;
    resize: vertical;
}

.form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 15px;
}

.form-group {
    text-align: center;
}

.form-group label {
    display: block;
    font-weight: 850;
    margin-bottom: 7px;
}

.login {
    max-width: 500px;
    margin: 160px auto 100px;
    padding: 25px;
}

.alert {
    padding: 12px;
    margin: 15px 0;
    border-radius: 12px;
    background: #f7d5d1;
    color: #7b1e18;
    font-weight: 750;
}

.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
}

.stat {
    padding: 25px;
    border-radius: 22px;
    background: var(--brown-100);
}

.stat-number {
    font-size: 2.3rem;
    font-weight: 950;
}

.lang {
    display: flex;
    justify-content: center;
    gap: 7px;
    margin: 20px 0;
    flex-wrap: wrap;
}

.lang button {
    border: 1px solid var(--brown-200);
    border-radius: 999px;
    background: var(--white);
    color: inherit;
    padding: 7px 12px;
    font-weight: 800;
}

.hidden {
    display: none !important;
}

@media (max-width: 750px) {
    .nav-inner {
        flex-direction: column;
    }

    .nav {
        position: relative;
    }

    .hero {
        padding-top: 70px;
    }

    .staff-panel {
        margin-top: 40px;
    }

    .about-box {
        padding: 28px 20px;
    }
}
</style>
</head>

<body>

<nav class="nav">
    <div class="nav-inner">

        <a href="{{ url_for('index') }}" class="brand">
            <img src="{{ url_for('static', filename=logo_file) }}"
                 alt="PADRON logo"
                 onerror="this.style.display='none'">
            <span>PADRON</span>
        </a>

        <div class="nav-links">
            <a href="{{ url_for('index') }}#about">About</a>
            <a href="{{ url_for('index') }}#products">Products</a>
            <a href="{{ url_for('index') }}#mission">Mission</a>
            <a href="{{ url_for('index') }}#vision">Vision</a>
            <a href="{{ url_for('index') }}#contact">Contact</a>

            {% if logged_in %}
                <a href="{{ url_for('staff') }}">Staff</a>
            {% endif %}
        </div>

        <button class="mode" onclick="toggleMode()" id="modeButton">
            🌙 Dark
        </button>
    </div>
</nav>


{% block_content %}{% endblock %}

<script>
function toggleMode() {
    document.body.classList.toggle("dark");

    const dark = document.body.classList.contains("dark");
    localStorage.setItem("padron-mode", dark ? "dark" : "light");

    document.getElementById("modeButton").innerText =
        dark ? "☀️ Bright" : "🌙 Dark";
}

(function () {
    const mode = localStorage.getItem("padron-mode");

    if (mode === "dark") {
        document.body.classList.add("dark");

        const button = document.getElementById("modeButton");
        if (button) button.innerText = "☀️ Bright";
    }
})();

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add("visible");
        }
    });
}, {
    threshold: .12
});

document.querySelectorAll(".reveal").forEach(el => observer.observe(el));

function setLanguage(language) {
    document.querySelectorAll("[data-en]").forEach(el => {
        const value = el.dataset[language];

        if (value) {
            el.innerHTML = value;
        }
    });

    localStorage.setItem("padron-language", language);
}

(function () {
    const language = localStorage.getItem("padron-language") || "en";
    setLanguage(language);
})();
</script>

</body>
</html>
"""


# ============================================================
# HOME PAGE
# ============================================================

HOME_CONTENT = r"""
<section class="hero">
    <div class="hero-card">

        <img
            class="logo"
            src="{{ url_for('static', filename=logo_file) }}"
            alt="PADRON logo"
            onerror="this.style.display='none'"
        >

        <div class="kicker">Liliw, Laguna • Since 2015</div>

        <h1>PADRON</h1>

        <p
            data-en="Handcrafted Filipino footwear shaped by heritage, creativity, and the hands of local artisans."
            data-fil="Sapatos na gawa ng mga Pilipinong artisan, hinubog ng tradisyon, pagkamalikhain, at husay."
        >
            Handcrafted Filipino footwear shaped by heritage, creativity,
            and the hands of local artisans.
        </p>

        <div class="actions">
            <a href="#products" class="btn btn-primary">Explore Products ↓</a>
            <a href="#about" class="btn btn-secondary">Our Story</a>
        </div>

        <div class="lang">
            <button onclick="setLanguage('en')">English</button>
            <button onclick="setLanguage('fil')">Filipino</button>
        </div>

    </div>
</section>


<section class="section reveal" id="about">
    <div class="about-box">

        <div class="kicker">About Us</div>

        <h2 class="section-title">A Filipino Story in Every Pair</h2>

        <p>
            Golden Zapatillas Corporation is a family-owned business established in
            <strong>2015</strong>, continuing a family tradition of manufacturing
            high-quality footwear in Liliw, Laguna.
        </p>

        <p>
            Our goal is to create footwear that showcases the creativity and
            craftsmanship of our artisans: artist painters, beadworkers,
            embroiderers, and shoemakers from Laguna.
        </p>

        <p>
            We use locally sourced materials like abaca and indigenous fabrics
            such as Ifugao fabric and Inabel, supporting local suppliers while
            creating footwear with a Filipino touch and world-class quality.
        </p>

        <p>
            The name <strong>Padron</strong> means "pattern" in Spanish.
            Every footwear design begins with a padron or pattern, and the
            finished product reveals the beauty that grows from that beginning.
        </p>

    </div>
</section>


<section class="section reveal" id="products">

    <div class="kicker">Our Products</div>

    <h2 class="section-title">Made by Hand. Made with Purpose.</h2>

    <p class="section-subtitle">
        Handmade footwear celebrating Filipino craftsmanship,
        sustainability, heritage, and women empowerment.
    </p>

    <div class="grid">

        {% for product in products %}

        <article class="card product">

            <div class="icon">
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

            <span class="product-tag">
                {{ product["category"] or "Footwear" }}
            </span>

            <h3>{{ product["name"] }}</h3>

            <p>{{ product["description"] }}</p>

            {% if product["price"] > 0 %}
                <div class="price">
                    ₱{{ "%.2f"|format(product["price"]) }}
                </div>
            {% else %}
                <div class="price">Price available in store</div>
            {% endif %}

            {% if product["sizes"] %}
                <p><strong>Sizes:</strong> {{ product["sizes"] }}</p>
            {% endif %}

            {% if product["material"] %}
                <p><strong>Material:</strong> {{ product["material"] }}</p>
            {% endif %}

        </article>

        {% endfor %}

    </div>
</section>


<section class="section reveal" id="mission">

    <div class="kicker">Mission</div>

    <h2 class="section-title">Empowering Filipino Artisans</h2>

    <div class="about-box">
        <p>{{ mission }}</p>
    </div>

</section>


<section class="section reveal" id="vision">

    <div class="kicker">Vision</div>

    <h2 class="section-title">A Future Built on Craftsmanship</h2>

    <div class="about-box">
        <p>{{ vision }}</p>
    </div>

</section>


<section class="section reveal">

    <div class="quote">
        “Every design begins with a pattern.
        Every pair carries a story.”
    </div>

</section>


<section class="contact" id="contact">

    <div class="contact-inner">

        <div class="kicker">Visit / Contact</div>

        <h2 class="section-title">PADRON</h2>

        <p>
            {{ address }}
        </p>

        <p>
            📱 {{ phone }}
        </p>

        <p>
            📍 Liliw, Laguna, Philippines
        </p>

        <div class="footer">
            PADRON • Filipino handcrafted footwear
            <br>
            By JHR
        </div>

    </div>

</section>
"""


@app.route("/")
def index():
    record_visitor()

    db = get_db()
    products = db.execute("""
        SELECT *
        FROM products
        WHERE active = 1
        ORDER BY id ASC
    """).fetchall()
    db.close()

    content = HOME_CONTENT

    html = PAGE.replace(
        "{% block_content %}",
        content
    )

    return render_template_string(
        html,
        title="Handcrafted Filipino Footwear",
        logo_file=LOGO_FILE,
        products=products,
        mission=MISSION,
        vision=VISION,
        address=ADDRESS,
        phone=PHONE,
        logged_in=staff_logged_in(),
    )


# ============================================================
# STAFF LOGIN
# ============================================================

LOGIN_PAGE = r"""
<div class="login">

    <div class="card">

        <img
            src="{{ url_for('static', filename=logo_file) }}"
            alt="PADRON"
            style="width:130px;height:100px;object-fit:contain;"
            onerror="this.style.display='none'"
        >

        <div class="kicker">Private Staff Area</div>

        <h1 style="font-size:3rem;">Staff Login</h1>

        {% if error %}
            <div class="alert">{{ error }}</div>
        {% endif %}

        <form method="POST">

            <div class="form-group">
                <label>Username</label>
                <input
                    name="username"
                    autocomplete="username"
                    required
                >
            </div>

            <br>

            <div class="form-group">
                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    autocomplete="current-password"
                    required
                >
            </div>

            <br>

            <button class="btn btn-primary" type="submit">
                Enter Staff Dashboard
            </button>

        </form>

        <br>

        <a href="{{ url_for('index') }}" class="btn btn-secondary">
            ← Back to PADRON
        </a>

    </div>

</div>
"""


@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    if staff_logged_in():
        return redirect(url_for("staff"))

    error = None

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            session["staff_logged_in"] = True
            return redirect(url_for("staff"))

        error = "Incorrect staff username or password."

    html = PAGE.replace(
        "{% block_content %}",
        LOGIN_PAGE
    )

    return render_template_string(
        html,
        title="Staff Login",
        logo_file=LOGO_FILE,
        logged_in=False,
        error=error,
    )


@app.route("/staff/logout")
def staff_logout():
    session.clear()
    return redirect(url_for("index"))


# ============================================================
# STAFF DASHBOARD
# ============================================================

STAFF_PAGE = r"""
<div class="staff-panel">

    <div class="staff-head">

        <div>
            <div class="kicker">PADRON Management</div>
            <h1 style="font-size:clamp(2.5rem,6vw,5rem);">
                Staff Dashboard
            </h1>
            <p style="color:var(--brown-700);">
                Update footwear information and monitor website activity.
            </p>
        </div>

        <div>
            <a href="{{ url_for('index') }}"
               class="btn btn-secondary">
                View Store
            </a>

            <a href="{{ url_for('staff_logout') }}"
               class="btn btn-primary">
                Logout
            </a>
        </div>

    </div>


    <div class="stat-grid">

        <div class="stat">
            <div class="stat-number">{{ total_visitors }}</div>
            <div>Total Views</div>
        </div>

        <div class="stat">
            <div class="stat-number">{{ unique_ips }}</div>
            <div>Unique IPs</div>
        </div>

        <div class="stat">
            <div class="stat-number">{{ total_products }}</div>
            <div>Products</div>
        </div>

        <div class="stat">
            <div class="stat-number">{{ total_stock }}</div>
            <div>Total Stock</div>
        </div>

    </div>


    <div class="card">

        <h2>➕ Add Product</h2>

        <form method="POST"
              action="{{ url_for('add_product') }}">

            <div class="form-grid">

                <div class="form-group">
                    <label>Name</label>
                    <input name="name" required>
                </div>

                <div class="form-group">
                    <label>Category</label>
                    <input name="category">
                </div>

                <div class="form-group">
                    <label>Price</label>
                    <input
                        type="number"
                        step="0.01"
                        min="0"
                        name="price"
                        value="0"
                    >
                </div>

                <div class="form-group">
                    <label>Stock</label>
                    <input
                        type="number"
                        min="0"
                        name="stock"
                        value="0"
                    >
                </div>

                <div class="form-group">
                    <label>Sizes</label>
                    <input name="sizes">
                </div>

                <div class="form-group">
                    <label>Color</label>
                    <input name="color">
                </div>

                <div class="form-group">
                    <label>Material</label>
                    <input name="material">
                </div>

            </div>

            <br>

            <div class="form-group">
                <label>Description</label>
                <textarea name="description"></textarea>
            </div>

            <br>

            <button class="btn btn-primary">
                Add Product
            </button>

        </form>

    </div>


    <br>


    <div class="card">

        <h2>📦 Product Inventory</h2>

        <div class="table-wrap">

            <table>

                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Category</th>
                        <th>Price</th>
                        <th>Stock</th>
                        <th>Sizes</th>
                        <th>Color</th>
                        <th>Material</th>
                        <th>Action</th>
                    </tr>
                </thead>

                <tbody>

                {% for product in products %}

                <tr>

                    <form method="POST"
                          action="{{ url_for('update_product', product_id=product['id']) }}">

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
                                step="0.01"
                                min="0"
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
                            <button class="btn btn-primary"
                                    type="submit">
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

        <h2>👁 Visitor Activity</h2>

        <p style="color:var(--brown-700);">
            Staff-only website activity information.
        </p>

        <div class="table-wrap">

            <table>

                <thead>
                    <tr>
                        <th>IP</th>
                        <th>Device / Browser</th>
                        <th>Language</th>
                        <th>Page</th>
                        <th>Time</th>
                    </tr>
                </thead>

                <tbody>

                {% for visitor in visitors %}

                    <tr>

                        <td>{{ visitor["ip"] }}</td>

                        <td style="max-width:300px;">
                            {{ visitor["user_agent"] }}
                        </td>

                        <td>{{ visitor["language"] }}</td>

                        <td>{{ visitor["path"] }}</td>

                        <td>{{ visitor["created_at"] }}</td>

                    </tr>

                {% endfor %}

                </tbody>

            </table>

        </div>

    </div>

</div>
"""


@app.route("/staff")
def staff():

    if not staff_logged_in():
        return redirect(url_for("staff_login"))

    db = get_db()

    products = db.execute("""
        SELECT *
        FROM products
        ORDER BY id ASC
    """).fetchall()

    visitors = db.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
        LIMIT 200
    """).fetchall()

    total_visitors = db.execute(
        "SELECT COUNT(*) AS total FROM visitors"
    ).fetchone()["total"]

    unique_ips = db.execute(
        "SELECT COUNT(DISTINCT ip) AS total FROM visitors"
    ).fetchone()["total"]

    total_products = db.execute(
        "SELECT COUNT(*) AS total FROM products"
    ).fetchone()["total"]

    total_stock = db.execute(
        "SELECT COALESCE(SUM(stock), 0) AS total FROM products"
    ).fetchone()["total"]

    db.close()

    html = PAGE.replace(
        "{% block_content %}",
        STAFF_PAGE
    )

    return render_template_string(
        html,
        title="Staff Dashboard",
        logo_file=LOGO_FILE,
        logged_in=True,
        products=products,
        visitors=visitors,
        total_visitors=total_visitors,
        unique_ips=unique_ips,
        total_products=total_products,
        total_stock=total_stock,
    )


# ============================================================
# PRODUCT MANAGEMENT
# ============================================================

@app.route("/staff/product/add", methods=["POST"])
def add_product():

    if not staff_logged_in():
        return redirect(url_for("staff_login"))

    name = request.form.get("name", "").strip()

    if not name:
        return redirect(url_for("staff"))

    try:
        price = float(request.form.get("price", 0) or 0)
    except ValueError:
        price = 0

    try:
        stock = max(0, int(request.form.get("stock", 0) or 0))
    except ValueError:
        stock = 0

    db = get_db()

    db.execute("""
        INSERT INTO products
        (name, category, description, price, stock, sizes, color, material)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        request.form.get("category", "").strip(),
        request.form.get("description", "").strip(),
        max(0, price),
        stock,
        request.form.get("sizes", "").strip(),
        request.form.get("color", "").strip(),
        request.form.get("material", "").strip(),
    ))

    db.commit()
    db.close()

    return redirect(url_for("staff"))


@app.route("/staff/product/<int:product_id>/update", methods=["POST"])
def update_product(product_id):

    if not staff_logged_in():
        return redirect(url_for("staff_login"))

    try:
        price = max(
            0,
            float(request.form.get("price", 0) or 0)
        )
    except ValueError:
        price = 0

    try:
        stock = max(
            0,
            int(request.form.get("stock", 0) or 0)
        )
    except ValueError:
        stock = 0

    db = get_db()

    db.execute("""
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
        request.form.get("name", "").strip(),
        request.form.get("category", "").strip(),
        price,
        stock,
        request.form.get("sizes", "").strip(),
        request.form.get("color", "").strip(),
        request.form.get("material", "").strip(),
        product_id,
    ))

    db.commit()
    db.close()

    return redirect(url_for("staff"))


# ============================================================
# SIMPLE HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "store": STORE_NAME,
        "year": 2015,
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return redirect(url_for("index"))


@app.errorhandler(500)
def server_error(error):
    return """
    <div style="
        min-height:100vh;
        display:grid;
        place-items:center;
        font-family:system-ui;
        text-align:center;
        background:#fffaf4;
        color:#382219;
        padding:30px;
    ">
        <div>
            <h1>PADRON</h1>
            <h2>Something went wrong.</h2>
            <p>Please try again.</p>
            <a href="/" style="
                display:inline-block;
                padding:12px 20px;
                background:#4b2e20;
                color:white;
                border-radius:999px;
                text-decoration:none;
            ">Return Home</a>
        </div>
    </div>
    """, 500


# ============================================================
# LOCAL DEVELOPMENT
# Render uses Gunicorn and does not use this section.
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
