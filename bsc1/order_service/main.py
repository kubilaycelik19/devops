import os
import time
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Order Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

DB_HOST = os.getenv("DB_HOST", "order_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secretpassword")
DB_NAME = os.getenv("DB_NAME", "orders_db")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:5001")

class OrderCreate(BaseModel):
    user_id: int
    product_name: str
    quantity: int = 1

def get_db_connection():
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
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                product_name VARCHAR(150) NOT NULL,
                quantity INT NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    conn.close()

@app.get("/")
def read_root():
    return {"service": "order_service", "status": "healthy"}

@app.get("/orders")
def list_orders():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, user_id, product_name, quantity, created_at FROM orders ORDER BY id ASC;")
        orders = cur.fetchall()
    conn.close()
    return orders

@app.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate):
    # 1. ADIM: User Service'e HTTP isteği atıp kullanıcı var mı teyit ediyoruz
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{USER_SERVICE_URL}/users/{order.user_id}", timeout=5.0)
        except httpx.RequestError:
            raise HTTPException(
                status_code=503, 
                detail="User Service'e ulaşılamadı. Doğrulama yapılamıyor."
            )

    if response.status_code == 404:
        raise HTTPException(
            status_code=400, 
            detail=f"Sipariş başarısız: ID'si {order.user_id} olan bir kullanıcı bulunamadı!"
        )

    user_info = response.json()

    # 2. ADIM: Kullanıcı geçerliyse siparişi kendi veritabanımıza yazıyoruz
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO orders (user_id, product_name, quantity) VALUES (%s, %s, %s) RETURNING id, user_id, product_name, quantity, created_at;",
            (order.user_id, order.product_name, order.quantity)
        )
        new_order = cur.fetchone()
        conn.commit()
    conn.close()

    return {
        "message": "Sipariş başarıyla oluşturuldu.",
        "order": new_order,
        "ordered_by": user_info["username"]
    }