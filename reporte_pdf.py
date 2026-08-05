"""
reporte_pdf.py — Reporte de indicadores de BitaLogs en PDF, generado a
partir de un HTML/CSS que replica el dashboard de la app (misma marca:
hero azul, tarjetas KPI, tarjetas de gráfico con sombra, paleta viva).

Los gráficos se rasterizan con Plotly/kaleido y se incrustan como
imágenes, para que el HTML no dependa de JavaScript y wkhtmltopdf
(motor WebKit) lo renderice fielmente.

Expone:
    construir_pdf(titulo, subtitulo, kpis, figuras) -> bytes
    construir_pdf_multi(titulo, bloques) -> bytes
"""

import os
import base64
from io import BytesIO

import pdfkit
from PIL import Image

# ---- Identidad ----
ESTUDIANTE = "Luis Velásquez"
CUENTA = "21941285"
CARRERA = "Ingeniería Biomédica"

# ---- Paleta de marca (idéntica al dashboard) ----
_PALETA = ["#2563EB", "#0EA5A5", "#7C3AED", "#F59E0B", "#EF4444",
           "#16A34A", "#0891B2", "#DB2777"]
_KPI_ACENTOS = ["#2563EB", "#0EA5A5", "#EF4444", "#7C3AED", "#F59E0B"]

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo_bitalogs_b64.txt")
try:
    with open(_LOGO_PATH, "r", encoding="utf-8") as _f:
        _LOGO = _f.read().strip()
except Exception:
    _LOGO = ""

# Configuración de wkhtmltopdf: busca el binario tanto en Linux
# (Streamlit Cloud: /usr/bin) como en Windows (Program Files). Así el
# mismo código funciona en local y en el deploy sin cambios.
_WK = None
_RUTAS_WK = (
    "/usr/bin/wkhtmltopdf",
    "/usr/local/bin/wkhtmltopdf",
    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
    r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
)
for _p in _RUTAS_WK:
    if os.path.exists(_p):
        try:
            _WK = pdfkit.configuration(wkhtmltopdf=_p)
            break
        except Exception:
            continue
# Último recurso: confiar en que esté en el PATH.
if _WK is None:
    try:
        _WK = pdfkit.configuration()
    except Exception:
        _WK = None


def _fig_img_b64(fig, w=820, h=560, tipo="bar"):
    """Rasteriza una figura Plotly a PNG y la devuelve como data-URI."""
    f = _estilizar(fig, tipo)
    png = f.to_image(format="png", width=w, height=h, scale=2)
    return "data:image/png;base64," + base64.b64encode(png).decode()


def _estilizar(fig, tipo):
    """Aplica el look del dashboard a la figura antes de rasterizar."""
    import copy
    f = copy.deepcopy(fig)
    barras_h = any(getattr(t, "orientation", None) == "h"
                   for t in f.data if t.type == "bar")
    tiene_pie = any(t.type == "pie" for t in f.data)

    f.update_layout(
        template="plotly_white",
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#1B2436", size=15, family="Arial"),
        title=None, margin=dict(l=45, r=25, t=15, b=55),
        showlegend=tiene_pie,
    )
    f.update_xaxes(gridcolor="#EEF1F6", zeroline=False, tickfont=dict(size=13),
                   title_font=dict(size=14))
    f.update_yaxes(gridcolor="#EEF1F6", zeroline=False, tickfont=dict(size=13),
                   title_font=dict(size=14))
    if tiene_pie:
        f.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.05,
                                    xanchor="center", x=0.5,
                                    font=dict(size=13)))
    for i, tr in enumerate(f.data):
        if tr.type == "pie":
            tr.marker.colors = ["#2563EB", "#F59E0B", "#16A34A", "#7C3AED",
                                "#EF4444", "#0EA5A5", "#DB2777", "#0891B2"]
            tr.textfont = dict(color="white", size=17, family="Arial Black")
            tr.textposition = "inside"
            tr.textinfo = "percent"
            tr.marker.line = dict(color="white", width=3)
        elif tr.type == "bar":
            if tr.marker.color is None or isinstance(tr.marker.color, str):
                tr.marker.color = _PALETA[i % len(_PALETA)]
            tr.textfont = dict(size=14, color="#1B2436")
            try:
                tr.marker.cornerradius = 6
            except Exception:
                pass

    if barras_h:
        cats = []
        for tr in f.data:
            if tr.type == "bar" and getattr(tr, "orientation", None) == "h":
                for yv in (tr.y or []):
                    if yv not in cats:
                        cats.append(yv)
        f.update_yaxes(showticklabels=False, title="")
        f.update_layout(bargap=0.62, margin=dict(l=45, r=30, t=30, b=55))
        for cat in cats:
            f.add_annotation(x=0, y=cat, text="<b>%s</b>" % cat,
                             showarrow=False, xanchor="left", yanchor="bottom",
                             yshift=15, xshift=-2,
                             font=dict(size=13, color="#1B2436"))
    return f


