#!/usr/bin/env python3
"""
GoForAI - Backend Flask
Serveur pour la plateforme de formation GoForAI
Avec auth par téléphone et paiement crypto (MaxelPay)
"""

import os
import json
import sqlite3
import hashlib
import hmac
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, render_template, jsonify, request, send_from_directory, session, g

logging.basicConfig(level=logging.WARNING, format='[%(asctime)s] %(levelname)s %(message)s')
log = logging.getLogger('goforai')
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s'))
log.addHandler(handler)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'goforai-dev-secret-key-2024')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# ── Configuration ──────────────────────────────────────────────────────────

PAYMENT_PRICE_USD = float(os.environ.get('PAYMENT_PRICE_USD', '10.14'))
MAXELPAY_API_KEY = os.environ.get('MAXELPAY_API_KEY', 'pk_live_qkVKErwKOoe9xWeewizm0jUrlEIqD2zK')
MAXELPAY_SECRET_KEY = os.environ.get('MAXELPAY_SECRET_KEY', '')
MAXELPAY_BASE = 'https://api.maxelpay.com/api/v1'
SITE_BASE_URL = os.environ.get('SITE_BASE_URL', 'https://goforai.onrender.com')
PUBLIC_URL = os.environ.get('PUBLIC_URL', 'https://goforai.onrender.com')

FREE_COURSE_IDS = {
    'ceb90efb-3a1a-47f9-b179-9455ff0bb857',  # Guide de Base (PDFs gratuits)
    '1a1c5624-4683-43e9-ab27-82794e7d44f5',  # Module 1 (gratuit)
}

if os.environ.get('NETLIFY') == 'true':
    DB_PATH = os.path.join('/tmp', 'goforai.db')
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'goforai.db')

# ── Données des cours et leçons ────────────────────────────────────────────

COURSES = [
    {
        "id": "ceb90efb-3a1a-47f9-b179-9455ff0bb857",
        "title": "Guide de Base",
        "description": "Maîtriser comment rédiger des prompts que l'IA comprend",
        "sort_order": 0,
        "icon": "book-open",
        "color": "#3b82f6"
    },
    {
        "id": "1a1c5624-4683-43e9-ab27-82794e7d44f5",
        "title": "Module 1 : Création de portraits",
        "description": "La méthode pour créer des portraits indissociables d'une vraie séance photo professionnelle.",
        "sort_order": 1,
        "icon": "camera",
        "color": "#8b5cf6"
    },
    {
        "id": "3299e494-47d3-4320-8e5c-325a4331a9cb",
        "title": "Module 2 : Retouche sur PC",
        "description": "Le processus pour retoucher des images sur Photoshop comme un pro sur PC",
        "sort_order": 2,
        "icon": "monitor",
        "color": "#06b6d4"
    },
    {
        "id": "10822f50-1a68-4a15-a13d-8172b0042b64",
        "title": "Module 3 : Retouche sur téléphone",
        "description": "Le processus pour retoucher des images sur Photopea comme un pro sur mobile",
        "sort_order": 3,
        "icon": "smartphone",
        "color": "#10b981"
    },
    {
        "id": "e3b8591a-22ec-4002-8939-e343e2d20e54",
        "title": "Module 4 : Cas pratique",
        "description": "Créer un studio virtuel et le monétiser sur Facebook",
        "sort_order": 4,
        "icon": "briefcase",
        "color": "#f59e0b"
    },
    {
        "id": "6a73b06c-f39b-4059-992a-92ae89549789",
        "title": "Module 5 : Cas pratique",
        "description": "Générer des images 4K en haute résolution et réaliser une retouche avancée",
        "sort_order": 5,
        "icon": "image",
        "color": "#ef4444"
    },
    {
        "id": "930079ec-339e-4328-821a-33355f362cbf",
        "title": "Module 6 : Séance Photo Virtuelle",
        "description": "Créer des séries de photos cohérentes sur Google Flow, sans retouche",
        "sort_order": 6,
        "icon": "aperture",
        "color": "#ec4899"
    },
    {
        "id": "70b46420-1536-4daf-9002-06ee754ae907",
        "title": "Module 7 : Shooting Produit IA",
        "description": "Générer des visuels produits e-commerces qui font vendre sur Whisk AI.",
        "sort_order": 7,
        "icon": "shopping-bag",
        "color": "#6366f1"
    },
    {
        "id": "6206f74f-aaec-4825-b278-e92fdd3a76c0",
        "title": "Module 8 : Création de contenu",
        "description": "Générer des idées de contenus et rédiger votre premier post avec Chat GPT",
        "sort_order": 8,
        "icon": "pen-tool",
        "color": "#14b8a6"
    }
]

