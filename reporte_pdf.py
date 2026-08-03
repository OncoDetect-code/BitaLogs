"""
reporte_pdf.py — Reporte de indicadores de BitaLogs en PDF, con la
identidad visual de la app (marca BitaLogs):

  - Cabecera con hero azul degradado, logo de BitaLogs e identidad del
    estudiante.
  - Fila de tarjetas KPI con acento de color.
  - Gráficos distribuidos en grilla, con paleta viva y sin superposición.

Expone:
    construir_pdf(titulo, subtitulo, kpis, figuras) -> bytes
    construir_pdf_multi(titulo, bloques) -> bytes
"""

from io import BytesIO
import copy
import os

from fpdf import FPDF
from PIL import Image

# ---- Identidad ----
ESTUDIANTE = "Luis Velásquez"
CUENTA = "21941285"
CARRERA = "Ingeniería Biomédica"

# ---- Paleta de marca (coincide con el dashboard) ----
_AZUL = (37, 99, 235)       # #2563EB
_AZUL_CL = (96, 165, 250)   # #60A5FA
_INK = (27, 36, 54)         # #1B2436
_MUTED = (107, 120, 144)    # #6B7890
_BLANCO = (255, 255, 255)
_GRIS_BG = (238, 241, 246)  # #EEF1F6

_KPI_ACENTOS = [(37, 99, 235), (14, 165, 165), (239, 68, 68),
                (124, 58, 237), (245, 158, 11)]

_PALETA = ["#2563EB", "#0EA5A5", "#7C3AED", "#F59E0B", "#EF4444",
           "#16A34A", "#0891B2", "#DB2777"]

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo_bitalogs.png")

_MX = 12
_ANCHO = 210 - 2 * _MX

_REEMPLAZOS = {
    "—": "-", "–": "-", "…": "...", "'": "'", "'": "'",
    "\u201c": '"', "\u201d": '"', "•": "-", "·": "-",
}


def _sanear(texto):
    if not texto:
        return ""
    t = str(texto)
    for k, v in _REEMPLAZOS.items():
        t = t.replace(k, v)
    return t.encode("latin-1", "ignore").decode("latin-1").strip()


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _figura_limpia(fig, con_leyenda_abajo=True):
    """Aplica el look de marca a una figura Plotly antes de exportarla."""
    f = copy.deepcopy(fig)
    tiene_pie = any(t.type == "pie" for t in f.data)
    barras_h = any(getattr(t, "orientation", None) == "h"
                   for t in f.data if t.type == "bar")
    mostrar_leyenda = tiene_pie and con_leyenda_abajo

    f.update_layout(
        template="plotly_white",
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#1B2436", size=24, family="Arial"),
        title=None,
        showlegend=mostrar_leyenda,
        margin=dict(l=55, r=35, t=15, b=95 if mostrar_leyenda else 55),
    )
    f.update_xaxes(title_font=dict(size=23), tickfont=dict(size=20),
                   gridcolor="#EEF1F6")
    f.update_yaxes(title_font=dict(size=23), tickfont=dict(size=20),
                   gridcolor="#EEF1F6")
    if mostrar_leyenda:
        f.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.06,
                                    xanchor="center", x=0.5,
                                    font=dict(size=22)))
    for i, tr in enumerate(f.data):
        if tr.type == "pie":
            # Paleta pie con máximo contraste entre porciones vecinas y
            # colores vivos (como el dashboard): azul, ámbar, verde,
            # violeta, rosa, teal.
            tr.marker.colors = ["#2563EB", "#F59E0B", "#16A34A",
                                "#7C3AED", "#EF4444", "#0EA5A5",
                                "#DB2777", "#0891B2"]
            tr.textfont = dict(color="white", size=30, family="Arial Black")
            tr.textposition = "inside"
            tr.textinfo = "percent"
            tr.insidetextorientation = "horizontal"
            tr.marker.line = dict(color="white", width=4)
        elif tr.type == "bar":
            if tr.marker.color is None or isinstance(tr.marker.color, str):
                tr.marker.color = _PALETA[i % len(_PALETA)]
            tr.textfont = dict(size=23, color="#1B2436")
            tr.outsidetextfont = dict(size=23, color="#1B2436")
            try:
                tr.marker.cornerradius = 8
            except Exception:
                pass

    if barras_h:
        # Con color por categoría, Plotly crea una traza por categoría
        # (cada una con un solo valor en y). Hay que recolectar y de
        # TODAS las trazas, no solo la primera, o solo se anota una barra.
        cats = []
        for tr in f.data:
            if tr.type == "bar" and getattr(tr, "orientation", None) == "h":
                for yv in (tr.y or []):
                    if yv not in cats:
                        cats.append(yv)
        f.update_yaxes(showticklabels=False, title="")
        f.update_layout(bargap=0.68, margin=dict(l=55, r=45, t=45, b=55))
        for cat in cats:
            f.add_annotation(x=0, y=cat, text="<b>%s</b>" % cat,
                             showarrow=False, xanchor="left", yanchor="bottom",
                             yshift=24, xshift=-2,
                             font=dict(size=20, color="#1B2436"))
    return f


