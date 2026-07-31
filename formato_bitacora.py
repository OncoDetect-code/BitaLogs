"""
Generador del formato oficial "Matriz de Impacto" (UNITEC) para BitaLogs.

Replica la estructura del Excel institucional:
  - Encabezado: logo UNITEC centrado + FACULTAD DE INGENIERIA /
    INGENIERIA BIOMEDICA.
  - Tabla de 7 columnas: Semana | Equipo o proceso | Problema identificado |
    Solucion sugerida | Problema ya resuelto? | Impacto esperado o
    beneficio real | Observaciones.
  - Al final, la evidencia fotografica, distribuida y centrada segun
    cuantas imagenes haya (1 a 4).

El documento usa la tipografia Poppins (tamano base 8) y esta pensado
para descargarse e imprimirse tal cual como evidencia institucional.

Expone:
    bitacora_html(registros, titulo) -> str

`registros` es una lista de dicts con las claves internas de BitaLogs:
    semana, dia, fecha, area, equipo, problema, solucion, resuelto,
    impacto, observaciones, img1..img4
"""

import os
from html import escape

# Paleta institucional sobria
_AZUL = "#1F4E78"
_GRIS_ENC = "#D9E1F2"

# Fuente Poppins servida desde Google Fonts (con respaldo a sans-serif).
_POPPINS_LINK = ("https://fonts.googleapis.com/css2?"
                 "family=Poppins:wght@400;600;700&display=swap")

# Logo UNITEC embebido como data-URI (para que el HTML sea autocontenido
# y el logo se vea aunque el archivo se abra sin conexion).
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo_b64.txt")
try:
    with open(_LOGO_PATH, "r", encoding="utf-8") as _f:
        _LOGO_DATA = _f.read().strip()
except Exception:
    _LOGO_DATA = ""


# Valores que, venidos de un DataFrame, significan "vacio" pero llegan
# como texto ("None", "nan") o como float NaN. Sin filtrarlos, un slot
# de imagen vacio producia <img src="nan"> = el icono roto.
_VACIOS = {"", "none", "nan", "null", "<na>"}


def _es_vacio(v):
    if v is None:
        return True
    try:
        if isinstance(v, float) and v != v:
            return True
    except Exception:
        pass
    return str(v).strip().lower() in _VACIOS


def _v(rep, key, default=""):
    val = rep.get(key, default)
    return "" if _es_vacio(val) else str(val)


def _imgs_de(rep):
    """
    Lista de data-URIs REALES presentes (1 a 4) en el registro, en el
    orden img1 a img4. Se ignoran los slots vacios y cualquier valor que
    no sea un data-URI de imagen, para no renderizar nunca un <img> roto.
    """
    out = []
    for k in ("img1", "img2", "img3", "img4"):
        v = rep.get(k)
        if _es_vacio(v):
            continue
        s = str(v).strip()
        if s.startswith("data:image"):
            out.append(s)
    return out


def _bloque_imagenes(imgs):
    """
    HTML de la evidencia fotografica, centrada y distribuida segun la
    cantidad: 1 grande, 2 lado a lado, 3 en fila, 4 en grilla 2x2.
    """
    n = len(imgs)
    if n == 0:
        return ""

    if n == 1:
        col_w = "60%"
    elif n == 2:
        col_w = "46%"
    elif n == 3:
        col_w = "31%"
    else:
        col_w = "46%"

    celdas = ""
    for src in imgs:
        celdas += (
            f'<div class="img-cell" style="flex:0 0 {col_w}; max-width:{col_w};">'
            f'<img src="{src}" alt="" onerror="this.style.display=\'none\'"/></div>'
        )

    return f'<div class="img-grid">{celdas}</div>'


