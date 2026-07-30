"""
reporte_pdf.py — PDF de indicadores de BitaLogs con diseño tipo
*dashboard*: cabecera institucional con identificación del estudiante,
fila de tarjetas KPI de color, y gráficos distribuidos en grilla que
aprovecha toda la página.

Expone:
    construir_pdf(titulo, subtitulo, kpis, figuras) -> bytes
    construir_pdf_multi(titulo, bloques) -> bytes

Identidad del estudiante fija (cabecera de cada página):
    ESTUDIANTE, CUENTA, CARRERA
"""

from io import BytesIO
import copy

from fpdf import FPDF
from PIL import Image

# --- Identidad institucional (se muestra en la cabecera) ---
ESTUDIANTE = "Luis Velásquez"
CUENTA = "21941285"
CARRERA = "Ingeniería Biomédica"

_AZUL = (31, 78, 120)
_AZUL_CL = (46, 116, 181)
_GRIS_TXT = (90, 90, 90)
_BLANCO = (255, 255, 255)

# Colores de las tarjetas KPI (ciclo).
_KPI_COLORES = [(31, 78, 120), (39, 122, 90), (176, 58, 46),
                (124, 74, 158), (200, 128, 20)]

# Paleta forzada sobre cada figura (evita gráficos sin color).
_PALETA = ["#1F4E78", "#2E8B57", "#C0392B", "#8E44AD", "#D68910",
           "#16A085", "#2874A6", "#CA6F1E"]

_REEMPLAZOS = {
    "—": "-", "–": "-", "…": "...", "'": "'", "'": "'",
    "\u201c": '"', "\u201d": '"', "•": "-", "·": "-",
}

# Márgenes de trabajo
_MX = 12          # margen izquierdo/derecho
_ANCHO = 210 - 2 * _MX


def _sanear(texto: str) -> str:
    if not texto:
        return ""
    t = str(texto)
    for k, v in _REEMPLAZOS.items():
        t = t.replace(k, v)
    return t.encode("latin-1", "ignore").decode("latin-1").strip()


def _figura_limpia(fig, con_leyenda_abajo=True):
    """
    Copia la figura y le aplica una plantilla clara, colores forzados y
    -clave para no encimar títulos- mueve la leyenda ABAJO en horizontal
    y quita el título interno del gráfico (el título lo pone el PDF).
    """
    f = copy.deepcopy(fig)
    tiene_pie = any(t.type == "pie" for t in f.data)
    # La leyenda solo aporta en los pie/dona. En barras, las etiquetas
    # de los ejes ya identifican cada categoría, así que la leyenda
    # sería redundante y robaría espacio: se oculta.
    mostrar_leyenda = tiene_pie and con_leyenda_abajo
    f.update_layout(
        template="plotly_white",
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#333333", size=15),
        title=None,
        showlegend=mostrar_leyenda,
        margin=dict(l=55, r=25, t=15,
                    b=70 if mostrar_leyenda else 45),
    )
    if mostrar_leyenda:
        f.update_layout(legend=dict(
            orientation="h", yanchor="top", y=-0.05,
            xanchor="center", x=0.5, font=dict(size=11)))
    for i, tr in enumerate(f.data):
        if tr.type == "pie":
            tr.marker.colors = _PALETA
            tr.textfont = dict(color="white", size=13)
            tr.textposition = "inside"
        elif tr.type == "bar":
            if tr.marker.color is None or isinstance(tr.marker.color, str):
                tr.marker.color = _PALETA[i % len(_PALETA)]
        elif tr.type in ("scatter", "line"):
            tr.line.color = _PALETA[i % len(_PALETA)]
            tr.line.width = 3
    return f


def _fig_a_imagen(fig, w, h, con_leyenda_abajo=True, scale=2):
    f = _figura_limpia(fig, con_leyenda_abajo)
    png = f.to_image(format="png", width=w, height=h, scale=scale)
    return Image.open(BytesIO(png))


class _PDF(FPDF):
    def __init__(self, pie_texto):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._pie_texto = pie_texto
        self.set_auto_page_break(auto=True, margin=14)

    def header(self):
        # Banda institucional con identidad del estudiante (no genérica).
        self.set_fill_color(*_AZUL)
        self.rect(0, 0, 210, 20, style="F")
        self.set_xy(_MX, 4)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*_BLANCO)
        self.cell(0, 6, _sanear(ESTUDIANTE), new_x="LMARGIN", new_y="NEXT")
        self.set_x(_MX)
        self.set_font("Helvetica", "", 8.5)
        self.cell(0, 4, _sanear(f"Cuenta {CUENTA}  ·  {CARRERA}  ·  "
                                "Práctica Profesional"))
        self.set_y(26)

    def footer(self):
        self.set_y(-11)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, _sanear(f"{self._pie_texto}  ·  página {self.page_no()}"),
                  align="C")


