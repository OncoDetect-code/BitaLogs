"""Prueba aislada de conexion a Supabase. No toca Streamlit."""
import tomllib, sys
from pathlib import Path

secrets = Path(".streamlit/secrets.toml")
if not secrets.exists():
    print("ERROR: no encuentro .streamlit/secrets.toml. Estas en la carpeta correcta?")
    sys.exit(1)

data = tomllib.loads(secrets.read_text(encoding="utf-8"))
url = data.get("DB_URL", "")
if not url:
    print("ERROR: no hay DB_URL en el archivo.")
    sys.exit(1)

# Diagnostico del formato SIN mostrar la password completa
try:
    esquema, resto = url.split("://", 1)
    userpass, hostpart = resto.split("@", 1)
    user, pwd = userpass.split(":", 1)
except ValueError:
    print("ERROR: la URL no tiene el formato esperado. Revisa comillas y estructura.")
    print("   Longitud total leida:", len(url))
    sys.exit(1)

print("=== DIAGNOSTICO DE LA URL ===")
print("Esquema      :", esquema, "(debe ser postgresql+psycopg)")
print("Usuario      :", user, "(debe terminar en .lmdepijtjppdzmiteeul)")
print("Host         :", hostpart)
print("Password len :", len(pwd), "caracteres")
print("Password 1er :", repr(pwd[0]) if pwd else "(vacia)")
print("Password ult :", repr(pwd[-1]) if pwd else "(vacia)")
sospechosos = [c for c in pwd if c in '@#:/?%& []' or ord(c) < 33]
print("Caracteres sospechosos en password:", sospechosos if sospechosos else "ninguno")
print()

print("=== INTENTO DE CONEXION ===")
try:
    from sqlalchemy import create_engine, text
    eng = create_engine(url, pool_pre_ping=True)
    with eng.connect() as c:
        r = c.execute(text("SELECT 1")).scalar()
    print("EXITO! Conexion OK, SELECT 1 =", r)
except Exception as e:
    print("FALLO la conexion:")
    print(type(e).__name__, ":", str(e)[:300])