def _iconos_kpi():
    return [
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 7h-9M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/></svg>',
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.7 2.7-2-2 2.7-2.7Z"/></svg>',
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>',
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 7-7"/><path d="M17 5h4v4"/></svg>',
    ]


_ACENTOS_BG = ["#E0EBFF", "#D7F5F2", "#FEE2E2", "#EDE4FF", "#FEF0CF"]


def _bloque_html(subtitulo, kpis, figuras, progreso=None):
    """HTML de un bloque (una página) con hero, KPIs y grilla de gráficos."""
    logo = (f'<img src="{_LOGO}" alt="">' if _LOGO else "")
    iconos = _iconos_kpi()

    items = list(kpis.items())[:5]
    filas_kpi = [items[:3], items[3:]]
    kpi_html = ""
    idx = 0
    for fila in filas_kpi:
        if not fila:
            continue
        kpi_html += '<div class="kpi-row">'
        for k, v in fila:
            kpi_html += f"""
              <div class="kpi">
                <div class="ico" style="background:{_ACENTOS_BG[idx%5]};color:{_KPI_ACENTOS[idx%5]}">{iconos[idx%5]}</div>
                <div class="val">{v}</div><div class="lbl">{k}</div>
              </div>"""
            idx += 1
        kpi_html += '</div>'

    barra_prog = ""
    if progreso is not None:
        barra_prog = f'<div class="prog"><div class="prog-bar" style="width:{max(0,min(progreso,100)):.1f}%"></div></div>'

    # Gráficos como imágenes, en grilla 2 columnas
    graf_html = ""
    for tit, img_b64, color in figuras:
        graf_html += f"""
          <div class="gcard">
            <div class="gh" style="border-left-color:{color}">{tit}</div>
            <img class="gimg" src="{img_b64}" alt="">
          </div>"""

    return f"""
    <div class="page">
      <div class="hero">
        <div class="hero-l">
          <div class="mark">{logo}</div>
          <div class="hero-txt">
            <h1>BitaLogs - Panel de Rendimiento</h1>
            <p>{ESTUDIANTE} · Cuenta {CUENTA} · {CARRERA}</p>
          </div>
        </div>
        <div class="hero-r">{subtitulo}</div>
      </div>
      {barra_prog}
      <div class="kpis">{kpi_html}</div>
      <div class="grid">{graf_html}<div class="clear"></div></div>
    </div>"""


