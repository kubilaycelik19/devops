import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="User Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

DB_HOST = os.getenv("DB_HOST", "user_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secretpassword")
DB_NAME = os.getenv("DB_NAME", "users_db")

class UserCreate(BaseModel):
    username: str
    email: EmailStr

# Panel açıldığında hazır görünen başlangıç kullanıcıları.
# Yeni kullanıcı ekleme akışı ayrıca duruyor; bu kayıtlar yalnızca yoksa yazılır.
SEED_USERS = [
    ("ayse_demir", "ayse.demir@shop.local"),
    ("mehmet_yilmaz", "mehmet.yilmaz@shop.local"),
    ("elif_kaya", "elif.kaya@shop.local"),
    ("can_ozkan", "can.ozkan@shop.local"),
    ("zeynep_arslan", "zeynep.arslan@shop.local"),
    ("burak_celik", "burak.celik@shop.local"),
    ("selin_aksoy", "selin.aksoy@shop.local"),
    ("emre_dogan", "emre.dogan@shop.local"),
    ("deniz_kurt", "deniz.kurt@shop.local"),
    ("ece_sahin", "ece.sahin@shop.local"),
]

def get_db_connection():
    # Veritabanı konteyneri yeni ayağa kalkarken bağlantıyı birkaç kez dener
    retries = 5
    while retries > 0:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME,
                cursor_factory=RealDictCursor
            )
            return conn
        except psycopg2.OperationalError:
            retries -= 1
            time.sleep(2)
    raise Exception("Veritabanına bağlanılamadı.")

@app.on_event("startup")
def startup_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.executemany(
            """
            INSERT INTO users (username, email)
            VALUES (%s, %s)
            ON CONFLICT (email) DO NOTHING;
            """,
            SEED_USERS,
        )
        conn.commit()
    conn.close()

@app.get("/")
def read_root():
    return {"service": "user_service", "status": "healthy"}

@app.get("/users")
def list_users():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, email, created_at FROM users ORDER BY id ASC;")
        users = cur.fetchall()
    conn.close()
    return users

@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id, username, email, created_at;",
                (user.username, user.email)
            )
            new_user = cur.fetchone()
            conn.commit()
            return new_user
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")
    finally:
        conn.close()

# Order Service'in kullanıcıyı teyit etmek için çağıracağı kritik endpoint
@app.get("/users/{user_id}")
def get_user_by_id(user_id: int):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, email FROM users WHERE id = %s;", (user_id,))
        user = cur.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
    return user