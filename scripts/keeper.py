import os
import time
import random
import requests

# --- CONFIGURACIÓN ---
BASE_URL = "https://balconesdeparaguana1.vercel.app"

# Capturamos la URL principal de despertar desde GitHub Actions
WAKE_UP_URL = os.environ.get('TARGET_URL', f"{BASE_URL}/login/")

# Lista de tus endpoints públicos que consultan la BD
URLS = [
    f"{BASE_URL}/finanzas/condominio/",
    f"{BASE_URL}/finanzas/basura/",
    # Corregido: El mes debe ser de 1 a 12 para evitar errores 500 en Django
    f"{BASE_URL}/finanzas/condominio/?torre={random.randint(1, 24)}&mes={random.randint(1, 12)}&anio={random.randint(2024, 2028)}",
    f"{BASE_URL}/finanzas/basura/?torre={random.randint(1, 24)}&mes={random.randint(1, 12)}&anio={random.randint(2024, 2028)}",
    f"{BASE_URL}/general/basura/estado-solvencia/",
    f"{BASE_URL}/beneficios/clap/",
    f"{BASE_URL}/beneficios/gas/",
]

# Agentes de usuario creíbles (Chrome, Firefox, Safari en diferentes OS)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "",  # Tráfico directo
]


def simulate_activity():
    # 1. Lógica de Frecuencia
    # Reducimos la probabilidad de omisión para asegurar que Supabase no se apague
    if random.random() > 0.70:
        print("🎲 Omitiendo ejecución esta vez para mantener aleatoriedad en los logs.")
        return

    # 2. Retraso Humano (Human Delay)
    # Reducido un poco para no agotar los minutos gratuitos de GitHub Actions
    delay = random.randint(5, 45)
    print(f"⏳ Esperando {delay} segundos para simular comportamiento humano...")
    time.sleep(delay)

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": random.choice(REFERERS),
        "Accept-Language": "es-VE,es;q=0.9,en;q=0.8",
    }

    try:
        # 3. PING DE DESPERTAR (Garantiza que la BD se encienda sin importar la ruta)
        print(f"🔔 Enviando PING de Despertar a: {WAKE_UP_URL}")
        # Usamos un timeout alto (30s) porque Supabase tarda unos segundos en despertar
        response_wake = requests.get(WAKE_UP_URL, headers=headers, timeout=30)
        print(f"✅ Estado Despertar: {response_wake.status_code}")

        # 4. SIMULACIÓN DE NAVEGACIÓN ADICIONAL
        if random.choice([True, False]):
            time.sleep(random.randint(5, 15))
            second_url = random.choice(URLS)
            print(f"🚀 (Extra) Simulando navegación hacia: {second_url}")
            response_extra = requests.get(second_url, headers=headers, timeout=15)
            print(f"✅ Estado Extra: {response_extra.status_code}")

    except requests.exceptions.Timeout:
        print("⚠️ Tiempo de espera agotado. Probablemente Supabase estaba dormido y está despertando ahora.")
    except Exception as e:
        print(f"❌ Error en la petición: {e}")

if __name__ == "__main__":
    simulate_activity()