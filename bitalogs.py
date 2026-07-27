"""
BitaLogs — Dashboard de rendimiento de práctica profesional.
Ingeniería Biomédica · UNITEC · Autor: Luis

Basado en la estructura de ServiDox, adaptado para medir el rendimiento
del practicante: equipos atendidos, tipo de mantenimiento, área, horas
acumuladas, duración y promedio de atención, con carga de la bitácora
institucional (Matriz de impacto) y comentarios semanales de evaluadores.

CÓMO CORRERLO (terminal de Windows, una sola vez):
    pip install -r requirements.txt
    python -m streamlit run bitalogs.py

Se abre en el navegador (http://localhost:8501).

BASE DE DATOS (PostgreSQL / Supabase):
La conexión se lee de st.secrets["DB_URL"]. En local, crea el archivo
.streamlit/secrets.toml con:

    DB_URL = "postgresql+psycopg://postgres.xxxx:TU_PASSWORD@aws-0-...:6543/postgres"

En Streamlit Cloud, ese mismo valor se pega en Settings -> Secrets.
Las tablas se crean solas la primera vez (init_db).
"""

from datetime import date, datetime, time, timezone, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

import calendario as cal
from importar_bitacora import leer_matriz
from splash import mostrar_splash

# Honduras usa UTC-6 todo el año (sin horario de verano). En Streamlit
# Cloud el servidor corre en UTC, así que date.today() daría el día
# equivocado; hoy_hn() devuelve la fecha real de Honduras.
_TZ_HN = timezone(timedelta(hours=-6))


def hoy_hn() -> date:
    return datetime.now(_TZ_HN).date()

# ------------------------------------------------------------- Catálogos
AREAS = ["Hospitalización A", "Hospitalización B", "UCI A", "UCI B",
         "Sala Cuna", "UCIN", "Emergencia", "CEYE", "Laboratorio",
         "Quirófano 1", "Quirófano 2", "Quirófano 3", "Quirófano 4",
         "Área de mantenimiento", "Otra"]
TIPOS = ["Preventivo", "Correctivo", "Revisión y Diagnóstico",
         "Instalación", "Capacitación", "Otro"]
RESUELTO = ["Sí", "Parcial", "No"]

# Nombres bonitos de columnas (mostrar y exportar)
COLS = {
    "id": "ID", "fecha": "Fecha", "semana": "Semana", "dia": "Día",
    "hora_inicio": "Inicio", "hora_fin": "Fin", "duracion_min": "Duración (min)",
    "area": "Área", "equipo": "Equipo", "marca": "Marca", "modelo": "Modelo",
    "serie": "Serie No.", "tipo": "Tipo de mantenimiento",
    "problema": "Problema identificado", "solucion": "Solución sugerida",
    "resuelto": "¿Resuelto?", "impacto": "Impacto / beneficio",
    "observaciones": "Observaciones",
}
COLS_EDIT = ["fecha", "hora_inicio", "hora_fin", "area", "equipo", "marca",
             "modelo", "serie", "tipo", "problema", "solucion", "resuelto",
             "impacto", "observaciones"]


# ------------------------------------------------------------- DB layer
@st.cache_resource
def get_engine():
    """
    Motor SQLAlchemy hacia PostgreSQL (Supabase). La URL vive en
    st.secrets["DB_URL"]. pool_pre_ping evita conexiones muertas del
    pooler; se cachea para no reabrir el pool en cada rerun.
    """
    url = st.secrets["DB_URL"]
    return create_engine(url, pool_pre_ping=True)


