"""
ui_dashboard.py — Estilo visual y componentes del dashboard de BitaLogs.

Centraliza el CSS global (fondo claro, tarjetas), el hero con el logo de
BitaLogs, las tarjetas KPI con icono y el estilizado de las figuras de
Plotly, para que bitalogs.py solo llame funciones y no cargue con todo
el HTML/CSS.

Expone:
    inyectar_estilos()
    hero(subtitulo, dato_grande, dato_sub, periodo)
    fila_kpis(items)                # items: lista de dicts
    estilizar_figura(fig, tipo)     # aplica paleta y estilo del dashboard
    PALETA
"""

import os
import streamlit as st

# Paleta del dashboard (coincide con la maqueta aprobada).
PALETA = ["#2563EB", "#0EA5A5", "#7C3AED", "#F59E0B", "#EF4444",
          "#16A34A", "#0891B2", "#DB2777"]

_AZUL = "#2563EB"
_INK = "#1B2436"
_MUTED = "#6B7890"

# Logo de BitaLogs embebido (data-URI) para el hero.
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo_bitalogs_b64.txt")
try:
    with open(_LOGO_PATH, "r", encoding="utf-8") as _f:
        _LOGO = _f.read().strip()
except Exception:
    _LOGO = ""

# Iconos SVG de línea para las tarjetas KPI (sin emojis).
_ICONOS = {
    "equipos": ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M20 7h-9M14 17H5"/><circle cx="17" cy="17" r="3"/>'
                '<circle cx="7" cy="7" r="3"/></svg>'),
    "reloj": ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>'),
    "llave": ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 '
              '5.4-5.4l-2.7 2.7-2-2 2.7-2.7Z"/></svg>'),
    "lista": ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              '<rect x="4" y="3" width="16" height="18" rx="2"/>'
              '<path d="M8 7h8M8 11h8M8 15h5"/></svg>'),
    "tendencia": ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                  'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                  '<path d="M3 17l6-6 4 4 7-7"/><path d="M17 5h4v4"/></svg>'),
}

# Color de acento por índice de KPI (fondo del icono, texto del icono).
_KPI_ACENTOS = [
    ("#E0EBFF", "#2563EB"), ("#D7F5F2", "#0EA5A5"), ("#FEE2E2", "#EF4444"),
    ("#EDE4FF", "#7C3AED"), ("#FEF0CF", "#F59E0B"),
]


