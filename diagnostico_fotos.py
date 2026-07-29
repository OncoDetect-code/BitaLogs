"""Diagnostica cuántas imágenes hay realmente en la base de Supabase."""
import tomllib
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = tomllib.loads(Path(".streamlit/secrets.toml").read_text(encoding="utf-8"))["DB_URL"]
eng = create_engine(DB_URL, pool_pre_ping=True, connect_args={"prepare_threshold": None})

with eng.connect() as c:
    # ¿Existen las columnas de imagen?
    cols = c.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='atenciones' AND column_name LIKE 'img%'
        ORDER BY column_name""")).fetchall()
    print("Columnas de imagen en la tabla:", [r[0] for r in cols])

    # ¿Cuántos registros tienen alguna imagen no vacía?
    for i in (1, 2, 3, 4):
        n = c.execute(text(f"""
            SELECT COUNT(*) FROM atenciones
            WHERE img{i} IS NOT NULL AND img{i} <> ''""")).scalar()
        print(f"  Registros con img{i} llena: {n}")

    # Mostrar los ids que SÍ tienen al menos una foto
    filas = c.execute(text("""
        SELECT id, equipo, semana, dia,
               (img1 IS NOT NULL AND img1<>'') AS f1,
               (img2 IS NOT NULL AND img2<>'') AS f2,
               (img3 IS NOT NULL AND img3<>'') AS f3,
               (img4 IS NOT NULL AND img4<>'') AS f4,
               LENGTH(COALESCE(img1,'')) AS len1
        FROM atenciones
        WHERE (img1 IS NOT NULL AND img1<>'')
           OR (img2 IS NOT NULL AND img2<>'')
           OR (img3 IS NOT NULL AND img3<>'')
           OR (img4 IS NOT NULL AND img4<>'')
        ORDER BY id""")).fetchall()
    print(f"\nRegistros con al menos 1 foto: {len(filas)}")
    for f in filas:
        print(f"  #{f[0]} {f[1]} (S{f[2]}D{f[3]}) fotos=[{f[4]},{f[5]},{f[6]},{f[7]}] len_img1={f[8]}")
