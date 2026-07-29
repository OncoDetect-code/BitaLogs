"""
Generador del formato oficial "Matriz de Impacto" (UNITEC) para BitaLogs.

Replica la estructura del Excel institucional:
  - Encabezado: FACULTAD DE INGENIERÍA / INGENIERÍA BIOMÉDICA
  - Tabla de 7 columnas: Semana | Equipo o proceso | Problema identificado |
    Solución sugerida | ¿Problema ya resuelto? | Impacto esperado o
    beneficio real | Observaciones
  - Debajo de cada registro (o al final), la evidencia fotográfica,
    distribuida y centrada según cuántas imágenes haya (1 a 4).

Expone:
    bitacora_html(registros, titulo) -> str   (vista previa / imprimir)

`registros` es una lista de dicts con las claves internas de BitaLogs:
    semana, dia, fecha, area, equipo, problema, solucion, resuelto,
    impacto, observaciones, img1..img4
"""

from html import escape

# Paleta institucional sobria
_AZUL = "#1F4E78"
_GRIS_ENC = "#D9E1F2"


# Valores que, venidos de un DataFrame, significan "vacío" pero llegan
# como texto ("None", "nan") o como float NaN. Sin filtrarlos, un slot
# de imagen vacío producía <img src="nan"> = el ícono roto.
_VACIOS = {"", "none", "nan", "null", "<na>"}


def _es_vacio(v):
    if v is None:
        return True
    try:
        # float('nan') != float('nan'): así detectamos NaN de pandas
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
    orden img1→img4. Se ignoran los slots vacíos (None, NaN, "None",
    "nan", cadenas en blanco) y también cualquier valor que no sea un
    data-URI de imagen, para no renderizar nunca un <img> roto.
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
    Devuelve el HTML de la evidencia fotográfica, centrada y bien
    distribuida según la cantidad:
      1  -> una grande centrada
      2  -> dos lado a lado
      3  -> tres en fila
      4  -> grilla 2x2
    Siempre centrado y aprovechando el ancho disponible.
    """
    n = len(imgs)
    if n == 0:
        return ""

    # Ancho de cada celda según cantidad (para aprovechar el espacio)
    if n == 1:
        col_w = "70%"
        cols = 1
    elif n == 2:
        col_w = "48%"
        cols = 2
    elif n == 3:
        col_w = "32%"
        cols = 3
    else:  # 4
        col_w = "48%"
        cols = 2

    celdas = ""
    for src in imgs:
        celdas += (
            f'<div class="img-cell" style="flex:0 0 {col_w}; max-width:{col_w};">'
            f'<img src="{src}" alt="evidencia"/></div>'
        )

    return f"""
    <div class="evidencia">
      <div class="evidencia-tit">EVIDENCIA FOTOGRÁFICA</div>
      <div class="img-grid">{celdas}</div>
    </div>
    """


def bitacora_html(registros, titulo="Matriz de Impacto"):
    """HTML completo de la bitácora en formato UNITEC, con botón imprimir."""
    filas = ""
    bloques_img = ""

    for rep in registros:
        sem = _v(rep, "semana")
        dia = _v(rep, "dia")
        etiqueta_sem = f"Semana {sem}" + (f" · Día {dia}" if dia else "")
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
        # Evidencia por registro (si tiene imágenes)
        imgs = _imgs_de(rep)
        if imgs:
            enc = escape(_v(rep, "equipo")) or "Registro"
            bloques_img += (
                f"<div class='reg-evidencia'>"
                f"<div class='reg-tit'>{escape(etiqueta_sem)} — {enc}</div>"
                f"{_bloque_imagenes(imgs)}</div>"
            )

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>{escape(titulo)}</title>
<style>
  @page {{ size: landscape; margin: 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10px;
         color: #000; background: #fff; margin: 0; padding: 10px; }}
  .doc {{ max-width: 1050px; margin: 0 auto; }}
  .enc {{ text-align: center; margin-bottom: 8px; }}
  .enc .fac {{ font-weight: bold; font-size: 12px; letter-spacing: .5px; }}
  .enc .car {{ font-weight: bold; font-size: 11px; color: {_AZUL}; }}
  .enc .sub {{ font-size: 10px; color: #444; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  th, td {{ border: 1px solid #444; padding: 4px 6px; vertical-align: top;
           text-align: left; }}
  th {{ background: {_GRIS_ENC}; color: #1a1a1a; font-size: 9.5px;
       text-align: center; font-weight: bold; }}
  .c {{ text-align: center; }}
  .sem {{ font-weight: bold; white-space: nowrap; color: {_AZUL}; }}
  /* Evidencia fotográfica */
  .reg-evidencia {{ margin-top: 14px; page-break-inside: avoid; }}
  .reg-tit {{ font-weight: bold; font-size: 10px; color: {_AZUL};
             border-left: 3px solid {_AZUL}; padding-left: 6px; margin-bottom: 4px; }}
  .evidencia-tit {{ font-size: 8.5px; letter-spacing: .5px; color: #666;
                   text-align: center; margin-bottom: 4px; }}
  .img-grid {{ display: flex; flex-wrap: wrap; gap: 8px;
              justify-content: center; align-items: flex-start; }}
  .img-cell {{ display: flex; justify-content: center; }}
  .img-cell img {{ width: 100%; height: auto; max-height: 260px;
                  object-fit: contain; border: 1px solid #bbb; border-radius: 3px;
                  display: block; }}
  .seccion-fotos {{ margin-top: 18px; }}
  .seccion-fotos > h3 {{ font-size: 11px; color: {_AZUL};
                        border-bottom: 1px solid {_AZUL}; padding-bottom: 3px; }}
  /* Botón imprimir */
  .noprint {{ text-align: center; margin: 8px 0 14px; }}
  .btn {{ background: {_AZUL}; color: #fff; border: 0; padding: 9px 22px;
         font-size: 13px; border-radius: 4px; cursor: pointer; }}
  @media print {{
    body {{ padding: 0; }}
    .noprint {{ display: none !important; }}
  }}
</style></head><body>
<div class="noprint"><button class="btn" onclick="window.print()">🖨️ Imprimir / Guardar PDF</button></div>
<div class="doc">

  <div class="enc">
    <div class="fac">FACULTAD DE INGENIERÍA</div>
    <div class="car">INGENIERÍA BIOMÉDICA</div>
    <div class="sub">{escape(titulo)}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width:10%">Semana</th>
        <th style="width:15%">Equipo o proceso</th>
        <th style="width:19%">Problema identificado</th>
        <th style="width:18%">Solución sugerida</th>
        <th style="width:8%">¿Problema ya resuelto?</th>
        <th style="width:18%">Impacto esperado o beneficio real</th>
        <th style="width:12%">Observaciones</th>
      </tr>
    </thead>
    <tbody>
      {filas if filas else '<tr><td colspan="7" class="c">Sin registros para el filtro seleccionado.</td></tr>'}
    </tbody>
  </table>

  {f'<div class="seccion-fotos"><h3>Evidencia fotográfica</h3>{bloques_img}</div>' if bloques_img else ''}

</div></body></html>"""
