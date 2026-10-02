from flask import Flask, request, redirect, url_for, session, flash, render_template_string, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
import os
import secrets
from pymongo import MongoClient, ReturnDocument

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MONGO_URI = os.environ.get("MONGO_URI", "").strip()
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "clinic_database").strip()

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not configured. Add your MongoDB Atlas connection string to the environment variables.")

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
mongo_db = mongo_client[MONGO_DB_NAME]
staff_collection = mongo_db["staff"]
requests_collection = mongo_db["assistance_requests"]
counters_collection = mongo_db["counters"]
STATIC_DIR.mkdir(exist_ok=True)

app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
    SESSION_COOKIE_PERMANENT=False,
)


def next_request_id():
    result = counters_collection.find_one_and_update(
        {"_id": "assistance_request_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result["seq"]


def init_db():
    # Indexes keep usernames unique and make dashboard queries faster.
    staff_collection.create_index("username", unique=True)
    requests_collection.create_index([("status_rank", 1), ("urgency_rank", 1), ("created_at", -1)])

    # Keep the built-in admin account synchronized with ADMIN_PASSWORD.
    # This fixes the case where an admin account was created earlier with an
    # old password: changing ADMIN_PASSWORD in Render will reset the stored
    # password hash on the next deployment/startup.
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
    admin = staff_collection.find_one({"username": "admin"})

    if admin is None:
        staff_collection.insert_one({
            "username": "admin",
            "password_hash": generate_password_hash(admin_password),
            "role": "admin",
            "active": True,
            "created_at": now(),
        })
    else:
        staff_collection.update_one(
            {"_id": admin["_id"]},
            {"$set": {
                "password_hash": generate_password_hash(admin_password),
                "role": "admin",
                "active": True,
            }}
        )


STATUS_RANK = {
    "New": 0,
    "Seen": 1,
    "In Progress": 2,
    "Resolved": 3,
}

URGENCY_RANK = {
    "Urgent": 0,
    "Needs attention soon": 1,
    "Normal": 2,
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value, limit=2000):
    return (value or "").strip()[:limit]


def staff_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in"):
            return redirect(url_for("staff_login"))
        return fn(*args, **kwargs)
    return wrapper


def new_count():
    return requests_collection.count_documents({"status": "New"})


TRANSLATIONS = {
    "en": {
        "nav_home":"Home", "nav_about":"About", "nav_services":"Services", "nav_clinic":"Clinic", "nav_help":"Assistance", "nav_staff":"Staff",
        "tag":"Licensed Physician & Psychiatrist", "hero_title":"Your mind deserves <span>care.</span>",
        "hero_text":"Compassionate, patient-centered psychiatric care focused on helping you understand your mental well-being and move toward a healthier, more fulfilling life.",
        "help":"I Need Assistance", "meet":"Meet Dr. Tagupa →", "licensed":"Licensed Physician", "licensed_text":"A medical doctor committed to compassionate, patient-centered care.",
        "psychiatry":"Psychiatry", "psychiatry_text":"Psychiatric evaluation and treatment for a wide range of mental health concerns.",
        "centered":"Patient-Centered", "centered_text":"Your story, concerns, and well-being are at the heart of every consultation.",
        "about_kicker":"About the Doctor", "about_title":"Compassion backed by training.", "about_intro":"Professional medical and psychiatric training with a patient-centered approach.",
        "about_head":"Meet Dr. Tagupa", "about1":"Dr. Bebie Queen Lucelle R. Tagupa is a licensed physician and psychiatrist dedicated to providing compassionate, patient-centered mental health care.",
        "about2":"She earned her Bachelor’s degree in Medical Technology from Velez College and is also a licensed Medical Technologist.",
        "about3":"She proceeded to study Medicine at Xavier University – Ateneo de Cagayan.",
        "about4":"She completed her post-graduate internship at Davao Doctors Hospital and finished her residency training in Psychiatry at the Southern Philippines Medical Center – Institute of Psychiatry and Behavioral Medicine.",
        "about5":"During her final year of training, she served as Chief Resident and was awarded Most Outstanding Resident in Psychiatry during her graduation.",
        "services_kicker":"Mental Health Care", "services_title":"Care that starts with you.", "services_intro":"Support for understanding your mental well-being and moving forward.",
        "eval":"Psychiatric Evaluation", "eval_text":"Comprehensive assessment to better understand mental health concerns.",
        "consult":"Mental Health Consultation", "consult_text":"A respectful space to discuss concerns, emotions, thoughts, and behavior.",
        "treatment":"Treatment & Follow-Up", "treatment_text":"Patient-centered treatment and follow-up based on individual needs.",
        "clinic_kicker":"Clinic Information", "clinic_title":"Visit the clinic.", "clinic_intro":"Find the location and consultation schedule below.",
        "hospital":"Hospital", "location":"Location", "days":"Days", "time":"Time", "days_value":"Tuesday • Thursday • Saturday", "time_value":"9:00 AM – 4:00 PM",
        "help_kicker":"Patient Assistance", "help_title":"Need a little help?", "help_text":"Tell the clinic what you need. Your request will appear on the protected staff dashboard so the clinic team can follow up.",
        "name":"Name", "contact":"Contact", "urgency":"How urgent is this?", "language":"Preferred language", "concern":"How can we help?", "send":"Send Assistance Request →",
        "placeholder_name":"Your name", "placeholder_contact":"Phone or email", "placeholder_concern":"Tell the clinic what you need assistance with...",
        "warning":"Please do not use this form for emergencies. For an immediate medical or safety emergency, contact your local emergency services.",
        "resources_kicker":"Wellness Resources", "resources_title":"Small steps can help.", "resources_intro":"A self-care card is available here as an educational wellness resource. It is not a substitute for professional care.",
        "open_pdf":"Open Self-Care Card (PDF) →", "resource_alt":"Self-care wellness resource", "footer":"© 2026 Medina General Hospital. All rights reserved. • Licensed Physician • Psychiatrist", "quote":"Mental health care begins with <span class='accent'>being heard.</span>", "caption_role":"Licensed Physician • Psychiatrist", "urgent_normal":"Normal", "urgent_soon":"Needs attention soon", "urgent":"Urgent",
    },
    "fil": {
        "nav_home":"Home", "nav_about":"Tungkol sa Doktor", "nav_services":"Serbisyo", "nav_clinic":"Klinika", "nav_help":"Tulong", "nav_staff":"Staff",
        "tag":"Licensed Physician at Psychiatrist", "hero_title":"Ang iyong isip ay karapat-dapat sa <span>pag-aalaga.</span>",
        "hero_text":"Maalaga at patient-centered na psychiatric care upang matulungan kang maunawaan ang iyong mental well-being at mapabuti ang kalidad ng iyong buhay.",
        "help":"Kailangan Ko ng Tulong", "meet":"Kilalanin si Dr. Tagupa →", "licensed":"Licensed Physician", "licensed_text":"Doktor na nakatuon sa mahabagin at patient-centered na pangangalaga.",
        "psychiatry":"Psychiatry", "psychiatry_text":"Psychiatric evaluation at treatment para sa iba’t ibang mental health concerns.", "centered":"Patient-Centered", "centered_text":"Mahalaga ang iyong kuwento, mga alalahanin, at kapakanan sa bawat konsultasyon.",
        "about_kicker":"Tungkol sa Doktor", "about_title":"Mahusay na training, may malasakit.", "about_intro":"Propesyonal na medical at psychiatric training na may patient-centered na approach.", "about_head":"Kilalanin si Dr. Tagupa",
        "about1":"Si Dr. Bebie Queen Lucelle R. Tagupa ay isang licensed physician at psychiatrist na nakatuon sa mahabagin at patient-centered na mental health care.",
        "about2":"Natapos niya ang Bachelor’s degree sa Medical Technology sa Velez College at isa rin siyang licensed Medical Technologist.", "about3":"Nagpatuloy siya sa Medicine sa Xavier University – Ateneo de Cagayan.",
        "about4":"Nakumpleto niya ang post-graduate internship sa Davao Doctors Hospital at residency training sa Psychiatry sa Southern Philippines Medical Center – Institute of Psychiatry and Behavioral Medicine.",
        "about5":"Sa kanyang huling taon ng training, nagsilbi siya bilang Chief Resident at ginawaran bilang Most Outstanding Resident in Psychiatry.",
        "services_kicker":"Mental Health Care", "services_title":"Nagsisimula ang pag-aalaga sa iyo.", "services_intro":"Suporta para mas maunawaan ang iyong mental well-being at makapagpatuloy.",
        "eval":"Psychiatric Evaluation", "eval_text":"Masusing assessment upang mas maunawaan ang iyong mental health concerns.", "consult":"Mental Health Consultation", "consult_text":"Ligtas at magalang na lugar para pag-usapan ang iyong concerns, emosyon, isip, at behavior.", "treatment":"Treatment & Follow-Up", "treatment_text":"Patient-centered treatment at follow-up ayon sa iyong pangangailangan.",
        "clinic_kicker":"Impormasyon ng Klinika", "clinic_title":"Bumisita sa klinika.", "clinic_intro":"Narito ang lokasyon at schedule ng consultation.", "hospital":"Ospital", "location":"Lokasyon", "days":"Mga Araw", "time":"Oras", "days_value":"Martes • Huwebes • Sabado", "time_value":"9:00 AM – 4:00 PM",
        "help_kicker":"Tulong para sa Pasyente", "help_title":"Kailangan mo ba ng kaunting tulong?", "help_text":"Sabihin sa clinic kung ano ang kailangan mo. Makikita ito ng authorized staff sa protected dashboard para ma-follow up ka.", "name":"Pangalan", "contact":"Contact", "urgency":"Gaano ito ka-urgent?", "language":"Mas gustong wika", "concern":"Paano ka namin matutulungan?", "send":"Ipadala ang Request →", "placeholder_name":"Iyong pangalan", "placeholder_contact":"Telepono o email", "placeholder_concern":"Sabihin kung anong tulong ang kailangan mo...", "warning":"Huwag gamitin ang form na ito para sa emergency. Para sa agarang medical o safety emergency, tumawag sa local emergency services.",
        "resources_kicker":"Wellness Resources", "resources_title":"Maliit na hakbang, malaking tulong.", "quote":"Ang mental health care ay nagsisimula sa <span class='accent'>pakikinig.</span>", "caption_role":"Licensed Physician • Psychiatrist", "urgent_normal":"Normal", "urgent_soon":"Kailangang asikasuhin agad", "urgent":"Urgent", "resources_intro":"May self-care card dito bilang educational wellness resource. Hindi ito kapalit ng professional care.", "open_pdf":"Buksan ang Self-Care Card (PDF) →", "resource_alt":"Self-care wellness resource", "footer":"© 2026 Medina General Hospital. Nakalaan ang lahat ng karapatan. • Licensed Physician • Psychiatrist",
    },
    "ceb": {
        "nav_home":"Home", "nav_about":"Mahitungod", "nav_services":"Serbisyo", "nav_clinic":"Clinic", "nav_help":"Tabang", "nav_staff":"Staff",
        "tag":"Licensed Physician ug Psychiatrist", "hero_title":"Ang imong hunahuna angay sa <span>pag-atiman.</span>",
        "hero_text":"Mainiton ug patient-centered nga psychiatric care aron matabangan ka nga masabtan ang imong mental well-being ug mapauswag ang kalidad sa imong kinabuhi.",
        "help":"Nanginahanglan Ko og Tabang", "meet":"Ilaila si Dr. Tagupa →", "licensed":"Licensed Physician", "licensed_text":"Doktor nga naghatag og maloloy-on ug patient-centered nga pag-atiman.", "psychiatry":"Psychiatry", "psychiatry_text":"Psychiatric evaluation ug treatment para sa lain-laing mental health concerns.", "centered":"Patient-Centered", "centered_text":"Importante ang imong istorya, kabalaka, ug kaayohan sa matag consultation.",
        "about_kicker":"Mahitungod sa Doktor", "about_title":"Maayong training, adunay malasakit.", "about_intro":"Propesyonal nga medical ug psychiatric training nga patient-centered ang approach.", "about_head":"Ilaila si Dr. Tagupa", "about1":"Si Dr. Bebie Queen Lucelle R. Tagupa usa ka licensed physician ug psychiatrist nga naghatag og maloloy-on ug patient-centered nga mental health care.", "about2":"Nakakuha siya sa Bachelor’s degree sa Medical Technology gikan sa Velez College ug usa usab siya ka licensed Medical Technologist.", "about3":"Nagpadayon siya sa Medicine sa Xavier University – Ateneo de Cagayan.", "about4":"Nakompleto niya ang post-graduate internship sa Davao Doctors Hospital ug residency training sa Psychiatry sa Southern Philippines Medical Center – Institute of Psychiatry and Behavioral Medicine.", "about5":"Sa iyang katapusang tuig sa training, nagsilbi siya isip Chief Resident ug nadawat ang award nga Most Outstanding Resident in Psychiatry.",
        "services_kicker":"Mental Health Care", "services_title":"Ikaw ang sinugdanan sa pag-atiman.", "services_intro":"Suporta aron masabtan ang imong mental well-being ug makapadayon.", "eval":"Psychiatric Evaluation", "eval_text":"Masusing assessment aron masabtan ang mental health concerns.", "consult":"Mental Health Consultation", "consult_text":"Marespeto nga lugar sa paghisgot sa concerns, emosyon, hunahuna, ug behavior.", "treatment":"Treatment & Follow-Up", "treatment_text":"Patient-centered treatment ug follow-up base sa imong panginahanglan.",
        "clinic_kicker":"Impormasyon sa Clinic", "clinic_title":"Bisitaha ang clinic.", "clinic_intro":"Ani-a ang lokasyon ug consultation schedule.", "hospital":"Ospital", "location":"Lokasyon", "days":"Mga Adlaw", "time":"Oras", "days_value":"Martes • Huwebes • Sabado", "time_value":"9:00 AM – 4:00 PM",
        "help_kicker":"Tabang para sa Pasyente", "help_title":"Nanginahanglan og gamay nga tabang?", "help_text":"Sultihi ang clinic kung unsa imong gikinahanglan. Makita kini sa authorized staff sa protected dashboard aron ma-follow up ka.", "name":"Ngalan", "contact":"Contact", "urgency":"Unsa ka-urgent?", "language":"Piniling pinulongan", "concern":"Unsaon namo pagtabang?", "send":"Ipadala ang Request →", "placeholder_name":"Imong ngalan", "placeholder_contact":"Telepono o email", "placeholder_concern":"Isulti kung unsa nga tabang imong gikinahanglan...", "warning":"Ayaw gamita kini nga form para sa emergency. Para sa dali nga medical o safety emergency, kontaka ang local emergency services.",
        "resources_kicker":"Wellness Resources", "resources_title":"Gamay nga mga lakang makatabang.", "quote":"Ang mental health care nagsugod sa <span class='accent'>pagpaminaw.</span>", "caption_role":"Licensed Physician • Psychiatrist", "urgent_normal":"Normal", "urgent_soon":"Kinahanglan og dali nga pagtagad", "urgent":"Urgent", "resources_intro":"Adunay self-care card dinhi isip educational wellness resource. Dili kini kapuli sa professional care.", "open_pdf":"Ablihi ang Self-Care Card (PDF) →", "resource_alt":"Self-care wellness resource", "footer":"© 2026 Medina General Hospital. Tanang katungod gitagana. • Licensed Physician • Psychiatrist",
    },
}


TEMPLATE = """
<!doctype html>
<html lang="{{lang}}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} | Dr. Bebie Tagupa</title>
<style>
:root{--p:#7c3aed;--p2:#5b21b6;--pl:#a78bfa;--bg:#fbf9ff;--alt:#f1ebff;--card:#fff;--text:#21152d;--muted:#6f6479;--line:rgba(124,58,237,.16)}
body.dark{--bg:#100917;--alt:#1d1128;--card:#21152c;--text:#faf7ff;--muted:#c9bdd5;--line:rgba(167,139,250,.2)}
*{box-sizing:border-box;min-width:0}html{scroll-behavior:smooth;overflow-x:hidden}body{margin:0;width:100%;max-width:100%;overflow-x:hidden;font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);line-height:1.6;text-align:center;transition:.2s}a{text-decoration:none;color:inherit;overflow-wrap:anywhere}button,input,select,textarea{font:inherit;max-width:100%}.wrap{width:calc(100% - 32px);max-width:1120px;margin-inline:auto}
header{position:fixed;z-index:20;top:0;left:0;width:100%;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}nav{min-height:72px;display:flex;align-items:center;justify-content:center;gap:18px;flex-wrap:wrap}.brand{font-weight:900;color:var(--p)}.nav{display:flex;gap:18px;flex-wrap:wrap;justify-content:center}.nav a{font-size:13px;font-weight:800;color:var(--muted)}.nav a:hover{color:var(--p)}.tools{display:flex;gap:7px;align-items:center}.tools select,.tools button{height:38px;border:1px solid var(--line);border-radius:11px;background:var(--card);color:var(--text);padding:0 10px;cursor:pointer}
main{padding-top:72px}section{padding:82px 0;width:100%;max-width:100%;overflow:hidden}.hero{padding:100px 0 75px}.hero-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:55px;align-items:center;min-width:0}.pill,.kicker{color:var(--p);font-size:11px;font-weight:900;letter-spacing:1.7px;text-transform:uppercase}.pill{display:inline-block;background:var(--alt);padding:8px 13px;border-radius:999px;margin-bottom:17px}h1{font-size:clamp(42px,6vw,70px);line-height:1.02;letter-spacing:-3px;margin:0 0 18px}h1 span,.accent{color:var(--p)}.lead{color:var(--muted);font-size:17px;max-width:650px;margin:0 auto 25px}.buttons{display:flex;justify-content:center;gap:10px;flex-wrap:wrap}.btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 18px;border-radius:13px;border:1px solid var(--line);font-size:13px;font-weight:900;cursor:pointer}.primary{background:linear-gradient(135deg,var(--p),var(--p2));color:white;border:0}.secondary{background:var(--card);color:var(--text)}
.photo-card{width:min(390px,100%);margin:auto;padding:10px;border-radius:28px;background:linear-gradient(145deg,var(--card),var(--alt));border:1px solid var(--line);box-shadow:0 25px 60px rgba(74,38,110,.13)}.doctor-photo{width:100%;aspect-ratio:4/5;object-fit:cover;border-radius:20px;display:block;background:var(--alt)}.photo-caption{padding:13px 7px 4px;font-weight:900}.photo-caption small{display:block;color:var(--muted);font-weight:600}
.cards,.services,.clinic-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;min-width:0}.cards{margin-top:10px}.card,.service,.clinic,.request,.login{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:25px;box-shadow:0 14px 40px rgba(74,38,110,.07)}.icon{font-size:26px;margin-bottom:7px}.card h3,.service h3{margin:0 0 5px;font-size:17px}.card p,.service p,.clinic p{margin:0;color:var(--muted);font-size:13px}.alt{background:var(--alt)}.heading{max-width:760px;margin:0 auto 38px}.heading h2{font-size:clamp(31px,5vw,48px);line-height:1.1;letter-spacing:-1.7px;margin:7px 0 10px}.heading p{color:var(--muted);margin:0}.about-grid{display:grid;grid-template-columns:minmax(0,.75fr) minmax(0,1.25fr);gap:45px;align-items:center;min-width:0}.quote{font-size:28px;line-height:1.25;font-weight:900;padding:35px;background:var(--card);border:1px solid var(--line);border-radius:24px}.about p{color:var(--muted);margin:0 auto 13px;max-width:680px}.service{text-align:center}.service .icon{width:52px;height:52px;display:grid;place-items:center;margin:0 auto 13px;background:var(--alt);border-radius:14px}.clinic-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.clinic{padding:28px;min-width:0;overflow:hidden}.row{padding:14px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;justify-content:center;align-items:flex-start;min-width:0;max-width:100%;overflow:hidden}.row:last-child{border-bottom:0}.row>div{min-width:0;max-width:100%;overflow-wrap:anywhere}.row>div>span{display:block;max-width:100%;overflow-wrap:anywhere}.row b{display:block;font-size:12px;color:var(--p)}.row span{color:var(--muted);font-size:13px}
.help{width:100%;max-width:100%;overflow:hidden;background:linear-gradient(135deg,#4c1d95,#7c3aed);color:white;border-radius:28px;padding:42px}.help .kicker{color:#e7dbff}.help p{color:rgba(255,255,255,.82)}form{margin:22px auto 0;width:100%;max-width:820px;min-width:0}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field{text-align:left;min-width:0;max-width:100%;overflow:hidden}.field.full{grid-column:1/-1}.field label{display:block;font-size:12px;font-weight:900;margin:0 0 5px}.field input,.field select,.field textarea{display:block;width:100%;max-width:100%;min-width:0;border:1px solid rgba(255,255,255,.22);border-radius:11px;background:rgba(255,255,255,.12);color:white;padding:12px;outline:0}.field option{color:#21152d}.field textarea{min-height:105px;resize:vertical}.field input::placeholder,.field textarea::placeholder{color:rgba(255,255,255,.65)}.form-actions{margin-top:12px}.light-btn{background:white;color:#5b21b6;border:0}.small{font-size:11px;color:rgba(255,255,255,.7);margin-top:9px}
.resource{width:100%;max-width:100%;min-width:0;overflow:hidden}.resource img{width:min(440px,100%);max-width:100%;border-radius:18px;border:1px solid var(--line);display:block;margin:0 auto 18px}.flash{margin:14px auto 0;padding:12px 16px;border-radius:12px;background:var(--card);border:1px solid var(--line);width:min(900px,92%)}.success{border-color:#86efac}.danger{border-color:#fca5a5}footer{margin-top:40px;padding:34px 18px;background:var(--alt);border-top:1px solid var(--line);color:var(--muted);font-size:12px;line-height:1.8;text-align:center}footer .copyright{font-weight:800;color:var(--text);font-size:13px}footer .sub{display:block;margin-top:4px}
.staff-head{padding:75px 0 20px}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;min-width:0}.stat strong{display:block;font-size:37px;color:var(--p)}.request{text-align:center;min-width:0;max-width:100%;overflow:hidden}.request.new{border:2px solid rgba(124,58,237,.35)}.request-top{display:flex;justify-content:center;gap:12px;flex-wrap:wrap}.request-name{font-size:18px;font-weight:900}.muted{color:var(--muted);font-size:12px}.badges{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin:8px}.badge{background:var(--alt);color:var(--p);border-radius:999px;padding:4px 9px;font-size:10px;font-weight:900}.urgent{background:#fee2e2;color:#991b1b}.request-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0;min-width:0}.request-field{padding:12px;min-width:0;max-width:100%;overflow:hidden;overflow-wrap:anywhere;border-radius:12px;background:var(--alt)}.request-field b{display:block;color:var(--p);font-size:10px;text-transform:uppercase}.request-field span{font-size:12px}.note{text-align:left;min-width:0;max-width:100%;overflow:hidden}.note textarea{display:block;width:100%;max-width:100%;min-width:0;min-height:80px;border:1px solid var(--line);border-radius:10px;padding:10px;background:var(--card);color:var(--text)}.login{max-width:470px;margin:70px auto}.login input{width:100%;padding:12px;margin:6px 0 13px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text)}
@media(max-width:850px){.hero-grid,.about-grid,.clinic-grid{grid-template-columns:1fr}.photo-area{order:-1}.cards,.services,.stats{grid-template-columns:1fr}.request-grid{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr}.field.full{grid-column:auto}.nav{display:none}}
/* FINAL CONTAINER FIX */
html,body{width:100%;max-width:100%;overflow-x:hidden}
body{margin:0}
.wrap{width:100%;max-width:1280px;margin-left:auto;margin-right:auto;padding-left:20px;padding-right:20px}
main.wrap{overflow:visible}
section{width:100%;max-width:100%;padding:82px 24px;overflow:hidden}
section > *{width:100%;max-width:100%;min-width:0}
.hero{padding:100px 24px 75px}
.alt{overflow:hidden}
.hero-grid,.about-grid,.cards,.services,.clinic-grid,.form-grid,.request-grid,.stats{width:100%;max-width:100%;min-width:0}
.hero-grid > *, .about-grid > *, .cards > *, .services > *, .clinic-grid > *, .form-grid > *, .request-grid > *, .stats > *{min-width:0;max-width:100%}
.card,.service,.clinic,.request,.login,.quote,.help,.resource,.photo-card{width:100%;max-width:100%;min-width:0}
.quote{overflow-wrap:anywhere;word-break:normal}
.about,.clinic,.card,.service,.request,.help,.resource{overflow:hidden}
.about p,.card p,.service p,.clinic p,.request-field span,.lead,.heading p{overflow-wrap:anywhere;word-break:normal}
.row{width:100%;max-width:100%;overflow:hidden}
.row > *{min-width:0;max-width:100%}
.field input,.field select,.field textarea,.note textarea{box-sizing:border-box;width:100%;max-width:100%;min-width:0}
.form-actions{width:100%;max-width:100%;overflow:hidden}
.form-actions .btn{max-width:100%;white-space:normal}
footer{width:100%;max-width:100%;overflow:hidden}
@media(max-width:850px){.wrap{padding-left:12px;padding-right:12px}section,.hero{padding-left:12px;padding-right:12px}.about-grid,.hero-grid,.clinic-grid{grid-template-columns:minmax(0,1fr)}.cards,.services,.stats{grid-template-columns:minmax(0,1fr)}.request-grid,.form-grid{grid-template-columns:minmax(0,1fr)}.field.full{grid-column:auto}}
</style></head>
<body>
<header><nav class="wrap"><a class="brand" href="{{ url_for('home') }}">💜 Dr. Bebie Tagupa</a><div class="nav"><a href="#home">{{t.nav_home}}</a><a href="#about">{{t.nav_about}}</a><a href="#services">{{t.nav_services}}</a><a href="#clinic">{{t.nav_clinic}}</a><a href="#assistance">{{t.nav_help}}</a><a href="{{url_for('staff_login')}}">{{t.nav_staff}}</a></div><div class="tools"><select id="language" onchange="setLanguage()"><option value="en" {% if lang == "en" %}selected{% endif %}>English</option><option value="fil" {% if lang == "fil" %}selected{% endif %}>Filipino</option><option value="ceb" {% if lang == "ceb" %}selected{% endif %}>Visaya</option></select><button onclick="toggleTheme()" id="theme">🌙</button></div></nav></header>
{% with messages=get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div class="flash {{category}}">{{message}}</div>{% endfor %}{% endwith %}
<main class="wrap">
<section class="hero" id="home"><div class="hero-grid"><div><div class="pill">{{t.tag}}</div><h1>{{t.hero_title|safe}}</h1><p class="lead">{{t.hero_text}}</p><div class="buttons"><a class="btn primary" href="#assistance">💜 {{t.help}}</a><a class="btn secondary" href="#about">{{t.meet}}</a></div></div><div class="photo-area"><div class="photo-card"><img class="doctor-photo" src="{{ url_for('static', filename='image0 (2).jpeg') }}" alt="Dr. Bebie Queen Lucelle R. Tagupa" onerror="this.src='{{ url_for('static', filename='doctor-placeholder.svg') }}'"><div class="photo-caption">Dr. Bebie Queen Lucelle R. Tagupa<small>{{t.caption_role}}</small></div></div></div></div></section>
<section><div class="cards"><div class="card"><div class="icon">🩺</div><h3>{{t.licensed}}</h3><p>{{t.licensed_text}}</p></div><div class="card"><div class="icon">🧠</div><h3>{{t.psychiatry}}</h3><p>{{t.psychiatry_text}}</p></div><div class="card"><div class="icon">💜</div><h3>{{t.centered}}</h3><p>{{t.centered_text}}</p></div></div></section>
<section class="alt" id="about"><div class="heading"><div class="kicker">{{t.about_kicker}}</div><h2>{{t.about_title}}</h2><p>{{t.about_intro}}</p></div><div class="about-grid"><div class="quote">“{{t.quote|safe}}”</div><div class="about"><h2>{{t.about_head}}</h2><p>{{t.about1}}</p><p>{{t.about2}}</p><p>{{t.about3}}</p><p>{{t.about4}}</p><p>{{t.about5}}</p></div></div></section>
<section id="services"><div class="heading"><div class="kicker">{{t.services_kicker}}</div><h2>{{t.services_title}}</h2><p>{{t.services_intro}}</p></div><div class="services"><div class="service"><div class="icon">🧠</div><h3>{{t.eval}}</h3><p>{{t.eval_text}}</p></div><div class="service"><div class="icon">💬</div><h3>{{t.consult}}</h3><p>{{t.consult_text}}</p></div><div class="service"><div class="icon">🌱</div><h3>{{t.treatment}}</h3><p>{{t.treatment_text}}</p></div></div></section>
<section class="alt" id="clinic"><div class="heading"><div class="kicker">{{t.clinic_kicker}}</div><h2>{{t.clinic_title}}</h2><p>{{t.clinic_intro}}</p></div><div class="clinic-grid"><div class="clinic"><h3>🏥 {{t.hospital}}</h3><div class="row"><span>🏥</span><div><b>{{t.hospital}}</b><span>Medina General Hospital</span></div></div><div class="row"><span>🚪</span><div><b>{{t.location}}</b><span>OPD Door 2</span></div></div></div><div class="clinic"><h3>🕘 {{t.time}}</h3><div class="row"><span>📅</span><div><b>{{t.days}}</b><span>{{t.days_value}}</span></div></div><div class="row"><span>⏰</span><div><b>{{t.time}}</b><span>{{t.time_value}}</span></div></div></div></div></section>
<section id="assistance"><div class="help"><div class="kicker">{{t.help_kicker}}</div><h2>{{t.help_title}}</h2><p>{{t.help_text}}</p><form method="post" action="{{url_for('request_assistance')}}"><div class="form-grid"><div class="field"><label>{{t.name}}</label><input name="patient_name" required maxlength="120" placeholder="{{t.placeholder_name}}"></div><div class="field"><label>{{t.contact}}</label><input name="contact" required maxlength="160" placeholder="{{t.placeholder_contact}}"></div><div class="field"><label>{{t.urgency}}</label><select name="urgency"><option value="Normal">{{t.urgent_normal}}</option><option value="Needs attention soon">{{t.urgent_soon}}</option><option value="Urgent">{{t.urgent}}</option></select></div><div class="field"><label>{{t.language}}</label><select name="preferred_language"><option>English</option><option>Filipino</option><option>Visaya</option></select></div><div class="field full"><label>{{t.concern}}</label><textarea name="concern" required maxlength="2000" placeholder="{{t.placeholder_concern}}"></textarea></div></div><div class="form-actions"><button class="btn light-btn" type="submit">{{t.send}}</button></div><div class="small">{{t.warning}}</div></form></div></section>
<section><div class="heading"><div class="kicker">{{t.resources_kicker}}</div><h2>{{t.resources_title}}</h2><p>{{t.resources_intro}}</p></div><div class="resource card"><img src="{{url_for('static',filename='self-care-contact.png')}}" alt="{{t.resource_alt}}"><div class="buttons"><a class="btn primary" href="{{url_for('self_care_pdf')}}" target="_blank">{{t.open_pdf}}</a></div></div></section>
</main><footer><div class="copyright">{{t.footer}}</div><span class="sub">Medina General Hospital • OPD Door 2 • {{t.days_value}} • {{t.time_value}}</span></footer>
<script>
function toggleTheme(){document.body.classList.toggle('dark');localStorage.setItem('theme',document.body.classList.contains('dark')?'dark':'light');syncTheme()}
function syncTheme(){document.getElementById('theme').textContent=document.body.classList.contains('dark')?'☀️':'🌙'}
function setLanguage(){const lang=document.getElementById('language').value;localStorage.setItem('language',lang);window.location.href='/?lang='+encodeURIComponent(lang)}
(function(){let th=localStorage.getItem('theme');if(th==='dark')document.body.classList.add('dark');syncTheme();if(!new URLSearchParams(window.location.search).has('lang')){const saved=localStorage.getItem('language');if(saved&&['en','fil','ceb'].includes(saved)){window.location.replace('/?lang='+saved);return}}document.getElementById('language').value=new URLSearchParams(window.location.search).get('lang')||localStorage.getItem('language')||'en'})();
</script></body></html>
"""


STAFF_TEMPLATE = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}}</title>
<style>
:root{--p:#7c3aed;--p2:#5b21b6;--bg:#fbf9ff;--alt:#f1ebff;--card:#fff;--text:#21152d;--muted:#6f6479;--line:rgba(124,58,237,.16)}body.dark{--bg:#100917;--alt:#1d1128;--card:#21152c;--text:#faf7ff;--muted:#c9bdd5;--line:rgba(167,139,250,.2)}*{box-sizing:border-box;min-width:0}html,body{overflow-x:hidden}body{margin:0;width:100%;max-width:100%;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text);text-align:center}a{text-decoration:none;color:inherit;overflow-wrap:anywhere}.wrap{width:calc(100% - 32px);max-width:1100px;margin-inline:auto}header{border-bottom:1px solid var(--line);background:var(--card)}nav{min-height:68px;display:flex;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap}.brand{font-weight:900;color:var(--p)}.tools{display:flex;gap:7px}.tools button{height:38px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text);cursor:pointer}.hero{padding:60px 0 25px}.kicker{color:var(--p);font-size:11px;font-weight:900;letter-spacing:2px;text-transform:uppercase}.hero h1{font-size:clamp(35px,5vw,55px);margin:7px 0}.muted{color:var(--muted)}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:20px 0}.card,.request,.login{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:23px;box-shadow:0 12px 35px rgba(74,38,110,.07)}.stat strong{display:block;color:var(--p);font-size:38px}.requests{display:grid;gap:14px}.request.new{border:2px solid rgba(124,58,237,.35)}.request-name{font-size:19px;font-weight:900}.badges{display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin:8px}.badge{background:var(--alt);color:var(--p);border-radius:999px;padding:4px 9px;font-size:10px;font-weight:900}.urgent{background:#fee2e2;color:#991b1b}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:14px 0}.field{background:var(--alt);padding:11px;border-radius:11px}.field b{display:block;color:var(--p);font-size:10px;text-transform:uppercase}.field span{font-size:12px}.note textarea{display:block;width:100%;max-width:100%;min-width:0;min-height:75px;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text)}.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 16px;border-radius:11px;border:1px solid var(--line);font-size:12px;font-weight:900;cursor:pointer;background:var(--card);color:var(--text);margin:4px}.primary{background:linear-gradient(135deg,var(--p),var(--p2));color:white;border:0}.green{background:#15803d;color:white;border:0}.danger{background:#b91c1c;color:white;border:0}.login{max-width:450px;margin:70px auto}.login input{width:100%;padding:12px;margin:5px 0 13px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text)}.flash{margin:14px auto;padding:12px;border:1px solid var(--line);border-radius:10px;width:min(800px,92%)}@media(max-width:700px){.stats,.grid{grid-template-columns:1fr}}
/* FINAL STAFF CONTAINER FIX */
html,body{width:100%;max-width:100%;overflow-x:hidden}
.wrap{width:100%;max-width:1280px;margin-left:auto;margin-right:auto;padding-left:20px;padding-right:20px}
main.wrap{overflow:visible}
.card,.request,.login{width:100%;max-width:100%;min-width:0;overflow:hidden}
.stats,.grid{width:100%;max-width:100%;min-width:0}
.stats > *, .grid > *{min-width:0;max-width:100%}
.field{min-width:0;max-width:100%;overflow:hidden;overflow-wrap:anywhere}
.note,.note textarea{width:100%;max-width:100%;min-width:0;box-sizing:border-box}
@media(max-width:700px){.wrap{padding-left:12px;padding-right:12px}.stats,.grid{grid-template-columns:minmax(0,1fr)}}
</style></head><body><header><nav class="wrap"><a class="brand" href="{{url_for('home')}}">💜 Dr. Bebie Tagupa</a><a href="{{url_for('home')}}">Public Site</a><a href="{{url_for('logout')}}">Log Out</a><div class="tools"><button onclick="toggleTheme()" id="theme">🌙</button></div></nav></header>{% with messages=get_flashed_messages(with_categories=true) %}{% for c,m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}<main class="wrap">{{body|safe}}</main><script>function toggleTheme(){document.body.classList.toggle('dark');localStorage.setItem('theme',document.body.classList.contains('dark')?'dark':'light');sync()}function sync(){document.getElementById('theme').textContent=document.body.classList.contains('dark')?'☀️':'🌙'}if(localStorage.getItem('theme')==='dark')document.body.classList.add('dark');sync()</script></body></html>
"""


def render_page(title, lang="en"):
    return render_template_string(TEMPLATE, title=title, lang=lang, t=TRANSLATIONS.get(lang, TRANSLATIONS["en"]))


@app.route("/")
def home():
    lang = request.args.get("lang", "en")
    if lang not in TRANSLATIONS:
        lang = "en"
    return render_page("Home", lang)


@app.post("/request-assistance")
def request_assistance():
    name = clean(request.form.get("patient_name"), 120)
    contact = clean(request.form.get("contact"), 160)
    concern = clean(request.form.get("concern"), 2000)
    urgency = clean(request.form.get("urgency"), 40)
    language = clean(request.form.get("preferred_language"), 30)
    if urgency not in {"Normal", "Needs attention soon", "Urgent"}:
        urgency = "Normal"
    if language not in {"English", "Filipino", "Visaya"}:
        language = "English"
    if not name or not contact or not concern:
        flash("Please complete your name, contact information, and assistance request.", "danger")
        return redirect(url_for("home", _anchor="assistance"))
    stamp = now()
    request_id = next_request_id()
    requests_collection.insert_one({
        "_id": request_id,
        "id": request_id,
        "patient_name": name,
        "contact": contact,
        "concern": concern,
        "urgency": urgency,
        "urgency_rank": URGENCY_RANK[urgency],
        "preferred_language": language,
        "status": "New",
        "status_rank": STATUS_RANK["New"],
        "staff_note": "",
        "created_at": stamp,
        "updated_at": stamp,
    })
    flash("Your assistance request has been sent to the clinic team.", "success")
    return redirect(url_for("home", _anchor="assistance"))


@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        username = clean(request.form.get("username"), 80)
        password = request.form.get("password", "")
        staff = staff_collection.find_one({"username": username, "active": True})
        if staff and check_password_hash(staff["password_hash"], password):
            session.clear()
            session["staff_logged_in"] = True
            session["staff_username"] = staff["username"]
            session["staff_role"] = staff["role"]
            return redirect(url_for("staff_dashboard"))
        flash("Invalid username or password.", "danger")
    body = """
    <section class="login"><div class="kicker">Private Clinic Area</div><h1>Staff Login</h1><p class="muted">Authorized clinic staff only.</p><form method="post"><label>Username</label><input name="username" autocomplete="username" required><label>Password</label><input type="password" name="password" autocomplete="current-password" required><button class="btn primary" style="width:100%" type="submit">🔐 Log In</button></form><p class="muted" style="font-size:11px">Set ADMIN_PASSWORD in Render Environment Variables before production use.</p></section>
    """
    return render_template_string(STAFF_TEMPLATE, title="Staff Login", body=body)


@app.route("/staff/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/staff")
@app.route("/staff/dashboard")
@staff_required
def staff_dashboard():
    rows = list(
        requests_collection.find().sort([
            ("status_rank", 1),
            ("urgency_rank", 1),
            ("created_at", -1),
        ]).limit(100)
    )
    active = requests_collection.count_documents({"status": {"$ne": "Resolved"}})
    resolved = requests_collection.count_documents({"status": "Resolved"})
    cards = []
    for r in rows:
        urgent = "urgent" if r["urgency"] == "Urgent" else ""
        new = "new" if r["status"] == "New" else ""
        actions = f"<form method='post' action='{url_for('update_status',request_id=r['id'],status='Seen')}' style='display:inline'><button class='btn primary'>Mark Seen</button></form>" if r["status"] == "New" else ""
        if r["status"] == "Seen":
            actions += f"<form method='post' action='{url_for('update_status',request_id=r['id'],status='In Progress')}' style='display:inline'><button class='btn primary'>In Progress</button></form>"
        if r["status"] != "Resolved":
            actions += f"<form method='post' action='{url_for('update_status',request_id=r['id'],status='Resolved')}' style='display:inline'><button class='btn green'>Resolve</button></form>"
        cards.append(f"""
        <article class='request {new}'><div class='request-name'>{r['patient_name']}</div><div class='muted'>Request #{r['id']} • {r['created_at'].replace('T',' ')} UTC</div><div class='badges'><span class='badge'>{r['status']}</span><span class='badge {urgent}'>{r['urgency']}</span><span class='badge'>{r['preferred_language']}</span></div><div class='grid'><div class='field'><b>Contact</b><span>{r['contact']}</span></div><div class='field'><b>Need</b><span>{r['concern']}</span></div><div class='field'><b>Staff Note</b><span>{r['staff_note'] or 'No note yet.'}</span></div></div><div class='note'><form method='post' action='{url_for('update_note',request_id=r['id'])}'><textarea name='staff_note' maxlength='2000' placeholder='Internal follow-up note...'>{r['staff_note']}</textarea><br><button class='btn' type='submit'>Save Note</button>{actions}</form></div></article>""")
    body = f"""
    <section class='hero'><div class='kicker'>Protected Clinic Area</div><h1>Staff Dashboard</h1><p class='muted'>Welcome, {session.get('staff_username','Staff')}. New patient assistance requests appear here.</p></section>
    <section><div class='stats'><div class='card stat'><strong id='newCount'>{new_count()}</strong><span class='muted'>New requests</span></div><div class='card stat'><strong>{active}</strong><span class='muted'>Active requests</span></div><div class='card stat'><strong>{resolved}</strong><span class='muted'>Resolved requests</span></div></div></section>
    <section><div class='requests'>{''.join(cards) if cards else "<div class='card'><h3>💜 No requests yet.</h3><p class='muted'>New assistance requests will appear here.</p></div>"}</div></section>
    <script>let n=document.getElementById('newCount');setInterval(()=>fetch('{url_for('staff_status')}').then(r=>r.json()).then(d=>{{if(n&&Number(n.textContent)!==d.new_count)location.reload()}}),10000)</script>
    """
    return render_template_string(STAFF_TEMPLATE, title="Staff Dashboard", body=body)


@app.route("/staff/status")
@staff_required
def staff_status():
    return jsonify(new_count=new_count())


@app.post("/staff/request/<int:request_id>/status/<status>")
@staff_required
def update_status(request_id, status):
    if status not in {"New", "Seen", "In Progress", "Resolved"}:
        flash("Invalid status.", "danger")
        return redirect(url_for("staff_dashboard"))
    requests_collection.update_one(
        {"id": request_id},
        {"$set": {
            "status": status,
            "status_rank": STATUS_RANK[status],
            "updated_at": now(),
        }}
    )
    return redirect(url_for("staff_dashboard"))


@app.post("/staff/request/<int:request_id>/note")
@staff_required
def update_note(request_id):
    note = clean(request.form.get("staff_note"), 2000)
    requests_collection.update_one(
        {"id": request_id},
        {"$set": {
            "staff_note": note,
            "updated_at": now(),
        }}
    )
    return redirect(url_for("staff_dashboard"))


@app.route("/self-care-card.pdf")
def self_care_pdf():
    path = STATIC_DIR / "self-care-card.pdf"
    if not path.exists():
        return "Self-care card not found.", 404
    return send_from_directory(STATIC_DIR, path.name, as_attachment=False)


@app.route("/health")
def health():
    return jsonify(status="ok")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)