LESSONS = [
    {
        "course_id": "ceb90efb-3a1a-47f9-b179-9455ff0bb857",
        "title": "La Bible du Prompting (Ebook PDF)",
        "description": "Maîtrise comment rédiger des prompts que l'IA comprend. Télécharge le guide complet au format PDF.",
        "lesson_type": "pdf",
        "video_id": None,
        "sort_order": 0,
        "local_pdf": "downloads_goforai/GUIDE_DE_BASE/01_LA_BIBLE_DU_PROMPTING.pdf",
        "duration": "45 min de lecture"
    },
    {
        "course_id": "1a1c5624-4683-43e9-ab27-82794e7d44f5",
        "title": "Créer des portraits indissociables d'une vraie séance photo professionnelle",
        "description": "Techniques avancées pour générer des portraits réalistes avec l'IA.",
        "lesson_type": "video",
        "video_id": "8d7qu0rOgjk",
        "sort_order": 0,
        "duration": "52 min"
    },
    {
        "course_id": "3299e494-47d3-4320-8e5c-325a4331a9cb",
        "title": "Retoucher des images sur Photoshop comme un pro sur PC",
        "description": "Workflow complet de retouche photo professionnelle sur PC.",
        "lesson_type": "video",
        "video_id": "7-gQwJZDDeM",
        "sort_order": 0,
        "duration": "48 min"
    },
    {
        "course_id": "10822f50-1a68-4a15-a13d-8172b0042b64",
        "title": "Retoucher des images sur Photopea comme un pro sur mobile",
        "description": "Maîtrisez la retouche photo directement depuis votre smartphone.",
        "lesson_type": "video",
        "video_id": "-bOVTbofiBI",
        "sort_order": 0,
        "duration": "41 min"
    },
    {
        "course_id": "e3b8591a-22ec-4002-8939-e343e2d20e54",
        "title": "Créer un studio virtuel et le monétiser sur Facebook",
        "description": "Construisez votre studio photo virtuel et générez des revenus.",
        "lesson_type": "video",
        "video_id": "4METyVyFNyM",
        "sort_order": 0,
        "duration": "55 min"
    },
    {
        "course_id": "6a73b06c-f39b-4059-992a-92ae89549789",
        "title": "Générer des images 4K en haute résolution et réaliser une retouche avancée",
        "description": "Créez des images 4K ultra-détaillées et apprenez les techniques de retouche avancée.",
        "lesson_type": "video",
        "video_id": "JEpQLu4szYI",
        "sort_order": 0,
        "duration": "1h 03 min"
    },
    {
        "course_id": "930079ec-339e-4328-821a-33355f362cbf",
        "title": "Créer des séries de photos cohérentes sur Google Flow, sans retouche",
        "description": "Générez des séries photo cohérentes en un seul workflow.",
        "lesson_type": "video",
        "video_id": "MVXnHnZXl04",
        "sort_order": 0,
        "duration": "47 min"
    },
    {
        "course_id": "ceb90efb-3a1a-47f9-b179-9455ff0bb857",
        "title": "Guide express — Créer des séries de photos en variante",
        "description": "Apprenez à créer rapidement des séries de photos variées.",
        "lesson_type": "pdf",
        "video_id": None,
        "sort_order": 1,
        "local_pdf": "downloads_goforai/MODULE_6___Séance_Photo_Virtuelle/02_guide-series-photos-variantes.pdf",
        "duration": "20 min de lecture"
    },
    {
        "course_id": "70b46420-1536-4daf-9002-06ee754ae907",
        "title": "Générer des visuels produits e-commerce qui font vendre sur Whisk AI",
        "description": "Créez des visuels produits professionnels pour booster vos ventes.",
        "lesson_type": "video",
        "video_id": "FAxJs5TMZ-0",
        "sort_order": 0,
        "duration": "49 min"
    },
    {
        "course_id": "6206f74f-aaec-4825-b278-e92fdd3a76c0",
        "title": "Générer des idées de contenu et rédiger votre premier post avec ChatGPT",
        "description": "Maîtrisez la création de contenu avec l'aide de l'IA.",
        "lesson_type": "video",
        "video_id": "tJNvchHDfWQ",
        "sort_order": 0,
        "duration": "38 min"
    }
]

