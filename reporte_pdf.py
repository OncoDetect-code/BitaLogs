"""
reporte_pdf.py — Genera el PDF de indicadores de BitaLogs (estilo
institucional UNITEC: azul sobrio), pensado para descargarse tanto de
una semana puntual como de toda la práctica.

Expone:
    construir_pdf(titulo, subtitulo, kpis, figuras) -> bytes

`kpis` es un dict {"Etiqueta": "valor"} (máx. ~4 para que se vea bien).
`figuras` es una lista de tuplas (titulo_grafico, figura_plotly).
"""

from io import BytesIO

from fpdf import FPDF
from PIL import Image

_AZUL = (31, 78, 120)     # #1F4E78
_GRIS = (217, 225, 242)   # #D9E1F2
_GRIS_TXT = (70, 70, 70)

# Las fuentes core de fpdf2 (Helvetica) solo soportan latin-1: los
# emojis y signos como el guión largo "—" rompen la generación. Se
# normalizan antes de imprimir cualquier texto.
_REEMPLAZOS = {
    "—": "-", "–": "-", "…": "...", "’": "'", "‘": "'",
    "“": '"', "”": '"', "•": "-",
}


def _sanear(texto: str) -> str:
    if not texto:
        return ""
    t = str(texto)
    for k, v in _REEMPLAZOS.items():
        t = t.replace(k, v)
    # Cualquier otro carácter fuera de latin-1 (p.ej. emojis) se descarta
    return t.encode("latin-1", "ignore").decode("latin-1").strip()


def _fig_a_imagen(fig, w=1000, h=520, scale=2):
    """Convierte una figura de Plotly a imagen PIL (requiere kaleido)."""
    png = fig.to_image(format="png", width=w, height=h, scale=scale)
    return Image.open(BytesIO(png))


class _PDF(FPDF):
    def __init__(self, pie_texto):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._pie_texto = pie_texto
        self.set_auto_page_break(auto=True, margin=16)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_AZUL)
        self.cell(0, 6, "FACULTAD DE INGENIERIA - INGENIERIA BIOMEDICA (UNITEC)",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_AZUL)
        self.set_line_width(0.4)
        self.line(10, 15, 200, 15)
        self.ln(6)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, _sanear(f"BitaLogs - {self._pie_texto} - pagina {self.page_no()}"),
                  align="C")


def _portada(pdf, titulo, subtitulo):
    pdf.add_page()
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*_AZUL)
    pdf.cell(0, 12, _sanear(titulo), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*_GRIS_TXT)
    pdf.cell(0, 8, _sanear(subtitulo), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)


def _tabla_kpis(pdf, kpis: dict):
    if not kpis:
        return
    pdf.set_font("Helvetica", "", 11)
    n = len(kpis)
    ancho = 190 / n
    y0 = pdf.get_y()
    for i, (k, v) in enumerate(kpis.items()):
        x = 10 + i * ancho
        pdf.set_fill_color(*_GRIS)
        pdf.rect(x, y0, ancho - 2, 22, style="F")
        pdf.set_xy(x, y0 + 3)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*_AZUL)
        pdf.cell(ancho - 2, 9, _sanear(str(v)), align="C")
        pdf.set_xy(x, y0 + 13)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_GRIS_TXT)
        pdf.cell(ancho - 2, 6, _sanear(k), align="C")
    pdf.set_y(y0 + 28)


def _grafico(pdf, fig, titulo_fig, ancho=190):
    img = _fig_a_imagen(fig)
    alto = ancho * (img.height / img.width)
    # Salto de página si el gráfico no cabe en lo que queda de la hoja
    if pdf.get_y() + alto + 14 > pdf.page_break_trigger:
        pdf.add_page()
    if titulo_fig:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*_AZUL)
        pdf.cell(0, 8, _sanear(titulo_fig), new_x="LMARGIN", new_y="NEXT")
    x = (210 - ancho) / 2
    pdf.image(img, x=x, w=ancho, h=alto)
    pdf.ln(alto + 8)


def construir_pdf(titulo: str, subtitulo: str, kpis: dict, figuras: list) -> bytes:
    """
    Arma el PDF completo: portada con título/subtítulo, fila de KPIs y
    luego cada gráfico de `figuras` en su propia sección (con salto de
    página automático si no caben todos en una hoja).
    """
    pdf = _PDF(subtitulo)
    _portada(pdf, titulo, subtitulo)
    _tabla_kpis(pdf, kpis)
    for tit, fig in figuras:
        _grafico(pdf, fig, tit)
    return bytes(pdf.output())
