import os
import sqlite3
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
DB_PATH = os.environ.get("DATABASE_PATH", "star_logistics.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")

STATUSES = [
    "Order Received",
    "Processing",
    "Shipped",
    "In Transit",
    "Out for Delivery",
    "Delivered",
    "Delivery Exception",
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_number TEXT UNIQUE NOT NULL,
                recipient TEXT NOT NULL,
                origin TEXT,
                destination TEXT,
                courier TEXT DEFAULT 'Star Logistics',
                status TEXT NOT NULL,
                location TEXT,
                updated_at TEXT NOT NULL,
                notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_number TEXT NOT NULL,
                status TEXT NOT NULL,
                location TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        if count == 0:
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            conn.execute("""
                INSERT INTO shipments
                (tracking_number, recipient, origin, destination, courier, status, location, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("STAR123456789", "Sample Customer", "Abuja, Nigeria",
                  "Lagos, Nigeria", "Star Logistics", "In Transit",
                  "Lokoja, Nigeria", now, "This is a demonstration shipment."))
            conn.execute("""
                INSERT INTO events (tracking_number, status, location, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("STAR123456789", "In Transit", "Lokoja, Nigeria",
                  "Package is moving towards its destination.", now))

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

def get_shipment(tracking_number):
    with db() as conn:
        shipment = conn.execute(
            "SELECT * FROM shipments WHERE tracking_number = ?",
            (tracking_number.upper().strip(),)
        ).fetchone()
        if not shipment:
            return None, []
        events = conn.execute(
            "SELECT * FROM events WHERE tracking_number = ? ORDER BY id DESC",
            (tracking_number.upper().strip(),)
        ).fetchall()
    return shipment, events

def fedex_track(tracking_number):
    """
    Optional live FedEx integration.
    This is intentionally a clear integration placeholder. Add credentials from
    the official FedEx Developer Portal and implement the current FedEx API
    request/response format before enabling it in production.
    """
    api_url = os.environ.get("FEDEX_TRACK_API_URL")
    access_token = os.environ.get("FEDEX_ACCESS_TOKEN")
    if not api_url or not access_token:
        return None, "FedEx API is not configured yet."
    try:
        response = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {access_token}",
                     "Content-Type": "application/json"},
            json={"trackingNumber": tracking_number},
            timeout=15,
        )
        response.raise_for_status()
        # Map the official API response to this site's shipment format here.
        return response.json(), None
    except requests.RequestException:
        return None, "FedEx could not be reached. Please try again later."

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        tracking_number = request.form.get("tracking_number", "").strip().upper()
        if not tracking_number:
            flash("Please enter a tracking number.", "error")
            return redirect(url_for("home"))
        return redirect(url_for("track", tracking_number=tracking_number))
    return render_template("index.html")

@app.route("/track/<tracking_number>")
def track(tracking_number):
    shipment, events = get_shipment(tracking_number)
    if not shipment:
        return render_template("not_found.html", tracking_number=tracking_number), 404

    live_message = None
    if shipment["courier"].lower() == "fedex":
        _, live_message = fedex_track(tracking_number)

    return render_template("track.html", shipment=shipment, events=events,
                           live_message=live_message)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect password.", "error")
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@login_required
def admin_dashboard():
    with db() as conn:
        shipments = conn.execute("SELECT * FROM shipments ORDER BY id DESC").fetchall()
    return render_template("admin.html", shipments=shipments, statuses=STATUSES)

@app.route("/admin/create", methods=["POST"])
@login_required
def create_shipment():
    tracking = request.form.get("tracking_number", "").strip().upper()
    recipient = request.form.get("recipient", "").strip()
    status = request.form.get("status", "Order Received")
    if not tracking or not recipient or status not in STATUSES:
        flash("Enter a tracking number, recipient and valid status.", "error")
        return redirect(url_for("admin_dashboard"))
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    try:
        with db() as conn:
            conn.execute("""
                INSERT INTO shipments
                (tracking_number, recipient, origin, destination, courier, status, location, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tracking, recipient, request.form.get("origin", ""),
                  request.form.get("destination", ""),
                  request.form.get("courier", "Star Logistics"), status,
                  request.form.get("location", ""), now,
                  request.form.get("notes", "")))
            conn.execute("""
                INSERT INTO events (tracking_number, status, location, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (tracking, status, request.form.get("location", ""),
                  "Shipment created.", now))
        flash(f"Shipment {tracking} created.", "success")
    except sqlite3.IntegrityError:
        flash("That tracking number already exists.", "error")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/update", methods=["POST"])
@login_required
def update_shipment():
    tracking = request.form.get("tracking_number", "").strip().upper()
    status = request.form.get("status", "")
    location = request.form.get("location", "").strip()
    details = request.form.get("details", "").strip()
    if status not in STATUSES:
        flash("Choose a valid status.", "error")
        return redirect(url_for("admin_dashboard"))
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    with db() as conn:
        exists = conn.execute(
            "SELECT id FROM shipments WHERE tracking_number = ?", (tracking,)
        ).fetchone()
        if not exists:
            flash("Shipment not found.", "error")
            return redirect(url_for("admin_dashboard"))
        conn.execute("""
            UPDATE shipments SET status = ?, location = ?, updated_at = ?
            WHERE tracking_number = ?
        """, (status, location, now, tracking))
        conn.execute("""
            INSERT INTO events (tracking_number, status, location, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tracking, status, location, details or status, now))
    flash(f"Shipment {tracking} updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html"), 500

init_db()

if __name__ == "__main__":
    app.run(debug=True)