def _titulo_bloque(pdf, titulo, subtitulo):
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*_AZUL)
    pdf.cell(0, 9, _sanear(titulo), align="C", new_x="LMARGIN", new_y="NEXT")
    if subtitulo:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*_GRIS_TXT)
        pdf.cell(0, 6, _sanear(subtitulo), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _tarjetas_kpis(pdf, kpis: dict):
    if not kpis:
        return
    n = len(kpis)
    gap = 4
    ancho = (_ANCHO - gap * (n - 1)) / n
    alto = 21
    y0 = pdf.get_y()
    for i, (k, v) in enumerate(kpis.items()):
        x = _MX + i * (ancho + gap)
        color = _KPI_COLORES[i % len(_KPI_COLORES)]
        pdf.set_fill_color(*color)
        pdf.rect(x, y0, ancho, alto, style="F", round_corners=True,
                 corner_radius=1.5)
        pdf.set_xy(x, y0 + 3.5)
        pdf.set_font("Helvetica", "B", 17)
        pdf.set_text_color(*_BLANCO)
        pdf.cell(ancho, 8, _sanear(str(v)), align="C")
        pdf.set_xy(x, y0 + 12.5)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_BLANCO)
        pdf.multi_cell(ancho, 3.5, _sanear(k), align="C")
    pdf.set_y(y0 + alto + 6)


def _grid_graficos(pdf, figuras, cols=2):
    """
    Grilla de `cols` columnas que reparte el ALTO disponible de la
    página entre las filas de gráficos, para aprovechar el espacio en
    vez de dejar la mitad inferior en blanco. Cada gráfico se rasteriza
    al tamaño exacto de su celda.
    """
    if not figuras:
        return
    gap = 7
    cel_w = (_ANCHO - gap * (cols - 1)) / cols
    n_filas = (len(figuras) + cols - 1) // cols

    y_ini = pdf.get_y()
    alto_disp = pdf.page_break_trigger - y_ini
    # Alto por fila: reparte el espacio, con techo y piso razonables.
    fila_h = alto_disp / n_filas
    fila_h = max(58, min(fila_h, 95))
    titulo_h = 7
    img_h_mm = fila_h - titulo_h - 4

    # Relación de aspecto de la imagen según el alto de celda en mm.
    px_w = 900
    px_h = int(px_w * (img_h_mm / cel_w))

    idx = 0
    for r in range(n_filas):
        fila = figuras[idx:idx + cols]
        if pdf.get_y() + fila_h > pdf.page_break_trigger:
            pdf.add_page()
        y_fila = pdf.get_y()
        for j, (tit, fig) in enumerate(fila):
            x = _MX + j * (cel_w + gap)
            # Título de la celda
            pdf.set_xy(x, y_fila)
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*_AZUL)
            pdf.cell(cel_w, titulo_h, _sanear(tit), align="C")
            # Imagen
            img = _fig_a_imagen(fig, px_w, px_h)
            real_h = cel_w * (img.height / img.width)
            pdf.image(img, x=x, y=y_fila + titulo_h, w=cel_w, h=real_h)
        pdf.set_y(y_fila + fila_h)
        idx += cols


def construir_pdf(titulo: str, subtitulo: str, kpis: dict, figuras: list) -> bytes:
    pdf = _PDF(subtitulo)
    pdf.add_page()
    _titulo_bloque(pdf, titulo, subtitulo)
    _tarjetas_kpis(pdf, kpis)
    _grid_graficos(pdf, figuras, cols=2)
    return bytes(pdf.output())


def construir_pdf_multi(titulo: str, bloques: list) -> bytes:
    pdf = _PDF(titulo)
    for b in bloques:
        pdf.add_page()
        _titulo_bloque(pdf, titulo, b.get("subtitulo", ""))
        _tarjetas_kpis(pdf, b.get("kpis", {}))
        _grid_graficos(pdf, b.get("figuras", []), cols=2)
    return bytes(pdf.output())
