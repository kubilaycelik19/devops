import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import psycopg2

PORT = int(os.environ.get("PORT", 5001))
DB_HOST = os.environ.get("DB_HOST", "db")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "secretpassword")
DB_NAME = os.environ.get("DB_NAME", "users_db")

def get_db_connection():
    # Postgres hazır olana kadar birkaç saniye deneme döngüsü
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME
            )
            return conn
        except psycopg2.OperationalError:
            time.sleep(1)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Tabloyu oluştur
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL
        );
    """)
    # Tablo boşsa başlangıç verisi ekle
    cur.execute("SELECT COUNT(*) FROM users;")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (name) VALUES ('Ahmet'), ('Mehmet'), ('Ayşe');")
    conn.commit()
    cur.close()
    conn.close()

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM users;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        users_list = [{"id": r[0], "name": r[1]} for r in rows]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            "servis": "User Servisi (PostgreSQL Baglantili)",
            "kullanicilar": users_list
        }
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

if __name__ == '__main__':
    init_db()
    server = HTTPServer(('0.0.0.0', PORT), SimpleHandler)
    print(f"User service {PORT} portunda ve PostgreSQL ile devrede...")
    server.serve_forever()