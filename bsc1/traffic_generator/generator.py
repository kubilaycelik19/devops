import os
import random
import time
import httpx

# İstekler doğrudan Nginx'e (api_gateway) gidecek
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://nginx:80")

# Üretilen siparişlerin bu kadarı, sistemde olmayan bir kullanıcıyla hata simülasyonu yapar
ORDER_ERROR_RATE = 0.10

PRODUCTS = [
    "MacBook Pro M3 Max",
    "Dell UltraSharp 34 Monitor",
    "Keychron Q1 Mechanical Keyboard",
    "Logitech MX Master 3S",
    "Sony WH-1000XM5 Kulaklık",
    "CalDigit TS4 Thunderbolt Dock",
]

GHOST_PRODUCTS = [
    "Quantum Core Processor",
    "Dark Matter GPU",
    "Neural Interface Rig",
    "Ghost Server Blade",
    "Holographic Array Module",
    "Sub-Zero Liquid Cooler",
]


def ghost_user_id(existing_ids):
    """Veritabanında olmayan 4 basamaklı bir kullanıcı kimliği üretir."""
    for _ in range(1000):
        candidate = random.randint(1000, 9999)
        if candidate not in existing_ids:
            return candidate
    return max(existing_ids or {0}) + 10000


def fetch_users(client):
    response = client.get("/api/users")
    response.raise_for_status()
    users = response.json()
    if not isinstance(users, list):
        return []
    return [user for user in users if isinstance(user, dict) and "id" in user]


def wait_for_users(client):
    for attempt in range(30):
        try:
            users = fetch_users(client)
            if users:
                print(f"[+] Kullanıcı havuzu hazır: {len(users)} kayıt")
                return users
        except Exception as exc:
            print(f"[-] Kullanıcılar okunamadı ({attempt + 1}/30): {exc}")
        time.sleep(2)
    print("[-] Kullanıcı havuzu boş. Siparişler hazır olana kadar denenecek.")
    return []


def create_order(client, users):
    existing_ids = {user["id"] for user in users}

    if random.random() < ORDER_ERROR_RATE:
        payload = {
            "user_id": ghost_user_id(existing_ids),
            "product_name": random.choice(GHOST_PRODUCTS),
            "quantity": 1,
        }
        response = client.post("/api/orders", json=payload)
        print(
            f"[!] Hata simülasyonu user_id={payload['user_id']} "
            f"urun={payload['product_name']} -> HTTP {response.status_code}"
        )
        return

    user = random.choice(users)
    payload = {
        "user_id": user["id"],
        "product_name": random.choice(PRODUCTS),
        "quantity": random.randint(1, 3),
    }
    response = client.post("/api/orders", json=payload)
    print(
        f"[+] Sipariş user_id={payload['user_id']} "
        f"urun={payload['product_name']} -> HTTP {response.status_code}"
    )


def run():
    print(f"[*] Traffic Generator başlatıldı. Hedef: {GATEWAY_URL}")
    time.sleep(5)

    users = []
    with httpx.Client(base_url=GATEWAY_URL, timeout=5.0) as client:
        users = wait_for_users(client)

    while True:
        try:
            with httpx.Client(base_url=GATEWAY_URL, timeout=5.0) as client:
                refreshed = fetch_users(client)
                if refreshed:
                    users = refreshed

                roll = random.random()

                # %55 sipariş üret. Bunların %10'u dinamik hata simülasyonudur.
                if roll < 0.55:
                    if users:
                        create_order(client, users)
                    else:
                        print("[-] Sipariş atlandı: henüz kullanıcı yok.")

                # %30 sipariş listeleme
                elif roll < 0.85:
                    client.get("/api/orders")

                # %15 kullanıcı listeleme
                else:
                    client.get("/api/users")

        except Exception as exc:
            print(f"[-] Trafik döngüsü hatası: {exc}")

        time.sleep(random.uniform(1.0, 3.0))


if __name__ == "__main__":
    run()
