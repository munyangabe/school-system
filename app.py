#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "sms.db"
STATIC_DIR = ROOT / "static"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                parent_phone TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                score REAL NOT NULL,
                term TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status TEXT CHECK(status IN ('present','late','absent')) NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                term TEXT NOT NULL,
                paid_on TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            );
            """
        )
        conn.commit()


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, code=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str):
        if not path.exists() or not path.is_file():
            self.send_error(404, "Not Found")
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _parse_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/static/styles.css":
            return self._send_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
        if path == "/static/app.js":
            return self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")

        if path == "/api/students":
            with get_conn() as conn:
                rows = conn.execute(
                    "SELECT id, name, class_name, parent_phone, created_at FROM students ORDER BY id DESC"
                ).fetchall()
            return self._send_json([dict(r) for r in rows])

        if path == "/api/dashboard":
            with get_conn() as conn:
                students = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
                avg_grade = conn.execute("SELECT ROUND(AVG(score), 2) AS a FROM grades").fetchone()["a"]
                absent = conn.execute("SELECT COUNT(*) AS c FROM attendance WHERE status='absent'").fetchone()["c"]
                paid = conn.execute("SELECT ROUND(COALESCE(SUM(amount), 0), 2) AS s FROM payments").fetchone()["s"]
            return self._send_json(
                {
                    "students": students,
                    "average_grade": avg_grade if avg_grade is not None else 0,
                    "absent_count": absent,
                    "paid_total": paid,
                }
            )

        if path.startswith("/api/reports/student/"):
            student_id = path.rsplit("/", 1)[-1]
            if not student_id.isdigit():
                return self._send_json({"error": "Invalid student id"}, 400)
            sid = int(student_id)
            with get_conn() as conn:
                student = conn.execute(
                    "SELECT id, name, class_name, parent_phone FROM students WHERE id=?", (sid,)
                ).fetchone()
                if not student:
                    return self._send_json({"error": "Student not found"}, 404)

                grades = [
                    dict(r)
                    for r in conn.execute(
                        "SELECT subject, score, term, created_at FROM grades WHERE student_id=? ORDER BY id DESC", (sid,)
                    ).fetchall()
                ]
                attendance = [
                    dict(r)
                    for r in conn.execute(
                        "SELECT date, status FROM attendance WHERE student_id=? ORDER BY date DESC", (sid,)
                    ).fetchall()
                ]
                payments = [
                    dict(r)
                    for r in conn.execute(
                        "SELECT amount, term, paid_on FROM payments WHERE student_id=? ORDER BY paid_on DESC", (sid,)
                    ).fetchall()
                ]

            avg = round(sum(g["score"] for g in grades) / len(grades), 2) if grades else 0
            absent_count = len([a for a in attendance if a["status"] == "absent"])
            return self._send_json(
                {
                    "student": dict(student),
                    "summary": {
                        "average_grade": avg,
                        "attendance_entries": len(attendance),
                        "absent_count": absent_count,
                        "payments_total": round(sum(p["amount"] for p in payments), 2),
                    },
                    "grades": grades,
                    "attendance": attendance,
                    "payments": payments,
                }
            )

        self.send_error(404, "Not Found")

    def do_POST(self):
        path = urlparse(self.path).path
        payload = self._parse_body()
        if payload is None:
            return self._send_json({"error": "Invalid JSON"}, 400)

        if path == "/api/students":
            name = str(payload.get("name", "")).strip()
            class_name = str(payload.get("class_name", "")).strip()
            parent_phone = str(payload.get("parent_phone", "")).strip()
            if not name or not class_name:
                return self._send_json({"error": "name and class_name are required"}, 400)
            with get_conn() as conn:
                cur = conn.execute(
                    "INSERT INTO students(name, class_name, parent_phone, created_at) VALUES(?,?,?,?)",
                    (name, class_name, parent_phone, now_iso()),
                )
                conn.commit()
                new_id = cur.lastrowid
            return self._send_json({"id": new_id, "message": "Student added"}, 201)

        if path == "/api/grades":
            required = ["student_id", "subject", "score", "term"]
            if any(k not in payload for k in required):
                return self._send_json({"error": "student_id, subject, score, term are required"}, 400)
            try:
                sid = int(payload["student_id"])
                score = float(payload["score"])
            except (TypeError, ValueError):
                return self._send_json({"error": "student_id and score must be numeric"}, 400)

            with get_conn() as conn:
                student = conn.execute("SELECT id FROM students WHERE id=?", (sid,)).fetchone()
                if not student:
                    return self._send_json({"error": "Student not found"}, 404)
                conn.execute(
                    "INSERT INTO grades(student_id, subject, score, term, created_at) VALUES(?,?,?,?,?)",
                    (sid, str(payload["subject"]).strip(), score, str(payload["term"]).strip(), now_iso()),
                )
                conn.commit()
            return self._send_json({"message": "Grade recorded"}, 201)

        if path == "/api/attendance":
            required = ["student_id", "date", "status"]
            if any(k not in payload for k in required):
                return self._send_json({"error": "student_id, date, status are required"}, 400)
            try:
                sid = int(payload["student_id"])
            except (TypeError, ValueError):
                return self._send_json({"error": "student_id must be numeric"}, 400)
            status = str(payload["status"]).strip()
            if status not in {"present", "late", "absent"}:
                return self._send_json({"error": "status must be present|late|absent"}, 400)
            with get_conn() as conn:
                student = conn.execute("SELECT id FROM students WHERE id=?", (sid,)).fetchone()
                if not student:
                    return self._send_json({"error": "Student not found"}, 404)
                conn.execute(
                    "INSERT INTO attendance(student_id, date, status, created_at) VALUES(?,?,?,?)",
                    (sid, str(payload["date"]).strip(), status, now_iso()),
                )
                conn.commit()
            return self._send_json({"message": "Attendance recorded"}, 201)

        if path == "/api/payments":
            required = ["student_id", "amount", "term", "paid_on"]
            if any(k not in payload for k in required):
                return self._send_json({"error": "student_id, amount, term, paid_on are required"}, 400)
            try:
                sid = int(payload["student_id"])
                amount = float(payload["amount"])
            except (TypeError, ValueError):
                return self._send_json({"error": "student_id and amount must be numeric"}, 400)
            with get_conn() as conn:
                student = conn.execute("SELECT id FROM students WHERE id=?", (sid,)).fetchone()
                if not student:
                    return self._send_json({"error": "Student not found"}, 404)
                conn.execute(
                    "INSERT INTO payments(student_id, amount, term, paid_on, created_at) VALUES(?,?,?,?,?)",
                    (sid, amount, str(payload["term"]).strip(), str(payload["paid_on"]).strip(), now_iso()),
                )
                conn.commit()
            return self._send_json({"message": "Payment recorded"}, 201)

        self.send_error(404, "Not Found")


def run(host="0.0.0.0", port=8000):
    init_db()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"SMS running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    host = os.getenv("SMS_HOST", "0.0.0.0")
    port = int(os.getenv("SMS_PORT", "8000"))
    run(host=host, port=port)