def _fig_a_imagen(fig, w, h, con_leyenda_abajo=True, scale=3):
    f = _figura_limpia(fig, con_leyenda_abajo)
    png = f.to_image(format="png", width=w, height=h, scale=scale)
    return Image.open(BytesIO(png))


class _PDF(FPDF):
    def __init__(self, pie_texto):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._pie_texto = pie_texto
        self.set_auto_page_break(auto=True, margin=14)

    def footer(self):
        self.set_y(-11)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, _sanear("BitaLogs  ·  %s  ·  página %d"
                                % (self._pie_texto, self.page_no())),
                  align="C")


def _hero(pdf, titulo, subtitulo):
    """Cabecera azul con logo de BitaLogs e identidad."""
    x, y, w, h = _MX, 12, _ANCHO, 30
    # Fondo azul (dos rectángulos para simular degradado suave)
    pdf.set_fill_color(*_AZUL)
    pdf.rect(x, y, w, h, style="F", round_corners=True, corner_radius=4)
    pdf.set_fill_color(*_AZUL_CL)
    pdf.rect(x + w * 0.62, y, w * 0.38, h, style="F", round_corners=True,
             corner_radius=4)
    pdf.set_fill_color(*_AZUL)
    pdf.rect(x + w * 0.60, y, w * 0.06, h, style="F")

    # Logo en recuadro blanco
    if os.path.exists(_LOGO_PATH):
        pdf.set_fill_color(*_BLANCO)
        pdf.rect(x + 5, y + 6, 18, 18, style="F", round_corners=True,
                 corner_radius=3)
        try:
            pdf.image(_LOGO_PATH, x=x + 6.5, y=y + 7.5, w=15, h=15)
        except Exception:
            pass

    # Texto identidad
    pdf.set_xy(x + 27, y + 7)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*_BLANCO)
    pdf.cell(w * 0.58 - 27, 7, "BitaLogs - Panel de Rendimiento",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x + 27)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(w * 0.58 - 27, 5, _sanear("%s  ·  Cuenta %s  ·  %s"
                                       % (ESTUDIANTE, CUENTA, CARRERA)))

    # Subtítulo del periodo (derecha): solo "Toda la práctica" o "Semana N"
    periodo = subtitulo
    for pref in ("Ingeniería Biomédica · ", "Ingeniería Biomédica - ",
                 "Ingenieria Biomedica - ", "Ingenieria Biomedica · "):
        periodo = periodo.replace(pref, "")
    pdf.set_xy(x + w * 0.62, y + 11)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_BLANCO)
    pdf.cell(w * 0.36 - 4, 7, _sanear(periodo), align="R")

    pdf.set_y(y + h + 6)


