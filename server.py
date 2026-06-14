"""
FDM Pricing App - Flask + Supabase Backend
Local:  python server.py  → http://localhost:5000
Cloud:  deployed on Render, uses DATABASE_URL env var from Supabase
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__, static_folder=".")
CORS(app)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    return jsonify({"error": str(e)}), 500

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    url = os.environ.get("DATABASE_URL")  # read fresh each time
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    if "sslmode" not in url:
        url += "?sslmode=require"
    return psycopg.connect(url, row_factory=dict_row)


def init_db():
    """Create the quotes table if it doesn't exist."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id        SERIAL PRIMARY KEY,
                    date      TEXT NOT NULL,
                    product   TEXT NOT NULL,
                    plain_cost  TEXT,
                    primer_cost TEXT,
                    paint_cost  TEXT,
                    grams     NUMERIC,
                    hours     NUMERIC,
                    primer_val NUMERIC,
                    paint_val  NUMERIC,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
        conn.commit()


def row_to_dict(row):
    return {
        "id":         row["id"],
        "date":       row["date"],
        "product":    row["product"],
        "plainCost":  row["plain_cost"],
        "primerCost": row["primer_cost"],
        "paintCost":  row["paint_cost"],
        "grams":      float(row["grams"] or 0),
        "hours":      float(row["hours"] or 0),
        "primerVal":  float(row["primer_val"] or 0),
        "paintVal":   float(row["paint_val"] or 0),
    }


# --- Routes ---

@app.route("/")
def index():
    return send_from_directory(".", "PricingApp.html")


@app.route("/api/quotes", methods=["GET"])
def get_quotes():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM quotes ORDER BY created_at DESC;")
            rows = cur.fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/quotes", methods=["POST"])
def add_quote():
    q = request.get_json()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quotes (date, product, plain_cost, primer_cost, paint_cost, grams, hours, primer_val, paint_val)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                q.get("date"), q.get("product"),
                q.get("plainCost"), q.get("primerCost"), q.get("paintCost"),
                q.get("grams", 0), q.get("hours", 0),
                q.get("primerVal", 0), q.get("paintVal", 0)
            ))
            new_id = cur.fetchone()["id"]
        conn.commit()
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/quotes/<int:quote_id>", methods=["PUT"])
def update_quote(quote_id):
    q = request.get_json()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE quotes SET
                    date        = %s,
                    product     = %s,
                    plain_cost  = %s,
                    primer_cost = %s,
                    paint_cost  = %s,
                    grams       = %s,
                    hours       = %s,
                    primer_val  = %s,
                    paint_val   = %s
                WHERE id = %s;
            """, (
                q.get("date"), q.get("product"),
                q.get("plainCost"), q.get("primerCost"), q.get("paintCost"),
                q.get("grams", 0), q.get("hours", 0),
                q.get("primerVal", 0), q.get("paintVal", 0),
                quote_id
            ))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/quotes/<int:quote_id>", methods=["DELETE"])
def delete_quote(quote_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM quotes WHERE id = %s;", (quote_id,))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/quotes/bulk", methods=["PUT"])
def bulk_update():
    """Replace all quotes — used by bulk edit save."""
    quotes = request.get_json()
    with get_conn() as conn:
        with conn.cursor() as cur:
            for q in quotes:
                if q.get("id"):
                    cur.execute("""
                        UPDATE quotes SET
                            date        = %s,
                            product     = %s,
                            plain_cost  = %s,
                            primer_cost = %s,
                            paint_cost  = %s,
                            grams       = %s,
                            hours       = %s,
                            primer_val  = %s,
                            paint_val   = %s
                        WHERE id = %s;
                    """, (
                        q.get("date"), q.get("product"),
                        q.get("plainCost"), q.get("primerCost"), q.get("paintCost"),
                        q.get("grams", 0), q.get("hours", 0),
                        q.get("primerVal", 0), q.get("paintVal", 0),
                        q["id"]
                    ))
        conn.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable not set.")
        exit(1)
    init_db()
    print("=" * 50)
    print("  Kevin's 3D Lab - FDM Pricing App")
    print("  Open http://localhost:5000 in your browser")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    app.run(port=5000, debug=False)
else:
    # Running under gunicorn on Render — init DB on startup
    if os.environ.get("DATABASE_URL"):
        init_db()