_CSS = """
  @page { size: A4 portrait; margin: 8mm; }
  *{box-sizing:border-box;margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif}
  body{color:#1B2436;background:#fff}
  .page{page-break-after:always}
  .page:last-child{page-break-after:auto}
  .clear{clear:both}

  /* Hero grande y con presencia */
  .hero{background:#3B82F6;background:linear-gradient(120deg,#3B82F6,#60A5FA);
        border-radius:20px;padding:30px 32px;color:#fff;margin-bottom:16px;
        width:100%;display:table}
  .hero-l{display:table-cell;vertical-align:middle;width:74%}
  .hero-r{display:table-cell;vertical-align:middle;text-align:right;
          font-size:22px;font-weight:800;color:#fff}
  .mark{width:82px;height:82px;border-radius:18px;background:#fff;
        display:inline-block;vertical-align:middle;padding:11px;text-align:center}
  .mark img{width:60px;height:60px;object-fit:contain;vertical-align:middle}
  .hero-txt{display:inline-block;vertical-align:middle;margin-left:20px}
  .hero h1{font-size:29px;font-weight:800;line-height:1.1}
  .hero-txt p{color:#DCE9FF;font-size:15px;margin-top:6px}

  .prog{height:11px;border-radius:7px;background:#E6EAF2;overflow:hidden;margin-bottom:16px}
  .prog-bar{height:100%;background:#2563EB;border-radius:7px}

  /* KPIs en dos filas centradas: 3 arriba, 2 abajo, grandes */
  .kpis{width:100%;margin-bottom:16px;text-align:center}
  .kpi-row{width:100%;margin-bottom:12px;font-size:0;text-align:center}
  .kpi-row:last-child{margin-bottom:0}
  .kpi{display:inline-block;vertical-align:top;width:31.5%;margin:0 0.8%;
       background:#fff;border:1px solid #E6EAF2;border-radius:15px;
       padding:20px 22px;min-height:104px;text-align:left}
  .kpi .ico{width:50px;height:50px;border-radius:13px;text-align:center;
            line-height:50px;margin-bottom:11px}
  .kpi .ico svg{width:26px;height:26px;vertical-align:middle}
  .kpi .val{font-size:32px;font-weight:800;line-height:1}
  .kpi .lbl{font-size:13px;color:#6B7890;font-weight:600;margin-top:6px}

  /* Grilla de gráficos: 2 columnas, grandes */
  .grid{width:100%;overflow:hidden}
  .gcard{float:left;width:49%;background:#fff;border:1px solid #E6EAF2;
         border-radius:16px;padding:18px 20px;margin-bottom:15px}
  .gcard:nth-child(odd){margin-right:2%}
  .gh{font-size:16px;font-weight:700;margin-bottom:10px;padding-left:11px;
      border-left:6px solid #2563EB;line-height:1.2}
  .gimg{width:100%;height:auto;display:block}
"""


def _html_completo(cuerpo):
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>{cuerpo}</body></html>"


_OP = {"page-size": "A4", "margin-top": "8mm", "margin-bottom": "8mm",
       "margin-left": "8mm", "margin-right": "8mm", "encoding": "UTF-8",
       "enable-local-file-access": None, "quiet": ""}


def _colores_secciones(n):
    base = ["#0EA5A5", "#2563EB", "#7C3AED", "#16A34A", "#F59E0B", "#0891B2"]
    return [base[i % len(base)] for i in range(n)]


def _prep_figuras(figuras):
    """Convierte [(titulo, fig)] en [(titulo, img_b64, color)]."""
    cols = _colores_secciones(len(figuras))
    out = []
    for i, (tit, fig) in enumerate(figuras):
        tipo = "pie" if any(t.type == "pie" for t in fig.data) else "bar"
        out.append((tit, _fig_img_b64(fig, tipo=tipo), cols[i]))
    return out


def construir_pdf(titulo, subtitulo, kpis, figuras, progreso=None):
    figs = _prep_figuras(figuras)
    cuerpo = _bloque_html(subtitulo, kpis, figs, progreso)
    html = _html_completo(cuerpo)
    return pdfkit.from_string(html, False, options=_OP, configuration=_WK)


def construir_pdf_multi(titulo, bloques):
    cuerpo = ""
    for b in bloques:
        figs = _prep_figuras(b.get("figuras", []))
        cuerpo += _bloque_html(b.get("subtitulo", ""), b.get("kpis", {}),
                               figs, b.get("progreso"))
    html = _html_completo(cuerpo)
    return pdfkit.from_string(html, False, options=_OP, configuration=_WK)