def _tarjetas_kpis(pdf, kpis):
    if not kpis:
        return
    n = len(kpis)
    gap = 4
    ancho = (_ANCHO - gap * (n - 1)) / n
    alto = 20
    y0 = pdf.get_y()
    for i, (k, v) in enumerate(kpis.items()):
        x = _MX + i * (ancho + gap)
        # tarjeta blanca con barra de acento
        pdf.set_fill_color(*_BLANCO)
        pdf.set_draw_color(230, 234, 242)
        pdf.rect(x, y0, ancho, alto, style="DF", round_corners=True,
                 corner_radius=2.5)
        color = _KPI_ACENTOS[i % len(_KPI_ACENTOS)]
        pdf.set_fill_color(*color)
        pdf.rect(x, y0 + 2, 2.2, alto - 4, style="F")
        pdf.set_xy(x + 5, y0 + 3.5)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*_INK)
        pdf.cell(ancho - 6, 8, _sanear(str(v)))
        pdf.set_xy(x + 5, y0 + 12)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_MUTED)
        pdf.cell(ancho - 6, 4, _sanear(k))
    pdf.set_y(y0 + alto + 6)


def _titulo_seccion(pdf, x, y, w, texto, color_hex):
    pdf.set_fill_color(*_hex_rgb(color_hex))
    pdf.rect(x, y + 0.5, 2.2, 5.5, style="F")
    pdf.set_xy(x + 4, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_INK)
    pdf.cell(w - 4, 6.5, _sanear(texto))


def _grid_graficos(pdf, figuras, cols=2):
    if not figuras:
        return
    gap = 7
    cel_w = (_ANCHO - gap * (cols - 1)) / cols
    n_filas = (len(figuras) + cols - 1) // cols
    y_ini = pdf.get_y()
    alto_disp = pdf.page_break_trigger - y_ini
    fila_h = max(66, min(alto_disp / n_filas, 100))
    titulo_h = 9
    img_h_mm = fila_h - titulo_h - 5
    px_w = 1000
    px_h = int(px_w * (img_h_mm / cel_w))

    colores = ["#0EA5A5", "#2563EB", "#7C3AED", "#16A34A", "#F59E0B", "#0891B2"]
    idx = 0
    for r in range(n_filas):
        fila = figuras[idx:idx + cols]
        if pdf.get_y() + fila_h > pdf.page_break_trigger:
            pdf.add_page()
        y_fila = pdf.get_y()
        for j, (tit, fig) in enumerate(fila):
            x = _MX + j * (cel_w + gap)
            # tarjeta blanca de fondo
            pdf.set_fill_color(*_BLANCO)
            pdf.set_draw_color(230, 234, 242)
            pdf.rect(x, y_fila, cel_w, fila_h - 3, style="DF",
                     round_corners=True, corner_radius=3)
            _titulo_seccion(pdf, x + 4, y_fila + 4, cel_w - 8, tit,
                            colores[(idx + j) % len(colores)])
            img = _fig_a_imagen(fig, px_w, px_h)
            real_h = (cel_w - 8) * (img.height / img.width)
            pdf.image(img, x=x + 4, y=y_fila + titulo_h + 3, w=cel_w - 8,
                      h=min(real_h, img_h_mm))
        pdf.set_y(y_fila + fila_h)
        idx += cols


def construir_pdf(titulo, subtitulo, kpis, figuras):
    pdf = _PDF(subtitulo)
    pdf.add_page()
    _hero(pdf, titulo, subtitulo)
    _tarjetas_kpis(pdf, kpis)
    _grid_graficos(pdf, figuras, cols=2)
    return bytes(pdf.output())


def construir_pdf_multi(titulo, bloques):
    pie = bloques[0]["subtitulo"] if bloques else titulo
    pdf = _PDF(pie)
    for b in bloques:
        pdf.add_page()
        _hero(pdf, titulo, b.get("subtitulo", ""))
        _tarjetas_kpis(pdf, b.get("kpis", {}))
        _grid_graficos(pdf, b.get("figuras", []), cols=2)
    return bytes(pdf.output())