def inyectar_estilos():
    """CSS global: fondo claro, tipografía, tarjetas, sidebar, pestañas
    y controles, para que TODA la app comparta el mismo lenguaje visual."""
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=Inter:wght@400;500;600&display=swap');

      /* ---------- Base ---------- */
      .stApp { background:#EEF1F6; }
      .block-container { padding-top:1.4rem; max-width:1200px; }
      html, body, [class*="css"] { font-family:'Inter',sans-serif; }

      /* ---------- Pestañas de navegación (suave, tipo Excel) ---------- */
      .stTabs [data-baseweb="tab-list"]{
        gap:2px; background:#fff; padding:6px; border-radius:12px;
        box-shadow:0 2px 8px rgba(21,36,54,.05); border:1px solid #E6EAF2;
      }
      .stTabs [data-baseweb="tab"]{
        height:auto; padding:8px 15px; border-radius:8px; color:#6B7890;
        font-weight:600; font-size:14px; background:transparent;
        transition:background .15s, color .15s;
      }
      .stTabs [data-baseweb="tab"]:hover{ background:#F1F4FA; color:#1B2436; }
      /* Seleccionada: fondo azul MUY suave + texto azul + subrayado fino */
      .stTabs [aria-selected="true"]{
        background:#EAF1FF !important; color:#2563EB !important;
        box-shadow:inset 0 -2px 0 #2563EB;
      }
      .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{
        display:none !important;
      }

      /* ---------- Sidebar ---------- */
      section[data-testid="stSidebar"]{
        background:#fff !important; border-right:1px solid #E6EAF2;
      }
      section[data-testid="stSidebar"] > div{ background:#fff !important; }
      section[data-testid="stSidebar"] .block-container{ padding-top:1.5rem; }
      section[data-testid="stSidebar"] h1,
      section[data-testid="stSidebar"] h2,
      section[data-testid="stSidebar"] label,
      section[data-testid="stSidebar"] p{
        font-family:'Poppins',sans-serif; color:#1B2436;
      }

      /* ---------- Campos de entrada: fondo BLANCO ---------- */
      /* selectbox, multiselect, date, number, text: la caja donde se
         escribe/elige va en blanco sobre el fondo gris de la app. */
      div[data-baseweb="select"] > div,
      div[data-baseweb="input"] > div,
      .stTextInput input, .stNumberInput input, .stDateInput input,
      div[data-baseweb="base-input"]{
        background:#fff !important; border-radius:10px !important;
        border:1px solid #E1E7F2 !important;
      }
      .stMultiSelect div[data-baseweb="select"] > div{
        background:#fff !important;
      }
      /* Refuerzo: cualquier selectbox (dentro o fuera de un form) blanco */
      div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
      div[data-testid="stNumberInput"] div[data-baseweb="input"],
      div[data-testid="stDateInput"] div[data-baseweb="input"]{
        background:#fff !important; border:1px solid #E1E7F2 !important;
        border-radius:10px !important;
      }
      /* Selectbox cerrado: el value-container interno también en blanco */
      div[data-testid="stSelectbox"] [data-baseweb="select"] *,
      div[data-testid="stSelectbox"] [role="combobox"]{
        background-color:#fff !important;
      }
      div[data-testid="stSelectbox"] [data-baseweb="select"] > div{
        background:#fff !important;
      }
      /* Contenedores de formulario: fondo tarjeta blanca */
      div[data-testid="stForm"]{
        background:#fff; border:1px solid #E6EAF2; border-radius:16px;
        padding:16px 18px; box-shadow:0 4px 14px rgba(21,36,54,.05);
      }
      .stRadio [role="radiogroup"] label, .stCheckbox label{ font-size:14px; }

      /* ---------- Radios como VIÑETAS (segmentos), no puntos ---------- */
      /* Oculta el circulito y convierte cada opción en una pastilla
         clickeable; la seleccionada se pinta de azul suave. */
      div[role="radiogroup"]{
        display:flex; flex-wrap:wrap; gap:8px;
      }
      div[role="radiogroup"] > label{
        background:#fff; border:1px solid #E1E7F2; border-radius:10px;
        padding:8px 14px; margin:0; cursor:pointer; transition:.15s;
        display:flex; align-items:center;
      }
      div[role="radiogroup"] > label:hover{ border-color:#B9CBF0; background:#F6F9FF; }
      /* ocultar el círculo del radio */
      div[role="radiogroup"] > label > div:first-child{
        display:none !important;
      }
      /* opción seleccionada: la que contiene el input checked */
      div[role="radiogroup"] > label:has(input:checked){
        background:#EAF1FF; border-color:#2563EB; color:#2563EB; font-weight:600;
      }
      /* En el sidebar los segmentos van en columna para aprovechar el ancho */
      section[data-testid="stSidebar"] div[role="radiogroup"]{
        flex-direction:column;
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] > label{
        width:100%;
      }

      /* Botones */
      .stButton > button, .stDownloadButton > button{
        border-radius:11px; font-weight:600; border:1px solid #E6EAF2;
        background:#fff;
      }
      .stButton > button:hover, .stDownloadButton > button:hover{
        border-color:#2563EB; color:#2563EB;
      }
      .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"]{
        background:#2563EB; border-color:#2563EB; color:#fff;
      }
      .stDataFrame, .stDataEditor{ border-radius:12px; overflow:hidden; }

      /* ---------- Hero ---------- */
      .bl-hero{
        background:linear-gradient(120deg,#3B82F6,#60A5FA);
        border-radius:20px; padding:20px 26px; color:#fff; margin-bottom:18px;
        box-shadow:0 12px 30px rgba(59,130,246,.28);
      }
      .bl-hero-top{
        display:flex; align-items:center; justify-content:space-between;
        gap:20px; flex-wrap:wrap;
      }
      .bl-hero h1{ font-family:'Poppins',sans-serif; font-weight:800; font-size:24px;
                   letter-spacing:-.3px; margin:0; color:#fff; }
      .bl-hero .who p{ color:#DCE9FF; font-size:13px; margin:4px 0 0; }
      .bl-hero .headline{ text-align:right; }
      .bl-hero .headline .big{ font-family:'Poppins',sans-serif; font-weight:800;
                               font-size:38px; line-height:1; color:#fff; }
      .bl-hero .headline .big span{ font-size:19px; color:#DCE9FF; }
      .bl-hero .headline .cap{ color:#DCE9FF; font-size:12px; text-transform:uppercase;
                               letter-spacing:.6px; margin-top:4px; }
      .bl-progress{
        margin-top:16px; height:9px; border-radius:6px;
        background:rgba(255,255,255,.25); overflow:hidden;
      }
      .bl-progress-bar{
        height:100%; border-radius:6px; background:#fff;
        box-shadow:0 0 10px rgba(255,255,255,.5); transition:width .4s;
      }

      /* ---------- Tarjetas KPI ---------- */
      .bl-kpis{ display:grid; grid-template-columns:repeat(5,1fr); gap:14px; margin-bottom:6px; }
      .bl-kpi{ background:#fff; border-radius:16px; padding:16px;
               box-shadow:0 4px 14px rgba(21,36,54,.06); display:flex; gap:12px; align-items:center; }
      .bl-kpi .ico{ width:44px; height:44px; border-radius:12px; display:grid;
                    place-items:center; flex:none; }
      .bl-kpi .ico svg{ width:22px; height:22px; }
      .bl-kpi .val{ font-family:'Poppins',sans-serif; font-weight:800; font-size:25px;
                    line-height:1; color:#1B2436; }
      .bl-kpi .val small{ font-size:14px; color:#6B7890; font-weight:600; }
      .bl-kpi .lbl{ color:#6B7890; font-size:11.5px; font-weight:600; margin-top:3px; }

      /* ---------- Encabezado de sección ---------- */
      .bl-h3{ font-family:'Poppins',sans-serif; font-weight:700; font-size:15px;
              color:#1B2436; display:flex; align-items:center; gap:9px;
              margin:22px 0 12px; }
      .bl-h3 .bar{ width:5px; height:18px; border-radius:3px; display:inline-block; }

      /* ---------- Panel contenedor de gráfico ---------- */
      .bl-card-open{ background:#fff; border-radius:16px; padding:14px 16px 4px;
                     box-shadow:0 4px 14px rgba(21,36,54,.06); margin-bottom:14px; }

      @media(max-width:900px){ .bl-kpis{ grid-template-columns:repeat(2,1fr); } }
    </style>
    """, unsafe_allow_html=True)


def hero(subtitulo, horas_acum, horas_tot, periodo_txt, progreso):
    """
    Barra superior del dashboard: título, dato estrella (horas / total)
    y una barra de progreso que refleja el avance del filtro actual.
    """
    pct = max(0, min(progreso, 100))
    st.markdown(f"""
    <div class="bl-hero">
      <div class="bl-hero-top">
        <div class="who">
          <h1>Panel de Rendimiento</h1>
        </div>
        <div class="headline">
          <div class="big">{horas_acum} h <span>/ {horas_tot} h</span></div>
          <div class="cap">{periodo_txt} · {progreso:.0f}% completado</div>
        </div>
      </div>
      <div class="bl-progress">
        <div class="bl-progress-bar" style="width:{pct:.1f}%"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def fila_kpis(items):
    """
    Fila de tarjetas KPI. `items` es una lista de dicts:
        {"valor": "23", "unidad": "", "label": "Equipos atendidos",
         "icono": "equipos"}
    """
    tarjetas = ""
    for i, it in enumerate(items):
        bg, fg = _KPI_ACENTOS[i % len(_KPI_ACENTOS)]
        svg = _ICONOS.get(it.get("icono", "lista"), _ICONOS["lista"])
        unidad = it.get("unidad", "")
        u_html = f"<small>{unidad}</small>" if unidad else ""
        tarjetas += (
            f'<div class="bl-kpi">'
            f'<div class="ico" style="background:{bg};color:{fg}">{svg}</div>'
            f'<div><div class="val">{it["valor"]}{u_html}</div>'
            f'<div class="lbl">{it["label"]}</div></div></div>'
        )
    st.markdown(f'<div class="bl-kpis">{tarjetas}</div>', unsafe_allow_html=True)


def encabezado_seccion(titulo, color):
    """Título de sección con barrita de color, estilo tarjeta."""
    st.markdown(
        f'<div class="bl-h3"><span class="bar" style="background:{color}"></span>'
        f'{titulo}</div>', unsafe_allow_html=True)


def estilizar_figura(fig, altura=300, leyenda=True):
    """
    Aplica el look del dashboard a una figura de Plotly: fondo
    transparente, tipografía Inter, paleta viva, barras redondeadas,
    donas con contorno blanco y leyenda abajo.
    """
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=_INK, size=13),
        title={"text": ""},   # sin título interno (evita el "undefined")
        height=altura,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=leyenda,
        legend=dict(orientation="h", yanchor="top", y=-0.12,
                    xanchor="center", x=0.5, font=dict(size=12)),
    )
    fig.update_xaxes(gridcolor="#EEF1F6", zeroline=False,
                     title_font=dict(size=13), tickfont=dict(size=12))
    fig.update_yaxes(gridcolor="#EEF1F6", zeroline=False,
                     title_font=dict(size=13), tickfont=dict(size=12))
    for tr in fig.data:
        if tr.type == "bar":
            tr.marker.line = dict(width=0)
            try:
                tr.marker.cornerradius = 6
            except Exception:
                pass
        elif tr.type == "pie":
            tr.marker.line = dict(color="white", width=3)
            tr.textfont = dict(color="white", size=15, family="Poppins")
    return fig


def tarjeta_categoria_unica(categoria, color=None):
    """
    Tarjeta destacada para cuando un donut tendría una sola categoría
    (100%). En vez de un círculo completo sin información, muestra
    '100% <categoria>' de forma clara.
    """
    c = color or _AZUL
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:16px;padding:26px 24px;
                background:linear-gradient(120deg,#EAF1FF,#F5F8FF);
                border:1px solid #DCE7FB;border-radius:14px;min-height:200px">
      <div style="font-family:'Poppins',sans-serif;font-weight:800;
                  font-size:40px;color:{c};line-height:1">100%</div>
      <div style="font-size:16px;color:#1B2436;font-weight:600">{categoria}</div>
    </div>
    """, unsafe_allow_html=True)


def aplicar_paleta(fig):
    """Fuerza la paleta viva del dashboard sobre las trazas de la figura."""
    for i, tr in enumerate(fig.data):
        if tr.type == "pie":
            tr.marker.colors = PALETA
    return fig