# ── Base de données SQLite ─────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

app.teardown_appcontext(close_db)

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            verification_code TEXT,
            code_expires_at TIMESTAMP,
            is_verified BOOLEAN DEFAULT 0,
            has_paid BOOLEAN DEFAULT 0,
            payment_session_id TEXT,
            payment_status TEXT DEFAULT 'none',
            payment_amount_usd REAL DEFAULT 19.99,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT,
            checkout_url TEXT,
            order_id TEXT,
            amount_usd REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')

    cursor = db.execute("PRAGMA table_info(payments)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'session_id' not in cols:
        for col_def in [('session_id', 'TEXT'), ('checkout_url', 'TEXT'), ('order_id', 'TEXT')]:
            db.execute(f"ALTER TABLE payments ADD COLUMN {col_def[0]} {col_def[1]}")
    cursor = db.execute("PRAGMA table_info(users)")
    user_cols = [col[1] for col in cursor.fetchall()]
    if 'payment_session_id' not in user_cols:
        db.execute("ALTER TABLE users ADD COLUMN payment_session_id TEXT")

    db.commit()
    db.close()

with app.app_context():
    init_db()

# ── Helpers ─────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentification requise.'}), 401
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

def user_has_access(course_id):
    if course_id in FREE_COURSE_IDS:
        return True
    user = get_current_user()
    if user and user['has_paid']:
        return True
    return False

def user_has_paid():
    user = get_current_user()
    return user is not None and user['has_paid']

def maxelpay_request(endpoint, method='GET', data=None):
    try:
        url = f'{MAXELPAY_BASE}{endpoint}'
        headers = {
            'X-API-KEY': MAXELPAY_API_KEY,
            'Content-Type': 'application/json',
            'User-Agent': 'GoForAI/1.0'
        }
        body = None
        if data:
            body = json.dumps(data).encode('utf-8')
        log.debug(f"[MaxelPay] {method} {url} body={data}")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            result = json.loads(raw)
            log.info(f"[MaxelPay] {method} {endpoint} => {resp.status} keys={list(result.keys())}")
            log.debug(f"[MaxelPay] Response: {raw[:500]}")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ''
        log.error(f"[MaxelPay] HTTPError {e.code} on {method} {endpoint}: {body[:300]}")
        return json.loads(body) if body.startswith('{') else None
    except Exception as e:
        log.error(f"[MaxelPay] Erreur API: {e}")
        return None

# ── Routes ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Page principale avec les cours et leçons."""
    user = get_current_user()
    paid = user_has_paid()
    user_phone_masked = None
    if user:
        phone = user['phone']
        user_phone_masked = phone[-4:].rjust(len(phone), '*')
    return render_template('index.html',
                         courses=COURSES,
                         lessons=LESSONS,
                         now=datetime.now(),
                         user=user,
                         has_paid=paid,
                         free_course_ids=FREE_COURSE_IDS,
                         payment_price_usd=PAYMENT_PRICE_USD,
                         payment_price_display='${:.2f}'.format(PAYMENT_PRICE_USD),
                         user_phone_masked=user_phone_masked)

@app.route('/api/courses')
def api_courses():
    return jsonify({
        'success': True,
        'data': sorted(COURSES, key=lambda x: x['sort_order']),
        'count': len(COURSES)
    })

@app.route('/api/lessons')
def api_lessons():
    course_id = request.args.get('course_id')
    lessons = LESSONS
    if course_id:
        lessons = [l for l in lessons if l['course_id'] == course_id]
    return jsonify({
        'success': True,
        'data': sorted(lessons, key=lambda x: (x['course_id'], x['sort_order'])),
        'count': len(lessons)
    })

@app.route('/api/stats')
def api_stats():
    total_videos = len([l for l in LESSONS if l['lesson_type'] == 'video'])
    total_pdfs = len([l for l in LESSONS if l['lesson_type'] == 'pdf'])
    return jsonify({
        'success': True,
        'data': {
            'total_courses': len(COURSES),
            'total_lessons': len(LESSONS),
            'total_videos': total_videos,
            'total_pdfs': total_pdfs,
            'total_duration': '8h+ de formation'
        }
    })

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()

    if not name or not email or not message:
        return jsonify({'success': False, 'error': 'Tous les champs sont requis.'}), 400

    print(f"[CONTACT] De: {name} <{email}> - {message[:100]}...")
    return jsonify({
        'success': True,
        'message': 'Votre message a bien été envoyé !'
    })

@app.route('/downloads/<path:filename>')
def serve_downloads(filename):
    download_dir = os.path.join(os.path.dirname(__file__), 'downloads_goforai')
    filepath = os.path.join(download_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'Fichier non trouvé'}), 404

    lesson = next((l for l in LESSONS if l.get('local_pdf') == 'downloads_goforai/' + filename), None)
    if lesson and not user_has_access(lesson['course_id']):
        return jsonify({'success': False, 'error': 'Accès payant requis. Veuillez débloquer.'}), 403

    return send_from_directory(download_dir, filename)

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('static/images', filename)