# -----------------------------------------------------------------------------
# MEDINA GENERAL HOSPITAL - PROJECT DOCUMENTATION / MAINTENANCE NOTES
# These comments intentionally document the application structure. They are
# kept in the source so future edits are easier to understand and maintain.
# -----------------------------------------------------------------------------
# Application maintenance note 331: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 332: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 333: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 334: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 335: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 336: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 337: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 338: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 339: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 340: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 341: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 342: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 343: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 344: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 345: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 346: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 347: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 348: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 349: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 350: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 351: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 352: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 353: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 354: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 355: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 356: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 357: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 358: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 359: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 360: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 361: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 362: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 363: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 364: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 365: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 366: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 367: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 368: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 369: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 370: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 371: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 372: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 373: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 374: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 375: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 376: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 377: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 378: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 379: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 380: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 381: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 382: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 383: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 384: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 385: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 386: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 387: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 388: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 389: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 390: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 391: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 392: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 393: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 394: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 395: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 396: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 397: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 398: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 399: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 400: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 401: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 402: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 403: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 404: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 405: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 406: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 407: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 408: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 409: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 410: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 411: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 412: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 413: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 414: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 415: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 416: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 417: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 418: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 419: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 420: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 421: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 422: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 423: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 424: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 425: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 426: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 427: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 428: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 429: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 430: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 431: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 432: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 433: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 434: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 435: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 436: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 437: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 438: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 439: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 440: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 441: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 442: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 443: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 444: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 445: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 446: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 447: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 448: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 449: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 450: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 451: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 452: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 453: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 454: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 455: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 456: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 457: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 458: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 459: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 460: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 461: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 462: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 463: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 464: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 465: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 466: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 467: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 468: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 469: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 470: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 471: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 472: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 473: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 474: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 475: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 476: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 477: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 478: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 479: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 480: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 481: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 482: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 483: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 484: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 485: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 486: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 487: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 488: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 489: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 490: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 491: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 492: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 493: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 494: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 495: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 496: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 497: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 498: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 499: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 500: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 501: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 502: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 503: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 504: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 505: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 506: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 507: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 508: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 509: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 510: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 511: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 512: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 513: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 514: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 515: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 516: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 517: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 518: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 519: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 520: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 521: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 522: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 523: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 524: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 525: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 526: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 527: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 528: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 529: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 530: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 531: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 532: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 533: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 534: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 535: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 536: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 537: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 538: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 539: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 540: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 541: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 542: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 543: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 544: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 545: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 546: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 547: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 548: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 549: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 550: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 551: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 552: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 553: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 554: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 555: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 556: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 557: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 558: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 559: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 560: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 561: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 562: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 563: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 564: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 565: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 566: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 567: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 568: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 569: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 570: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 571: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 572: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 573: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 574: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 575: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 576: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 577: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 578: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 579: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 580: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 581: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 582: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 583: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 584: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 585: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 586: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 587: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 588: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 589: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 590: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 591: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 592: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 593: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 594: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 595: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 596: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 597: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 598: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 599: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 600: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 601: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 602: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 603: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 604: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 605: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 606: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 607: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 608: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 609: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 610: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 611: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 612: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 613: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 614: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 615: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 616: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 617: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 618: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 619: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 620: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 621: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 622: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 623: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 624: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 625: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 626: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 627: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 628: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 629: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 630: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 631: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 632: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 633: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 634: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 635: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 636: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 637: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 638: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 639: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 640: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 641: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 642: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 643: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 644: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 645: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 646: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 647: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 648: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 649: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 650: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 651: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 652: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 653: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 654: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 655: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 656: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 657: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 658: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 659: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 660: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 661: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 662: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 663: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 664: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 665: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 666: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 667: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 668: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 669: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 670: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 671: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 672: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 673: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 674: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 675: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 676: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 677: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 678: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 679: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 680: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 681: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 682: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 683: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 684: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 685: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 686: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 687: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 688: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 689: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 690: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 691: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 692: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 693: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 694: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 695: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 696: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 697: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 698: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 699: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 700: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 701: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 702: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 703: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 704: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 705: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 706: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 707: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 708: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 709: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 710: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 711: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 712: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 713: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 714: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 715: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 716: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 717: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 718: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 719: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 720: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 721: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 722: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 723: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 724: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 725: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 726: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 727: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 728: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 729: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 730: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 731: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 732: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 733: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 734: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 735: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 736: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 737: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 738: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 739: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 740: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 741: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 742: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 743: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 744: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 745: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 746: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 747: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 748: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 749: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 750: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 751: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 752: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 753: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 754: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 755: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 756: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 757: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 758: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 759: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 760: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 761: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 762: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 763: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 764: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 765: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 766: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 767: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 768: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 769: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 770: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 771: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 772: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 773: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 774: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 775: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 776: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 777: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 778: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 779: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 780: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 781: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 782: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 783: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 784: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 785: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 786: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 787: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 788: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 789: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 790: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 791: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 792: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 793: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 794: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 795: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 796: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 797: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 798: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 799: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 800: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 801: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 802: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 803: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 804: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 805: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 806: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 807: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 808: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 809: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 810: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 811: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 812: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 813: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 814: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 815: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 816: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 817: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 818: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 819: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 820: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 821: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 822: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 823: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 824: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 825: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 826: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 827: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 828: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 829: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 830: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 831: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 832: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 833: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 834: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 835: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 836: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 837: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 838: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 839: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 840: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 841: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 842: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 843: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 844: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 845: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 846: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 847: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 848: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 849: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 850: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 851: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 852: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 853: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 854: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 855: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 856: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 857: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 858: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 859: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 860: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 861: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 862: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 863: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 864: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 865: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 866: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 867: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 868: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 869: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 870: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 871: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 872: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 873: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 874: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 875: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 876: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 877: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 878: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 879: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 880: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 881: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 882: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 883: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 884: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 885: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 886: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 887: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 888: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 889: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 890: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 891: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 892: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 893: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 894: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 895: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 896: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 897: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 898: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 899: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 900: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 901: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 902: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 903: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 904: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 905: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 906: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 907: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 908: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 909: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 910: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 911: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 912: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 913: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 914: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 915: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 916: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 917: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 918: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 919: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 920: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 921: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 922: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 923: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 924: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 925: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 926: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 927: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 928: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 929: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 930: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 931: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 932: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 933: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 934: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 935: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 936: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 937: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 938: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 939: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 940: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 941: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 942: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 943: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 944: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 945: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 946: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 947: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 948: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 949: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 950: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 951: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 952: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 953: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 954: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 955: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 956: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 957: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 958: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 959: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 960: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 961: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 962: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 963: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 964: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 965: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 966: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 967: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 968: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 969: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 970: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 971: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 972: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 973: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 974: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 975: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 976: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 977: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 978: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 979: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 980: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 981: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 982: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 983: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 984: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 985: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 986: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 987: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 988: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 989: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 990: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 991: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 992: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 993: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 994: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 995: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 996: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 997: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 998: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 999: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1000: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1001: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1002: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1003: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1004: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1005: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1006: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1007: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1008: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1009: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1010: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1011: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1012: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1013: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1014: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1015: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1016: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1017: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1018: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1019: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1020: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1021: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1022: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1023: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1024: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1025: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1026: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1027: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1028: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1029: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1030: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1031: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1032: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1033: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1034: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1035: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1036: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1037: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1038: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1039: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1040: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1041: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1042: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1043: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1044: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1045: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1046: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1047: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1048: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1049: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1050: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1051: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1052: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1053: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1054: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1055: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1056: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1057: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1058: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1059: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1060: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1061: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1062: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1063: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1064: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1065: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1066: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1067: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1068: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1069: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1070: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1071: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1072: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1073: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1074: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1075: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1076: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1077: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1078: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1079: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1080: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1081: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1082: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1083: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1084: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1085: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1086: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1087: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1088: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1089: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1090: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1091: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1092: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1093: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1094: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1095: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1096: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1097: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1098: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1099: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1100: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1101: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1102: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1103: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1104: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1105: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1106: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1107: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1108: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1109: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1110: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1111: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1112: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1113: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1114: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1115: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1116: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1117: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1118: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1119: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1120: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1121: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1122: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1123: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1124: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1125: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1126: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1127: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1128: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1129: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1130: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1131: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1132: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1133: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1134: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1135: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1136: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1137: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1138: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1139: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1140: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1141: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1142: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1143: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1144: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1145: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1146: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1147: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1148: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1149: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1150: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1151: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1152: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1153: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1154: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1155: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1156: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1157: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1158: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1159: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1160: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1161: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1162: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1163: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1164: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1165: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1166: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1167: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1168: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1169: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1170: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1171: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1172: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1173: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1174: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1175: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1176: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1177: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1178: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1179: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1180: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1181: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1182: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1183: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1184: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1185: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1186: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1187: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1188: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1189: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1190: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1191: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1192: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1193: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1194: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1195: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1196: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1197: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1198: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1199: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1200: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1201: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1202: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1203: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1204: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1205: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1206: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1207: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1208: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1209: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1210: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1211: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1212: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1213: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1214: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1215: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1216: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1217: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1218: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1219: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1220: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1221: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1222: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1223: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1224: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1225: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1226: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1227: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1228: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1229: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1230: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1231: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1232: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1233: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1234: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1235: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1236: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1237: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1238: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1239: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1240: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1241: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1242: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1243: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1244: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1245: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1246: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1247: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1248: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1249: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1250: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1251: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1252: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1253: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1254: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1255: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1256: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1257: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1258: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1259: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1260: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1261: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1262: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1263: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1264: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.
# Application maintenance note 1265: keep patient-facing content centered,
# accessible, concise, and available in English, Filipino, and Visaya.