def init_db():
    with get_engine().begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS atenciones (
                id SERIAL PRIMARY KEY,
                fecha TEXT NOT NULL,
                semana INTEGER, dia INTEGER,
                hora_inicio TEXT, hora_fin TEXT, duracion_min REAL,
                area TEXT, equipo TEXT, marca TEXT, modelo TEXT, serie TEXT,
                tipo TEXT, problema TEXT, solucion TEXT, resuelto TEXT,
                impacto TEXT, observaciones TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id SERIAL PRIMARY KEY,
                semana INTEGER NOT NULL,
                evaluador TEXT NOT NULL,
                comentario TEXT NOT NULL,
                fecha_registro TEXT NOT NULL
            )
        """))


def _dur_min(hi: str, hf: str):
    """Minutos entre hora_inicio y hora_fin (HH:MM). None si falta o inválido."""
    try:
        a = datetime.strptime(hi, "%H:%M")
        b = datetime.strptime(hf, "%H:%M")
        d = (b - a).total_seconds() / 60.0
        return round(d, 1) if d >= 0 else None
    except (ValueError, TypeError):
        return None


def insert_atencion(d: dict):
    d = dict(d)
    d["duracion_min"] = _dur_min(d.get("hora_inicio"), d.get("hora_fin"))
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO atenciones
            (fecha, semana, dia, hora_inicio, hora_fin, duracion_min, area,
             equipo, marca, modelo, serie, tipo, problema, solucion, resuelto,
             impacto, observaciones)
            VALUES (:fecha, :semana, :dia, :hora_inicio, :hora_fin,
                    :duracion_min, :area, :equipo, :marca, :modelo, :serie,
                    :tipo, :problema, :solucion, :resuelto, :impacto,
                    :observaciones)
        """), {
            "fecha": d["fecha"], "semana": d["semana"], "dia": d["dia"],
            "hora_inicio": d["hora_inicio"], "hora_fin": d["hora_fin"],
            "duracion_min": d["duracion_min"], "area": d["area"],
            "equipo": d["equipo"], "marca": d["marca"], "modelo": d["modelo"],
            "serie": d["serie"], "tipo": d["tipo"], "problema": d["problema"],
            "solucion": d["solucion"], "resuelto": d["resuelto"],
            "impacto": d["impacto"], "observaciones": d["observaciones"],
        })


def insert_muchas(regs: list[dict]):
    for r in regs:
        insert_atencion(r)


def load_atenciones() -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql_query(
            text("SELECT * FROM atenciones ORDER BY fecha DESC, id DESC"), conn)


def update_atenciones_from_df(df_edit: pd.DataFrame):
    """Reescribe la tabla con el contenido editado, recalculando semana/día/duración."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM atenciones"))
        for _, r in df_edit.iterrows():
            fecha = str(r.get("fecha", "")).strip()
            if not fecha:
                continue
            try:
                fd = datetime.strptime(fecha[:10], "%Y-%m-%d").date()
                sem = cal.semana_de_fecha(fd)
                dia = cal.dia_de_semana_num(fd)
            except ValueError:
                sem = r.get("semana"); dia = r.get("dia")
            hi = str(r.get("hora_inicio", "") or "")
            hf = str(r.get("hora_fin", "") or "")
            conn.execute(text("""
                INSERT INTO atenciones
                (fecha, semana, dia, hora_inicio, hora_fin, duracion_min, area,
                 equipo, marca, modelo, serie, tipo, problema, solucion,
                 resuelto, impacto, observaciones)
                VALUES (:fecha, :semana, :dia, :hora_inicio, :hora_fin,
                        :duracion_min, :area, :equipo, :marca, :modelo, :serie,
                        :tipo, :problema, :solucion, :resuelto, :impacto,
                        :observaciones)
            """), {
                "fecha": fecha[:10], "semana": sem, "dia": dia,
                "hora_inicio": hi, "hora_fin": hf, "duracion_min": _dur_min(hi, hf),
                "area": r.get("area"), "equipo": r.get("equipo"),
                "marca": r.get("marca"), "modelo": r.get("modelo"),
                "serie": r.get("serie"), "tipo": r.get("tipo"),
                "problema": r.get("problema"), "solucion": r.get("solucion"),
                "resuelto": r.get("resuelto"), "impacto": r.get("impacto"),
                "observaciones": r.get("observaciones"),
            })


def delete_atencion(id_: int):
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM atenciones WHERE id = :id"), {"id": id_})


# ---- Comentarios de evaluadores
def insert_comentario(semana: int, evaluador: str, comentario: str):
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO comentarios (semana, evaluador, comentario, fecha_registro)
            VALUES (:semana, :evaluador, :comentario, :fecha_registro)
        """), {
            "semana": semana, "evaluador": evaluador.strip(),
            "comentario": comentario.strip(),
            "fecha_registro": datetime.now().isoformat(timespec="minutes"),
        })