# ── Routes Auth ────────────────────────────────────────────────────────────

@app.route('/api/auth/status')
def api_auth_status():
    user = get_current_user()
    if not user:
        return jsonify({'success': True, 'data': {'logged_in': False}})
    return jsonify({
        'success': True,
        'data': {
            'logged_in': True,
            'phone': user['phone'][-4:].rjust(len(user['phone']), '*'),
            'has_paid': bool(user['has_paid']),
            'payment_status': user['payment_status'],
            'free_course_ids': list(FREE_COURSE_IDS)
        }
    })

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()

    if not phone or len(phone) < 8:
        return jsonify({'success': False, 'error': 'Numéro de téléphone invalide (min 8 chiffres).'}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()

    if user:
        # Utilisateur existant : connexion directe
        user_id = user['id']
    else:
        # Nouvel utilisateur
        cur = db.execute(
            "INSERT INTO users (phone, is_verified) VALUES (?, 1)",
            (phone,)
        )
        user_id = cur.lastrowid
        db.commit()

        # Re-fetch pour récupérer le has_paid
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    session.permanent = True
    session['user_id'] = user_id
    session['phone'] = phone

    return jsonify({
        'success': True,
        'message': 'Connecté avec succès.',
        'data': {
            'phone': phone[-4:].rjust(len(phone), '*'),
            'has_paid': bool(user['has_paid']),
            'payment_status': user['payment_status']
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Déconnecté.'})

# ── Routes Paiement ────────────────────────────────────────────────────────

@app.route('/api/payment/create', methods=['POST'])
@login_required
def api_payment_create():
    if not MAXELPAY_API_KEY:
        log.error("[Payment] Cle API MaxelPay non configuree")
        return jsonify({
            'success': False,
            'error': 'Cle API MaxelPay non configuree.'
        }), 500

    user = get_current_user()
    if user['has_paid']:
        log.warning(f"[Payment] User {user['id']} a deja paye")
        return jsonify({'success': False, 'error': 'Vous avez deja paye.'}), 400

    base = PUBLIC_URL or SITE_BASE_URL

    order_id = f'goforai_{user["id"]}_{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}'

    callback_url = f'{base}/api/webhook/maxelpay'
    success_url = f'{base}/?payment=success'
    cancel_url = f'{base}/?payment=cancel'

    payload = {
        'orderId': order_id,
        'amount': PAYMENT_PRICE_USD,
        'currency': 'USD',
        'description': f'GoForAI - Deblocage complet {PAYMENT_PRICE_USD} USD',
        'successUrl': success_url,
        'cancelUrl': cancel_url,
        'callbackUrl': callback_url
    }

    log.info(f"[Payment] Creation session pour user {user['id']} orderId={order_id} amount={PAYMENT_PRICE_USD}")
    log.debug(f"[Payment] Payload: {payload}")

    result = maxelpay_request('/payments/sessions', method='POST', data=payload)
    if not result:
        log.error("[Payment] Reponse API nulle")
        return jsonify({
            'success': False,
            'error': 'Erreur creation paiement. Reessayez.'
        }), 500

    if result.get('success') is False:
        api_errors = result.get('errors', [])
        msg = result.get('message', 'Erreur API.')
        if api_errors:
            msg = api_errors[0].get('msg', msg) if isinstance(api_errors[0], dict) else str(api_errors[0])
        log.error(f"[Payment] API erreur: {msg} | full={result}")
        return jsonify({
            'success': False,
            'error': msg
        }), 500

    result_data = result.get('data', result)
    session_id = result_data.get('sessionId') or result_data.get('session_id') or result_data.get('id', '')
    checkout_url = result_data.get('paymentUrl') or result_data.get('checkoutUrl') or result_data.get('checkout_url') or result_data.get('url', '')

    log.info(f"[Payment] Session created: sessionId={session_id} checkoutUrl={checkout_url}")

    if not checkout_url:
        log.error(f"[Payment] Pas de checkout_url dans la reponse: {result}")
        return jsonify({
            'success': False,
            'error': 'Erreur creation paiement. Reessayez.'
        }), 500

    db = get_db()
    db.execute(
        "INSERT INTO payments (user_id, session_id, checkout_url, order_id, amount_usd, status) VALUES (?, ?, ?, ?, ?, 'pending')",
        (user['id'], session_id, checkout_url, order_id, PAYMENT_PRICE_USD)
    )
    db.execute(
        "UPDATE users SET payment_session_id = ?, payment_status = 'pending' WHERE id = ?",
        (session_id, user['id'])
    )
    db.commit()

    log.info(f"[Payment] Payment record created for user {user['id']}, sessionId={session_id}")
    return jsonify({
        'success': True,
        'data': {
            'checkout_url': checkout_url,
            'session_id': session_id,
            'value_usd': PAYMENT_PRICE_USD
        }
    })

@app.route('/api/payment/status')
@login_required
def api_payment_status():
    user = get_current_user()
    db = get_db()

    if user['has_paid']:
        log.debug(f"[Payment/Status] User {user['id']} already paid")
        return jsonify({'success': True, 'data': {'paid': True, 'status': 'confirmed'}})

    payment = db.execute(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user['id'],)
    ).fetchone()

    if not payment:
        log.debug(f"[Payment/Status] User {user['id']} no payment record")
        return jsonify({'success': True, 'data': {'paid': False, 'status': 'none'}})

    if payment['status'] == 'confirmed':
        return jsonify({'success': True, 'data': {'paid': True, 'status': 'confirmed'}})

    if payment['session_id']:
        log.info(f"[Payment/Status] Checking MaxelPay session {payment['session_id']}")
        status_result = maxelpay_request(f'/payments/sessions/{payment["session_id"]}/status')
        if status_result:
            status_val = status_result.get('status', '').lower()
            log.info(f"[Payment/Status] Session {payment['session_id']} => status={status_val}")
            if status_val in ('paid', 'completed', 'confirmed'):
                db.execute(
                    "UPDATE payments SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), payment['id'])
                )
                db.execute(
                    "UPDATE users SET has_paid = 1, payment_status = 'confirmed' WHERE id = ?",
                    (user['id'],)
                )
                db.commit()
                log.info(f"[Payment/Status] User {user['id']} confirmed via polling")
                return jsonify({'success': True, 'data': {'paid': True, 'status': 'confirmed'}})
            elif status_val in ('expired', 'failed', 'cancelled'):
                return jsonify({
                    'success': True,
                    'data': {'paid': False, 'status': status_val}
                })
        else:
            log.warning(f"[Payment/Status] Could not fetch status for session {payment['session_id']}")

    return jsonify({
        'success': True,
        'data': {
            'paid': False,
            'status': 'pending',
            'checkout_url': payment['checkout_url'],
            'amount_usd': payment['amount_usd']
        }
    })

# ── Webhook MaxelPay ─────────────────────────────────────────────────────────

@app.route('/api/webhook/maxelpay', methods=['POST'])
def api_webhook_maxelpay():
    payload = request.get_data()
    signature = request.headers.get('X-MaxelPay-Signature', '')

    log.info(f"[Webhook] Received payload, signature={signature[:20] if signature else 'none'}...")

    if MAXELPAY_SECRET_KEY and signature:
        expected = hmac.new(
            MAXELPAY_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            log.warning("[Webhook] Signature invalide")
            return jsonify({'error': 'Invalid signature'}), 401

    data = request.get_json(force=True) if request.is_json else {}
    event = data.get('event', '')
    payment_data = data.get('data', {})
    order_id = payment_data.get('orderId', '')
    session_id = payment_data.get('sessionId', '')
    status = payment_data.get('status', '').lower()

    log.info(f"[Webhook] event={event} orderId={order_id} sessionId={session_id} status={status}")
    log.debug(f"[Webhook] Full payload: {data}")

    db = get_db()

    if event == 'payment.completed' or status in ('paid', 'completed', 'confirmed'):
        payment = db.execute(
            "SELECT * FROM payments WHERE session_id = ? OR order_id = ? ORDER BY id DESC LIMIT 1",
            (session_id, order_id)
        ).fetchone()

        if payment and payment['status'] != 'confirmed':
            db.execute(
                "UPDATE payments SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), payment['id'])
            )
            db.execute(
                "UPDATE users SET has_paid = 1, payment_status = 'confirmed' WHERE id = ?",
                (payment['user_id'],)
            )
            db.commit()
            log.info(f"[Webhook] Paiement confirme pour user_id={payment['user_id']}")

    elif event in ('payment.expired', 'payment.failed') or status in ('expired', 'failed', 'cancelled'):
        payment = db.execute(
            "SELECT * FROM payments WHERE session_id = ? OR order_id = ? ORDER BY id DESC LIMIT 1",
            (session_id, order_id)
        ).fetchone()
        if payment and payment['status'] == 'pending':
            db.execute(
                "UPDATE payments SET status = ? WHERE id = ?",
                (status, payment['id'])
            )
            db.execute(
                "UPDATE users SET payment_status = ? WHERE id = ?",
                (status, payment['user_id'])
            )
            db.commit()
            log.info(f"[Webhook] Paiement {status} pour user_id={payment['user_id']}")

    return jsonify({'received': True})

# ── API Accès ──────────────────────────────────────────────────────────────

@app.route('/api/access')
def api_access():
    paid = user_has_paid()
    accessible = {}
    for course in COURSES:
        cid = course['id']
        accessible[cid] = (cid in FREE_COURSE_IDS) or paid
    return jsonify({
        'success': True,
        'data': {
            'logged_in': 'user_id' in session,
            'has_paid': paid,
            'free_course_ids': list(FREE_COURSE_IDS),
            'accessible_courses': accessible
        }
    })

# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    print(f"\n{'='*60}")
    print(f"  GoForAI — Serveur démarré")
    print(f"  URL : http://localhost:{port}")
    print(f"  Prix deblocage : ${PAYMENT_PRICE_USD}")
    print(f"  Crypto : MaxelPay")
    print(f"  API Key : {'configuree' if MAXELPAY_API_KEY else 'NON CONFIGUREE'}")
    print(f"  Public URL : {PUBLIC_URL or SITE_BASE_URL}")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