def bitacora_html(registros, titulo="Matriz de Impacto"):
    """HTML acotado de la bitacora en formato UNITEC, listo para descargar."""
    filas = ""
    bloques_img = ""

    for rep in registros:
        sem = _v(rep, "semana")
        dia = _v(rep, "dia")
        etiqueta_sem = f"Semana {sem}" + (f" - Dia {dia}" if dia else "")
        filas += (
            "<tr>"
            f"<td class='c sem'>{escape(etiqueta_sem)}</td>"
            f"<td>{escape(_v(rep,'equipo'))}</td>"
            f"<td>{escape(_v(rep,'problema'))}</td>"
            f"<td>{escape(_v(rep,'solucion'))}</td>"
            f"<td class='c'>{escape(_v(rep,'resuelto'))}</td>"
            f"<td>{escape(_v(rep,'impacto'))}</td>"
            f"<td>{escape(_v(rep,'observaciones'))}</td>"
            "</tr>"
        )
        imgs = _imgs_de(rep)
        if imgs:
            enc = escape(_v(rep, "equipo")) or "Registro"
            bloques_img += (
                f"<div class='reg-evidencia'>"
                f"<div class='reg-tit'>{escape(etiqueta_sem)}: {enc}</div>"
                f"{_bloque_imagenes(imgs)}</div>"
            )

    logo_html = (f'<img class="logo" src="{_LOGO_DATA}" alt="UNITEC"/>'
                 if _LOGO_DATA else "")

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>{escape(titulo)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{_POPPINS_LINK}" rel="stylesheet">
<style>
  @page {{ size: landscape; margin: 10mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Poppins', Arial, sans-serif; font-size: 8px;
         color: #000; background: #fff; margin: 0; padding: 8px; }}
  .doc {{ max-width: 1050px; margin: 0 auto; }}
  .enc {{ text-align: center; margin-bottom: 8px; }}
  .enc .logo {{ height: 46px; width: auto; margin-bottom: 4px; }}
  .enc .fac {{ font-weight: 700; font-size: 10px; letter-spacing: .3px; }}
  .enc .car {{ font-weight: 600; font-size: 9px; color: {_AZUL}; }}
  .enc .sub {{ font-size: 8px; color: #444; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  th, td {{ border: 1px solid #444; padding: 3px 5px; vertical-align: top;
           text-align: left; font-size: 8px; }}
  th {{ background: {_GRIS_ENC}; color: #1a1a1a; text-align: center;
       font-weight: 600; }}
  .c {{ text-align: center; }}
  .sem {{ font-weight: 600; white-space: nowrap; color: {_AZUL}; }}
  .reg-evidencia {{ margin-top: 10px; page-break-inside: avoid; }}
  .reg-tit {{ font-weight: 600; font-size: 8px; color: {_AZUL};
             border-left: 3px solid {_AZUL}; padding-left: 5px;
             margin-bottom: 3px; }}
  .img-grid {{ display: flex; flex-wrap: wrap; gap: 6px;
              justify-content: center; align-items: flex-start; }}
  .img-cell {{ display: flex; justify-content: center; }}
  .img-cell img {{ width: 100%; height: auto; max-height: 230px;
                  object-fit: contain; border: 1px solid #bbb;
                  border-radius: 2px; display: block; }}
  .seccion-fotos {{ margin-top: 14px; }}
  .seccion-fotos > h3 {{ font-size: 9px; color: {_AZUL}; font-weight: 600;
                        border-bottom: 1px solid {_AZUL}; padding-bottom: 2px; }}
</style></head><body>
<div class="doc">

  <div class="enc">
    {logo_html}
    <div class="fac">FACULTAD DE INGENIERIA</div>
    <div class="car">INGENIERIA BIOMEDICA</div>
    <div class="sub">{escape(titulo)}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width:10%">Semana</th>
        <th style="width:15%">Equipo o proceso</th>
        <th style="width:19%">Problema identificado</th>
        <th style="width:18%">Solucion sugerida</th>
        <th style="width:8%">Problema ya resuelto?</th>
        <th style="width:18%">Impacto esperado o beneficio real</th>
        <th style="width:12%">Observaciones</th>
      </tr>
    </thead>
    <tbody>
      {filas if filas else '<tr><td colspan="7" class="c">Sin registros para el filtro seleccionado.</td></tr>'}
    </tbody>
  </table>

  {f'<div class="seccion-fotos"><h3>Evidencia fotografica</h3>{bloques_img}</div>' if bloques_img else ''}

</div></body></html>"""
