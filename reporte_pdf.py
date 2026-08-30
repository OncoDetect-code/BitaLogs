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
import tempfile
import plotly.io as pio

from weasyprint import HTML
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

def _fig_img_b64(fig, w=820, h=500, tipo="bar"):
    """Rasteriza una figura Plotly a PNG y la devuelve como data-URI."""
    import base64
    import tempfile
    import os
    
    f = _estilizar(fig, tipo)
    
    # Intentar con el método más robusto
    try:
        # Usar archivo temporal con write_image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            pio.write_image(f, tmp.name, width=w, height=h, scale=2, engine='kaleido')
            with open(tmp.name, 'rb') as img_file:
                png_data = img_file.read()
            os.unlink(tmp.name)
            return "data:image/png;base64," + base64.b64encode(png_data).decode()
    except Exception as e:
        print(f"Error con write_image: {e}")
        
    # Segundo intento: con formato diferente
    try:
        png_data = f.to_image(format="png", width=w, height=h, scale=2)
        return "data:image/png;base64," + base64.b64encode(png_data).decode()
    except Exception as e:
        print(f"Error con to_image: {e}")
    
    # Último recurso: imagen de respaldo
    try:
        from PIL import Image, ImageDraw
        # Crear una imagen simple con el título
        img = Image.new('RGB', (w, h), color='#f0f4f8')
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], outline='#2563EB', width=3)
        draw.text((w//4, h//2), "Gráfico no disponible", fill='#2563EB')
        buf = BytesIO()
        img.save(buf, format='png')
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except:
        # Si todo falla, devolver un pixel transparente
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

def _estilizar(fig, tipo):
    """Aplica el look del dashboard a la figura antes de rasterizar."""
    import copy
    f = copy.deepcopy(fig)
    barras_h = any(getattr(t, "orientation", None) == "h"
                   for t in f.data if t.type == "bar")
    tiene_pie = any(t.type == "pie" for t in f.data)
    # Barras apiladas / agrupadas: varias trazas de barras con nombre
    # (p. ej. la evolución del tipo por semana). Necesitan leyenda para
    # saber qué color es cada serie.
    trazas_bar_nombradas = [t for t in f.data
                            if t.type == "bar" and getattr(t, "name", None)]
    trazas_linea_nombradas = [t for t in f.data
                              if t.type == "scatter" and getattr(t, "name", None)]
    es_apilado = (f.layout.barmode == "stack") or len(trazas_bar_nombradas) > 1
    es_multilinea = len(trazas_linea_nombradas) > 1
    # Las barras horizontales ya llevan el nombre de cada categoría como
    # título arriba de la barra, así que la leyenda sería redundante y se
    # amontona: se omite en ese caso.
    mostrar_leyenda = (tiene_pie or es_apilado or es_multilinea) and not barras_h

    f.update_layout(
        template="plotly_white",
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#1B2436", size=15, family="Arial"),
        title=None, margin=dict(l=45, r=25, t=15, b=55),
        showlegend=mostrar_leyenda,
    )
    f.update_xaxes(gridcolor="#EEF1F6", zeroline=False, tickfont=dict(size=13),
                   title_font=dict(size=14))
    f.update_yaxes(gridcolor="#EEF1F6", zeroline=False, tickfont=dict(size=13),
                   title_font=dict(size=14))
    if mostrar_leyenda:
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


def _bloque_html(subtitulo, kpis, figuras, progreso=None,
                 horas_acum=None, horas_tot=None, comentarios=None):
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

    # Hero derecho: si hay horas, muestra el dato estrella grande
    # (104 h / 400 h) con periodo y % completado, como el dashboard.
    if horas_acum is not None and horas_tot:
        pct_txt = f"{progreso:.0f}% completado" if progreso is not None else ""
        cap = f"{subtitulo} · {pct_txt}" if pct_txt else subtitulo
        hero_r = (f'<div class="hero-r">'
                  f'<div class="big">{horas_acum} h '
                  f'<span>/ {horas_tot} h</span></div>'
                  f'<div class="cap">{cap}</div></div>')
    else:
        hero_r = f'<div class="hero-r"><div class="cap">{subtitulo}</div></div>'

    def _grid(figs):
        h = ""
        for tit, img_b64, color in figs:
            h += f"""
              <div class="gcard">
                <div class="gh" style="border-left-color:{color}">{tit}</div>
                <img class="gimg" src="{img_b64}" alt="">
              </div>"""
        return h

    # Primera página: hero + KPIs + hasta 4 gráficos. Si hay más, van en
    # páginas siguientes con un encabezado ligero (sin repetir KPIs), para
    # que cada página quede bien armada en vez de dejar huecos.
    primera = figuras[:4]
    resto = figuras[4:]
    coment_html = _seccion_comentarios(comentarios or [])

    html = f"""
    <div class="page">
      <div class="hero">
        <div class="hero-l">
          <div class="mark">{logo}</div>
          <div class="hero-txt">
            <h1>BitaLogs - Panel de Rendimiento</h1>
            <p>{ESTUDIANTE} · Cuenta {CUENTA} · {CARRERA}</p>
          </div>
        </div>
        {hero_r}
      </div>
      {barra_prog}
      <div class="kpis">{kpi_html}</div>
      <div class="grid">{_grid(primera)}</div>
      {coment_html if not resto else ""}
    </div>"""

    grupos = [resto[i:i+4] for i in range(0, len(resto), 4)]
    for idx_g, grupo in enumerate(grupos):
        # Los comentarios van pegados al último grupo de gráficos, para
        # aprovechar el espacio restante de esa página.
        es_ultimo = (idx_g == len(grupos) - 1)
        html += f"""
    <div class="page">
      <div class="subhead">
        <span class="subhead-mark"></span>
        BitaLogs · {subtitulo} · continuación
      </div>
      <div class="grid">{_grid(grupo)}</div>
      {coment_html if es_ultimo else ""}
    </div>"""

    return html


_CSS = """
  @page { size: A4 portrait; margin: 8mm; }
  *{box-sizing:border-box;margin:0;padding:0;font-family:Arial,Helvetica,sans-serif}
  body{color:#1B2436;background:#fff}
  .page{page-break-after:always}
  .page:last-child{page-break-after:auto}

  /* Hero, con flex (WeasyPrint sí lo soporta) */
  .hero{background:linear-gradient(120deg,#3B82F6,#60A5FA);
        border-radius:18px;padding:18px 24px;color:#fff;margin-bottom:11px;
        display:flex;align-items:center;justify-content:space-between}
  .hero-l{display:flex;align-items:center}
  .mark{width:62px;height:62px;border-radius:15px;background:#fff;
        display:flex;align-items:center;justify-content:center;padding:8px;
        flex:none}
  .mark img{max-width:100%;max-height:100%;object-fit:contain}
  .hero-txt{margin-left:15px}
  .hero h1{font-size:23px;font-weight:800;line-height:1.15}
  .hero-txt p{color:#DCE9FF;font-size:12.5px;margin-top:4px}
  .hero-r{color:#fff;text-align:right;white-space:nowrap;padding-left:12px}
  .hero-r .big{font-size:30px;font-weight:800;line-height:1}
  .hero-r .big span{font-size:16px;color:#DCE9FF;font-weight:700}
  .hero-r .cap{color:#DCE9FF;font-size:11px;text-transform:uppercase;
               letter-spacing:.4px;margin-top:5px;font-weight:600}

  .prog{height:9px;border-radius:6px;background:#E6EAF2;overflow:hidden;margin-bottom:12px}
  .prog-bar{height:100%;background:#2563EB;border-radius:6px}

  /* Encabezado ligero para páginas de continuación */
  .subhead{font-family:'Poppins',Arial,sans-serif;font-weight:700;font-size:15px;
           color:#1B2436;display:flex;align-items:center;gap:10px;
           margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #E6EAF2}
  .subhead-mark{width:24px;height:24px;border-radius:7px;
                background:linear-gradient(135deg,#3B82F6,#60A5FA);display:inline-block}

  /* KPIs con flex, 3+2 centrados */
  .kpis{margin-bottom:12px}
  .kpi-row{display:flex;justify-content:center;gap:12px;margin-bottom:10px}
  .kpi-row:last-child{margin-bottom:0}
  .kpi{width:32%;background:#fff;border:1px solid #E6EAF2;border-radius:13px;
       padding:13px 16px;min-height:78px}
  .kpi .ico{width:38px;height:38px;border-radius:10px;display:flex;
            align-items:center;justify-content:center;margin-bottom:7px}
  .kpi .ico svg{width:20px;height:20px}
  .kpi .val{font-size:24px;font-weight:800;line-height:1}
  .kpi .lbl{font-size:11px;color:#6B7890;font-weight:600;margin-top:4px}

  /* Grilla de gráficos: 2 columnas con flex */
  .grid{display:flex;flex-wrap:wrap;gap:2%}
  .gcard{width:49%;background:#fff;border:1px solid #E6EAF2;
         border-radius:14px;padding:12px 15px;margin-bottom:12px;
         page-break-inside:avoid}
  .gh{font-size:14px;font-weight:700;margin-bottom:7px;padding-left:10px;
      border-left:5px solid #2563EB;line-height:1.2}
  .gimg{width:100%;height:auto;display:block}

  /* Sección de comentarios de evaluadores */
  .coment-sec{margin-top:6px}
  .coment{background:#fff;border:1px solid #E6EAF2;border-radius:12px;
          padding:12px 15px;margin-bottom:9px;page-break-inside:avoid}
  .coment-top{display:flex;justify-content:space-between;align-items:baseline;
              margin-bottom:5px}
  .coment-nom{font-family:'Poppins',Arial,sans-serif;font-weight:700;
              font-size:13px;color:#1B2436}
  .coment-meta{font-size:10.5px;color:#6B7890;font-weight:600;
               text-transform:uppercase;letter-spacing:.3px}
  .coment-txt{font-size:12px;color:#3A4560;line-height:1.5}
"""


def _html_completo(cuerpo):
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>{cuerpo}</body></html>"


def _fmt_fecha(valor):
    """
    Convierte una fecha guardada como ISO (2026-08-05T14:30) a un formato
    legible en español (5 ago 2026, 14:30). Si no puede parsearla, la
    devuelve tal cual.
    """
    if not valor:
        return ""
    s = str(valor).strip()
    meses = ["ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]
    from datetime import datetime as _dt
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = _dt.strptime(s, fmt)
            base = f"{d.day} {meses[d.month-1]} {d.year}"
            if "%H" in fmt:
                return f"{base}, {d.hour:02d}:{d.minute:02d}"
            return base
        except ValueError:
            continue
    return s


def _seccion_comentarios(comentarios):
    """
    HTML de la sección de comentarios de evaluadores. `comentarios` es una
    lista de dicts con claves: evaluador, fecha, semana, comentario.
    Devuelve '' si no hay comentarios.
    """
    if not comentarios:
        return ""
    tarjetas = ""
    for c in comentarios:
        evaluador = str(c.get("evaluador", "") or "").strip() or "Evaluador"
        fecha = _fmt_fecha(c.get("fecha", ""))
        semana = c.get("semana", "")
        texto = str(c.get("comentario", "") or "").strip()
        meta = f"Semana {semana}" + (f" · {fecha}" if fecha else "")
        tarjetas += f"""
          <div class="coment">
            <div class="coment-top">
              <span class="coment-nom">{evaluador}</span>
              <span class="coment-meta">{meta}</span>
            </div>
            <div class="coment-txt">{texto}</div>
          </div>"""
    return f"""
      <div class="coment-sec">
        <div class="subhead">
          <span class="subhead-mark"></span>
          Comentarios de los evaluadores
        </div>
        {tarjetas}
      </div>"""


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


def construir_pdf(titulo, subtitulo, kpis, figuras, progreso=None,
                  horas_acum=None, horas_tot=None, comentarios=None):
    figs = _prep_figuras(figuras)
    cuerpo = _bloque_html(subtitulo, kpis, figs, progreso,
                          horas_acum, horas_tot, comentarios)
    html = _html_completo(cuerpo)
    return HTML(string=html).write_pdf()


def construir_pdf_multi(titulo, bloques):
    cuerpo = ""
    for b in bloques:
        figs = _prep_figuras(b.get("figuras", []))
        cuerpo += _bloque_html(b.get("subtitulo", ""), b.get("kpis", {}),
                               figs, b.get("progreso"),
                               b.get("horas_acum"), b.get("horas_tot"),
                               b.get("comentarios"))
    html = _html_completo(cuerpo)
    return HTML(string=html).write_pdf()