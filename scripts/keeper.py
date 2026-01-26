import time
import random
import requests

# --- CONFIGURACIÓN ---

BASE_URL = "https://balconesdeparaguana1.vercel.app"

# Lista de tus endpoints públicos que consultan la BD (Home, Listado, etc.)
# Hazlo de manera que realice peticiones a la bd
URLS = [
    f"{BASE_URL}/finanzas/condominio/",
    f"{BASE_URL}/finanzas/basura/",
    f"{BASE_URL}/finanzas/condominio/?torre={random.randint(1, 24)}&mes={random.randint(0, 12)}&anio={random.randint(2024, 2028)}",
    f"{BASE_URL}/finanzas/basura/?torre={random.randint(1, 24)}&mes={random.randint(0, 12)}&anio={random.randint(2024, 2028)}",
    f"{BASE_URL}/general/basura/estado-solvencia/",
    f"{BASE_URL}/general/basura/estado-solvencia/?mes={random.randint(1, 12)}&anio={random.randint(2024, 2028)}&monto_minimo={random.randint(0, 99999)}",
    f"{BASE_URL}/beneficios/clap/",
    f"{BASE_URL}/beneficios/gas/",
]

# Agentes de usuario creíbles (Chrome, Firefox, Safari en diferentes OS)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Referers para simular tráfico orgánico (Google, Bing, Directo)
REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "",  # Tráfico directo
]


def simulate_activity():
    # 1. Lógica de Frecuencia (3 a 14 veces por semana)
    # El Cron corre cada 8 horas = 21 ejecuciones posibles a la semana.
    # Queremos ~8 ejecuciones reales promedio (media entre 3 y 14).
    # Probabilidad de éxito necesaria: 8 / 21 ≈ 38%

    if random.random() > 0.40:
        print("🎲 Omitiendo ejecución esta vez para mantener aleatoriedad.")
        return

    # 2. Retraso Humano (Human Delay)
    # Espera entre 10 segundos y 15 minutos antes de lanzar la petición
    # Esto evita que los logs del servidor muestren peticiones siempre al minuto :00
    delay = random.randint(10, 900)
    print(f"⏳ Esperando {delay} segundos para simular comportamiento humano...")
    time.sleep(delay)

    # 3. Selección de Objetivo
    target_url = random.choice(URLS)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": random.choice(REFERERS),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }

    try:
        print(f"🚀 Enviando petición a: {target_url}")
        response = requests.get(target_url, headers=headers, timeout=10)
        print(f"✅ Estado: {response.status_code}")

        # OPCIONAL: Si quieres ser ultra paranoico, haz una segunda petición a otro link
        # simulando que el usuario hizo clic en algo más.
        if random.choice([True, False]):
            time.sleep(random.randint(5, 20))
            second_url = random.choice(URLS)
            requests.get(second_url, headers=headers, timeout=10)
            print(f"✅ (Extra) Segunda página visitada: {second_url}")

    except Exception as e:
        print(f"❌ Error en la petición: {e}")
        # No fallamos el script (exit 1) para no alertar a GitHub Actions,
        # ya que puede ser un error temporal de red.


if __name__ == "__main__":
    simulate_activity()
