import os
import sqlite3
import string
import random
from urllib.parse import urlparse
from flask import Flask, request, g, render_template, jsonify, abort
import validators

# ---------- Config ----------
PORT = int(os.environ.get("PORT", 8080))
BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{PORT}")
DB_PATH = os.environ.get("DB_PATH", "/tmp/safelink.db")
COUNTDOWN_SECONDS = 5

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ---------- Database ----------
def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE,
        target TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        clicks INTEGER DEFAULT 0
    );
    """)
    db.commit()

@app.before_request
def ensure_db():
    # create table if not exists (safe + idempotent)
    init_db()

@app.teardown_appcontext
def close_connection(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

# ---------- Helpers ----------
ALPHABET = string.ascii_letters + string.digits

def random_slug(n=6):
    return ''.join(random.choice(ALPHABET) for _ in range(n))

def is_safe_url(u):
    if not u or not validators.url(u):
        return False
    p = urlparse(u)
    return p.scheme in ("http", "https")

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html", base_url=BASE_URL)

@app.route("/api/create", methods=["POST"])
def api_create():
    data = request.get_json() or {}
    target = (data.get("target") or "").strip()
    custom = (data.get("custom") or "").strip()

    if not is_safe_url(target):
        return jsonify({"ok": False, "error": "Invalid or unsafe URL"}), 400

    db = get_db()
    cur = db.cursor()

    if custom:
        if not custom.isalnum() or len(custom) < 3:
            return jsonify({"ok": False, "error": "Custom slug must be alphanumeric"}), 400
        cur.execute("SELECT id FROM links WHERE slug = ?", (custom,))
        if cur.fetchone():
            return jsonify({"ok": False, "error": "Slug already used"}), 409
        slug = custom
    else:
        while True:
            slug = random_slug(6)
            cur.execute("SELECT id FROM links WHERE slug = ?", (slug,))
            if not cur.fetchone():
                break

    cur.execute("INSERT INTO links (slug, target) VALUES (?, ?)", (slug, target))
    db.commit()
    short = f"{BASE_URL}/s/{slug}"
    return jsonify({"ok": True, "short": short, "slug": slug, "target": target})

@app.route("/s/<slug>")
def serve_slug(slug):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM links WHERE slug = ?", (slug,))
    row = cur.fetchone()
    if not row:
        abort(404)
    return render_template("redirect.html", slug=slug, target=row["target"], countdown=COUNTDOWN_SECONDS)

@app.route("/go/<slug>", methods=["POST"])
def go_slug(slug):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM links WHERE slug = ?", (slug,))
    row = cur.fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Not found"}), 404
    cur.execute("UPDATE links SET clicks = clicks + 1 WHERE slug = ?", (slug,))
    db.commit()
    return jsonify({"ok": True, "redirect": row["target"]})

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