def load_comentarios() -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql_query(
            text("SELECT * FROM comentarios ORDER BY semana, fecha_registro"),
            conn)


def delete_comentario(id_: int):
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM comentarios WHERE id = :id"), {"id": id_})


# ------------------------------------------------------------- Excel export
def build_excel(df: pd.DataFrame, dcom: pd.DataFrame, path: Path):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.table import Table, TableStyleInfo
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def write_sheet(ws, data: pd.DataFrame, table_name: str):
        cols = list(data.columns)
        if not cols:
            return
        for j, col in enumerate(cols, 1):
            c = ws.cell(row=1, column=j, value=col)
            c.fill = header_fill; c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center",
                                    wrap_text=True)
            c.border = border
        for i, (_, row) in enumerate(data.iterrows(), start=2):
            for j, col in enumerate(cols, 1):
                c = ws.cell(row=i, column=j, value=row[col])
                c.border = border
                c.alignment = Alignment(vertical="top", wrap_text=True)
                if i % 2 == 0:
                    c.fill = PatternFill("solid", fgColor="F2F6FB")
        nrows = max(len(data) + 1, 2)
        ref = f"A1:{get_column_letter(len(cols))}{nrows}"
        if len(data) > 0:
            tbl = Table(displayName=table_name, ref=ref)
            tbl.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2", showRowStripes=True)
            ws.add_table(tbl)
        for j, col in enumerate(cols, 1):
            maxlen = max([len(str(col))] +
                         [len(str(v)) for v in data[col].astype(str).tolist()[:200]]
                         or [0])
            ws.column_dimensions[get_column_letter(j)].width = min(
                max(maxlen + 2, 10), 50)
        ws.freeze_panes = "A2"

    ws1 = wb.active
    ws1.title = "Atenciones"
    dshow = df.rename(columns=COLS)
    write_sheet(ws1, dshow, "TablaAtenciones")

    if not dcom.empty:
        ws2 = wb.create_sheet("Comentarios")
        cshow = dcom.rename(columns={
            "semana": "Semana", "evaluador": "Evaluador",
            "comentario": "Comentario", "fecha_registro": "Fecha"}).drop(
            columns=["id"], errors="ignore")
        write_sheet(ws2, cshow, "TablaComentarios")

    wb.save(path)


# =============================================================== UI
_ICONO = Path(__file__).parent / "bitalogs_icon.png"
st.set_page_config(page_title="BitaLogs · Práctica Profesional",
                   page_icon=str(_ICONO) if _ICONO.exists() else "📘",
                   layout="wide")

