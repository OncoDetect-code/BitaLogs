"""
Mantiene despiertas las apps de Streamlit Community Cloud (BitaLogs y
ServiDox) abriéndolas con un navegador real.

Por qué un navegador y no un simple ping HTTP:
Streamlit Cloud responde 200 con una cáscara HTML estática aunque la app
esté dormida; el ping "OK" NO la despierta. La app solo arranca cuando un
navegador ejecuta el JavaScript. Por eso se usa Selenium (Chrome headless):
carga la página de verdad y, si aparece el botón "Yes, get this app back
up!", lo clickea.

Se ejecuta desde GitHub Actions cada pocas horas (ver wake.yml).
"""

import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# URLs de las apps a mantener despiertas.
APPS = [
    "https://bitalogs-024.streamlit.app/",
    "https://servidox-024.streamlit.app/",
]

# Texto del botón de despertar (Streamlit lo muestra cuando la app duerme).
TEXTOS_BOTON = (
    "get this app back up",
    "Yes, get this app back up!",
)


def _driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
    return webdriver.Chrome(options=opts)


def _buscar_boton_despertar(driver):
    """Devuelve el botón de despertar si está presente, o None."""
    # El botón de Streamlit es un <button>; se busca por su texto.
    for boton in driver.find_elements(By.TAG_NAME, "button"):
        try:
            txt = (boton.text or "").lower()
        except Exception:
            continue
        if any(t.lower() in txt for t in TEXTOS_BOTON):
            return boton
    return None


def despertar(driver, url):
    """Abre una app y la despierta si está dormida. Devuelve un estado."""
    driver.get(url)
    # Dar tiempo a que cargue el shell y el JS decida si mostrar el botón.
    time.sleep(8)

    boton = _buscar_boton_despertar(driver)
    if boton is None:
        return "OK (ya despierta)"

    # Está dormida: clickear el botón y esperar a que arranque.
    try:
        driver.execute_script("arguments[0].click();", boton)
    except Exception:
        boton.click()

    # Esperar hasta ~90 s a que la app termine de levantar (el botón
    # desaparece cuando arranca).
    try:
        WebDriverWait(driver, 90).until(
            lambda d: _buscar_boton_despertar(d) is None)
        return "DESPERTADA"
    except TimeoutException:
        return "clic hecho, pero sigue cargando (revisar manualmente)"


def main():
    errores = 0
    driver = _driver()
    try:
        for url in APPS:
            try:
                estado = despertar(driver, url)
                print(f"[{estado}] {url}", flush=True)
            except Exception as e:
                errores += 1
                print(f"[ERROR] {url} -> {e}", flush=True)
    finally:
        driver.quit()

    # Salir con error solo si TODAS fallaron (para que el workflow avise).
    if errores == len(APPS):
        sys.exit(1)


if __name__ == "__main__":
    main()