# CSS responsive: en desktop mantiene el ancho amplio; en celular fuerza
# que el contenido ocupe todo el ancho y quede centrado (sin el hueco a
# la derecha). Se usan selectores fuertes + !important porque Streamlit
# aplica sus propios anchos que de otro modo ganan.
st.markdown("""
<style>
    /* Desktop: contenido centrado con ancho máximo cómodo */
    .stMainBlockContainer, .block-container,
    section.main > div.block-container {
        max-width: 1400px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
    }

    /* Celular: ocupar TODO el ancho, sin hueco a la derecha */
    @media (max-width: 768px) {
        .stMainBlockContainer, .block-container,
        section.main > div.block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
        }
        /* El área principal completa al 100% */
        section.main, .stMain, [data-testid="stMain"] {
            width: 100% !important;
        }
        [data-testid="stAppViewContainer"] {
            width: 100% !important;
        }
        /* KPIs y título legibles en vertical */
        [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
        h1 { font-size: 1.6rem !important; }
        /* Tabs con scroll horizontal si no caben */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Ícono para "Agregar a pantalla de inicio" (Android/iPhone) ---
# Lee bitalogs_icon.png, lo incrusta como base64 y declara las etiquetas
# que Chrome/Safari usan para el ícono del acceso directo, más un manifest
# mínimo para que Android lo trate como app (nombre + logo BitaLogs).
def _inyectar_icono_movil():
    import base64
    import json
    import streamlit.components.v1 as _components
    if not _ICONO.exists():
        return
    b64 = base64.b64encode(_ICONO.read_bytes()).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"
    manifest = {
        "name": "BitaLogs",
        "short_name": "BitaLogs",
        "icons": [{"src": data_uri, "sizes": "192x192", "type": "image/png"},
                  {"src": data_uri, "sizes": "512x512", "type": "image/png"}],
        "display": "standalone",
        "background_color": "#FFFFFF",
        "theme_color": "#1F4E78",
    }
    manifest_uri = ("data:application/manifest+json;base64," +
                    base64.b64encode(json.dumps(manifest).encode()).decode())
    # Se inyecta en el <head> del documento padre (la app real, no el iframe).
    _components.html(f"""
    <script>
    (function() {{
      var doc = window.parent.document;
      function add(tag, attrs) {{
        var el = doc.createElement(tag);
        for (var k in attrs) el.setAttribute(k, attrs[k]);
        doc.head.appendChild(el);
      }}
      if (!doc.getElementById('bl-touch-icon')) {{
        var l1 = doc.createElement('link');
        l1.id = 'bl-touch-icon';
        l1.rel = 'apple-touch-icon';
        l1.href = '{data_uri}';
        doc.head.appendChild(l1);
        add('link', {{rel: 'icon', type: 'image/png', href: '{data_uri}'}});
        add('link', {{rel: 'manifest', href: '{manifest_uri}'}});
        add('meta', {{name: 'apple-mobile-web-app-title', content: 'BitaLogs'}});
        add('meta', {{name: 'apple-mobile-web-app-capable', content: 'yes'}});
      }}
    }})();
    </script>
    """, height=0, width=0)


_inyectar_icono_movil()

mostrar_splash(st)   # pantalla de carga (~3.5 s) al abrir o recargar
init_db()

_logo_col, _tit_col = st.columns([1, 9])
with _logo_col:
    if _ICONO.exists():
        st.image(str(_ICONO), width=64)
with _tit_col:
    st.title("BitaLogs")
    st.caption("Dashboard de Rendimiento · Práctica Profesional · "
               "Ingeniería Biomédica UNITEC")

# Botón para volver a ver la animación de carga cuando se quiera
with st.sidebar:
    if st.button("▶️ Ver animación de carga"):
        mostrar_splash(st, forzar=True)

tab_dash, tab_input, tab_carga, tab_datos, tab_coment = st.tabs(
    ["📊 Dashboard", "➕ Nueva atención", "📥 Cargar bitácora",
     "🗂️ Datos", "💬 Comentarios"])


# ---------------- helper: preparar df con tipos
def _prep(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["_fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df


# =============================================================== TAB: Nueva atención
with tab_input:
    st.subheader("Registrar una atención a equipo")

    with st.form("nueva", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_fecha = st.date_input("Fecha", value=hoy_hn())
            f_area = st.selectbox("Área", AREAS)
            f_tipo = st.selectbox("Tipo de mantenimiento", TIPOS)
        with c2:
            f_equipo = st.text_input("Equipo", placeholder="Lámpara cielítica")
            f_marca = st.text_input("Marca", placeholder="Dräger")
            f_modelo = st.text_input("Modelo", placeholder="Polaris 100")
        with c3:
            f_serie = st.text_input("Serie No.", placeholder="ABC123")
            f_ini = st.time_input("Hora de inicio", value=time(8, 0))
            f_fin = st.time_input("Hora de finalización", value=time(9, 0))

        f_prob = st.text_area("Problema identificado", height=80)
        f_sol = st.text_area("Solución sugerida / trabajo realizado", height=80)

        cc1, cc2 = st.columns([1, 3])
        with cc1:
            f_res = st.selectbox("¿Resuelto?", RESUELTO)
        f_imp = st.text_area("Impacto esperado o beneficio real", height=70)
        f_obs = st.text_area("Observaciones", height=70)

        enviado = st.form_submit_button("Guardar atención", type="primary")
        if enviado:
            if not f_equipo.strip():
                st.error("El campo 'Equipo' es obligatorio.")
            else:
                sem = cal.semana_de_fecha(f_fecha)
                dia = cal.dia_de_semana_num(f_fecha)
                if sem is None:
                    st.warning("⚠️ La fecha está fuera del período de práctica "
                               f"(20 jul – 25 sep 2026). Se guardará sin semana.")
                insert_atencion({
                    "fecha": f_fecha.isoformat(), "semana": sem, "dia": dia,
                    "hora_inicio": f_ini.strftime("%H:%M"),
                    "hora_fin": f_fin.strftime("%H:%M"),
                    "area": f_area, "equipo": f_equipo.strip(),
                    "marca": f_marca.strip(), "modelo": f_modelo.strip(),
                    "serie": f_serie.strip(), "tipo": f_tipo,
                    "problema": f_prob.strip(), "solucion": f_sol.strip(),
                    "resuelto": f_res, "impacto": f_imp.strip(),
                    "observaciones": f_obs.strip(),
                })
                etq = f"Semana {sem}" if sem else "sin semana"
                st.success(f"✅ Atención registrada ({etq}, "
                           f"{cal.etiqueta_dia(f_fecha)}).")


# =============================================================== TAB: Cargar bitácora
with tab_carga:
    st.subheader("Cargar bitácora institucional (Matriz de impacto)")
    st.caption("Sube tu Excel de la Matriz de impacto (UNITEC). BitaLogs "
               "detecta semana, día, equipo, problema, solución, ¿resuelto?, "
               "impacto y observaciones. Luego asignas fecha, horas, área y "
               "tipo antes de guardar.")

    up = st.file_uploader("Archivo .xlsx", type=["xlsx"], key="up_bitacora")
    if up is not None:
        try:
            regs, avisos = leer_matriz(up)
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")
            regs, avisos = [], []

        for a in avisos:
            st.warning(a)

        if regs:
            st.success(f"Se detectaron **{len(regs)}** registro(s).")
            prev = pd.DataFrame(regs)

            # Sugerir fecha a partir de semana+día del formato
            def _fecha_sug(row):
                if row["semana"] and row["dia"]:
                    try:
                        return cal.fecha_de_semana_dia(
                            int(row["semana"]), int(row["dia"])).isoformat()
                    except Exception:
                        return ""
                return ""

            prev.insert(0, "fecha", prev.apply(_fecha_sug, axis=1))
            prev["area"] = ""
            prev["tipo"] = "Correctivo"
            prev["hora_inicio"] = "08:00"
            prev["hora_fin"] = "09:00"
            prev["marca"] = ""; prev["modelo"] = ""; prev["serie"] = ""

            st.markdown("**Revisa y completa antes de guardar** "
                        "(fecha, área, tipo y horas):")
            edit = st.data_editor(
                prev, use_container_width=True, hide_index=True,
                num_rows="dynamic", key="editor_carga",
                column_config={
                    "area": st.column_config.SelectboxColumn("Área", options=AREAS),
                    "tipo": st.column_config.SelectboxColumn(
                        "Tipo", options=TIPOS),
                    "resuelto": st.column_config.SelectboxColumn(
                        "¿Resuelto?", options=RESUELTO),
                },
            )
            if st.button("💾 Guardar todos en BitaLogs", type="primary",
                         key="save_carga"):
                nuevos = []
                for _, r in edit.iterrows():
                    fecha = str(r.get("fecha", "")).strip()[:10]
                    if not str(r.get("equipo", "")).strip():
                        continue
                    try:
                        fd = datetime.strptime(fecha, "%Y-%m-%d").date()
                        sem = cal.semana_de_fecha(fd)
                        dia = cal.dia_de_semana_num(fd)
                    except ValueError:
                        sem = r.get("semana"); dia = r.get("dia")
                    nuevos.append({
                        "fecha": fecha or hoy_hn().isoformat(),
                        "semana": sem, "dia": dia,
                        "hora_inicio": str(r.get("hora_inicio", "") or ""),
                        "hora_fin": str(r.get("hora_fin", "") or ""),
                        "area": r.get("area", ""), "equipo": r.get("equipo", ""),
                        "marca": r.get("marca", ""), "modelo": r.get("modelo", ""),
                        "serie": r.get("serie", ""), "tipo": r.get("tipo", "Otro"),
                        "problema": r.get("problema", ""),
                        "solucion": r.get("solucion", ""),
                        "resuelto": r.get("resuelto", "No"),
                        "impacto": r.get("impacto", ""),
                        "observaciones": r.get("observaciones", ""),
                    })
                insert_muchas(nuevos)
                st.success(f"✅ {len(nuevos)} atención(es) guardada(s).")
                st.rerun()


# =============================================================== TAB: Dashboard
with tab_dash:
    df = _prep(load_atenciones())
    if df.empty:
        st.info("Aún no hay atenciones. Regístralas en '➕ Nueva atención' "
                "o carga tu bitácora en '📥 Cargar bitácora'.")
    else:
        with st.sidebar:
            st.header("Filtros")
            modo = st.radio("Ver por:", ["Toda la práctica", "Semana", "Día"],
                            key="modo_filtro")
            sem_sel = None
            dia_fecha = None
            if modo == "Semana":
                sem_sel = st.selectbox(
                    "Semana", cal.lista_semanas(),
                    format_func=lambda n: cal.etiqueta_semana(n))
            elif modo == "Día":
                sem_pick = st.selectbox(
                    "Semana", cal.lista_semanas(),
                    format_func=lambda n: f"Semana {n}", key="dia_sem")
                dnum = st.selectbox("Día", [1, 2, 3, 4, 5],
                                    format_func=lambda d: cal.etiqueta_dia(
                                        cal.fecha_de_semana_dia(sem_pick, d)))
                dia_fecha = cal.fecha_de_semana_dia(sem_pick, dnum)

            st.divider()
            fa = st.multiselect("Área", AREAS)
            ft = st.multiselect("Tipo", TIPOS)

        fdf = df.copy()
        if modo == "Semana" and sem_sel:
            fdf = fdf[fdf["semana"] == sem_sel]
        elif modo == "Día" and dia_fecha is not None:
            fdf = fdf[fdf["_fecha"].dt.date == dia_fecha]
        if fa:
            fdf = fdf[fdf["area"].isin(fa)]
        if ft:
            fdf = fdf[fdf["tipo"].isin(ft)]

        # ---- KPIs principales ----
        total = len(fdf)
        equipos_unicos = fdf["equipo"].str.strip().str.lower().nunique()
        dur_prom = fdf["duracion_min"].dropna().mean()
        # Días con actividad para "equipos por día"
        dias_activos = fdf["_fecha"].dt.date.nunique()
        eq_por_dia = (total / dias_activos) if dias_activos else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Equipos atendidos", total,
                  help="Total de atenciones según los filtros.")
        k2.metric("Equipos únicos", equipos_unicos)
        k3.metric("Prom. atención",
                  f"{dur_prom:.0f} min" if pd.notna(dur_prom) else "—",
                  help="Duración promedio por atención (inicio→fin).")
        k4.metric("Equipos por día",
                  f"{eq_por_dia:.1f}" if dias_activos else "—",
                  help="Promedio de equipos atendidos por día con actividad.")

        # ---- Horas acumuladas ----
        st.divider()
        st.subheader("⏱️ Horas de práctica")
        hoy = hoy_hn()
        ref = hoy
        if modo == "Semana" and sem_sel:
            ref = cal.viernes_de_semana(sem_sel)
        elif modo == "Día" and dia_fecha is not None:
            ref = dia_fecha
        horas_acum = cal.horas_hasta(ref)
        horas_tot = cal.horas_totales_practica()
        sem_actual = cal.semana_de_fecha(ref) or (
            cal.TOTAL_SEMANAS if ref >= cal.fin_practica() else 1)

        hk1, hk2, hk3 = st.columns(3)
        hk1.metric("Horas acumuladas", f"{horas_acum} h",
                   help=f"A la fecha de referencia ({cal._fmt(ref)}), "
                        "asumiendo 8 h/día L-V.")
        hk2.metric("Horas totales", f"{horas_tot} h")
        hk3.metric("Progreso", f"{horas_acum/horas_tot*100:.0f}%",
                   help=f"Semana {sem_actual} de {cal.TOTAL_SEMANAS}.")
        st.progress(min(horas_acum / horas_tot, 1.0))

        # Gráfico de horas acumuladas por semana
        hsem = pd.DataFrame(cal.horas_por_semana_acumuladas())
        fig_h = px.line(hsem, x="etiqueta", y="horas_acumuladas",
                        markers=True, title="Horas acumuladas por semana",
                        labels={"etiqueta": "", "horas_acumuladas": "Horas"})
        fig_h.update_traces(line_color="#1F4E78")
        st.plotly_chart(fig_h, use_container_width=True)

        # ---- Gráficos de rendimiento ----
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            por_area = (fdf.groupby("area").size()
                        .reindex(AREAS, fill_value=0)
                        .rename_axis("Área").reset_index(name="Equipos"))
            por_area = por_area[por_area["Equipos"] > 0]
            if por_area.empty:
                st.caption("📊 Equipos por área")
                st.info("Aún no hay atenciones con área asignada para mostrar.")
            else:
                fig = px.bar(por_area, x="Área", y="Equipos",
                             title="Equipos por área")
                fig.update_traces(marker_color="#1F4E78")
                fig.update_layout(xaxis_tickangle=-40)
                st.plotly_chart(fig, use_container_width=True)
        with g2:
            por_tipo = (fdf.groupby("tipo").size()
                        .rename_axis("Tipo").reset_index(name="Cantidad"))
            fig2 = px.pie(por_tipo, names="Tipo", values="Cantidad",
                          title="Tipo de mantenimiento", hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

        g3, g4 = st.columns(2)
        with g3:
            por_res = (fdf.groupby("resuelto").size()
                       .reindex(RESUELTO, fill_value=0)
                       .rename_axis("¿Resuelto?").reset_index(name="Cantidad"))
            fig3 = px.bar(por_res, x="¿Resuelto?", y="Cantidad",
                          title="Tasa de resolución",
                          color="¿Resuelto?",
                          color_discrete_map={"Sí": "#2E8B57",
                                              "Parcial": "#E8A317",
                                              "No": "#C0392B"})
            fig3.update_layout(showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)
        with g4:
            dd = fdf.dropna(subset=["duracion_min"])
            if not dd.empty:
                fig4 = px.histogram(dd, x="duracion_min", nbins=12,
                                    title="Distribución de duración (min)")
                fig4.update_traces(marker_color="#1F4E78")
                fig4.update_layout(showlegend=False,
                                   xaxis_title="Minutos", yaxis_title="Atenciones")
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.caption("Sin datos de duración para graficar.")

        # ---- Equipos por semana ----
        if modo == "Toda la práctica":
            st.divider()
            por_sem = (fdf.dropna(subset=["semana"]).groupby("semana").size()
                       .reindex(cal.lista_semanas(), fill_value=0)
                       .rename_axis("Semana").reset_index(name="Equipos"))
            por_sem["Semana"] = por_sem["Semana"].apply(lambda n: f"Sem {n}")
            fig5 = px.bar(por_sem, x="Semana", y="Equipos",
                          title="Equipos atendidos por semana", text="Equipos")
            fig5.update_traces(marker_color="#2E8B57", textposition="outside")
            st.plotly_chart(fig5, use_container_width=True)

        # ---- Exportar ----
        st.divider()
        st.subheader("⬇️ Exportar a Excel (lo filtrado)")
        if st.button("Generar Excel", key="exp_dash"):
            out = Path(__file__).parent / "BitaLogs_Export.xlsx"
            cols_exp = ["id"] + COLS_EDIT + ["semana", "dia", "duracion_min"]
            build_excel(fdf[[c for c in cols_exp if c in fdf.columns]],
                        load_comentarios(), out)
            with open(out, "rb") as fh:
                st.download_button(
                    "📥 Descargar Excel", data=fh.read(),
                    file_name="BitaLogs_Export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument."
                         "spreadsheetml.sheet", key="dl_dash")
            st.success("Excel generado.")


# =============================================================== TAB: Datos
with tab_datos:
    df = load_atenciones()
    st.subheader("Todas las atenciones")
    st.caption("Edita cualquier celda. Al guardar, se recalculan semana, día y "
               "duración a partir de la fecha y las horas. Usa la papelera para "
               "borrar filas.")

    if df.empty:
        st.info("Sin datos todavía.")
    else:
        show = df.rename(columns=COLS)
        edited = st.data_editor(
            show, use_container_width=True, hide_index=True, num_rows="dynamic",
            key="editor_datos",
            column_config={
                "Área": st.column_config.SelectboxColumn("Área", options=AREAS),
                "Tipo de mantenimiento": st.column_config.SelectboxColumn(
                    "Tipo de mantenimiento", options=TIPOS),
                "¿Resuelto?": st.column_config.SelectboxColumn(
                    "¿Resuelto?", options=RESUELTO),
                "Semana": st.column_config.NumberColumn("Semana", disabled=True),
                "Día": st.column_config.NumberColumn("Día", disabled=True),
                "Duración (min)": st.column_config.NumberColumn(
                    "Duración (min)", disabled=True),
            },
        )
        if st.button("💾 Guardar cambios", type="primary", key="save_datos"):
            inv = {v: k for k, v in COLS.items()}
            update_atenciones_from_df(edited.rename(columns=inv))
            st.success("Cambios guardados.")
            st.rerun()

        st.divider()
        st.subheader("🗑️ Eliminar una atención")
        etqs = [f"#{r['id']}  |  {r['fecha']}  |  {r['area']}  |  {r['equipo']}"
                for _, r in df.iterrows()]
        sel = st.selectbox("Atención a eliminar", ["— Selecciona —"] + etqs,
                           key="del_at")
        if sel != "— Selecciona —":
            id_del = int(sel.split("  |  ")[0].replace("#", "").strip())
            if st.checkbox(f"Confirmo eliminar la atención #{id_del}",
                           key="cf_del"):
                if st.button("Eliminar definitivamente", key="btn_del_at"):
                    delete_atencion(id_del)
                    st.success(f"Atención #{id_del} eliminada.")
                    st.rerun()


# =============================================================== TAB: Comentarios
with tab_coment:
    st.subheader("💬 Comentarios semanales de evaluadores")
    st.caption("Tus evaluadores pueden dejar un comentario por semana. "
               "Cada comentario queda firmado con su nombre y fecha.")

    with st.form("nuevo_coment", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            cs = st.selectbox("Semana", cal.lista_semanas(),
                              format_func=lambda n: cal.etiqueta_semana(n))
        with c2:
            ce = st.text_input("Nombre del evaluador *",
                               placeholder="Ing. Nombre Apellido")
        ct = st.text_area("Comentario *", height=100)
        ok = st.form_submit_button("Guardar comentario", type="primary")
        if ok:
            if not ce.strip() or not ct.strip():
                st.error("El nombre del evaluador y el comentario son obligatorios.")
            else:
                insert_comentario(cs, ce, ct)
                st.success(f"Comentario de {ce.strip()} guardado (Semana {cs}).")

    st.divider()
    dcom = load_comentarios()
    if dcom.empty:
        st.info("Aún no hay comentarios registrados.")
    else:
        for n in cal.lista_semanas():
            sub = dcom[dcom["semana"] == n]
            if sub.empty:
                continue
            st.markdown(f"### {cal.etiqueta_semana(n)}")
            for _, r in sub.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{r['evaluador']}** · _{r['fecha_registro']}_")
                    st.write(r["comentario"])
                    if st.button("🗑️ Eliminar", key=f"delc_{r['id']}"):
                        delete_comentario(int(r["id"]))
                        st.rerun()