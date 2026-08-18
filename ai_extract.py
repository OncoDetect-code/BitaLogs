"""
Servicio de extracción de datos desde imágenes/PDF usando Gemini, para
BitaLogs. Lee un reporte/bitácora de una atención a equipo médico y
devuelve un dict con los campos del formulario "Nuevo registro" para que
el usuario los revise y edite antes de guardar.

Diseñado como capa de servicio independiente de la interfaz:
- No importa Streamlit.
- Recibe bytes de archivo, devuelve un dict con los campos de la atención.
- La clave de API se pasa como argumento (quien llama la obtiene de
  st.secrets). Es la MISMA clave de Gemini que usa ServiDox.
"""

from __future__ import annotations

import base64
import json
import re

# Campos que la IA intenta extraer (coinciden con el formulario de BitaLogs).
# No se pide semana/día (se derivan de la fecha) ni las imágenes.
CAMPOS_EXTRAIBLES = [
    "fecha", "hora_inicio", "hora_fin", "area", "equipo", "marca",
    "modelo", "serie", "tipo", "problema", "solucion", "resuelto",
    "impacto", "observaciones",
]

# Listas válidas para los campos de selección (deben coincidir con
# bitalogs.py). Se incluyen en el prompt para que la IA devuelva un valor
# exacto de la lista.
_AREAS = ("Hospitalización A", "Hospitalización B", "UCI A", "UCI B",
          "Sala Cuna", "UCIN", "Emergencia", "CEYE", "Laboratorio",
          "Quirófano 1", "Quirófano 2", "Quirófano 3", "Quirófano 4",
          "Maternidad", "Diagnóstico por imágenes",
          "Área de mantenimiento", "HDV La Lima", "Otra")
_TIPOS = ("Preventivo", "Correctivo", "Revisión y Diagnóstico",
          "Instalación", "Capacitación", "Otro")
_RESUELTO = ("Sí", "Parcial", "No")

_PROMPT = f"""Eres un asistente que transcribe bitácoras de atención a equipo médico
para una práctica profesional de Ingeniería Biomédica en un hospital.

Extrae la información del documento y devuélvela SOLO como un objeto JSON válido,
sin texto adicional, sin explicaciones, sin ```json. Usa exactamente estas claves:

- "fecha": la fecha de la atención en formato AAAA-MM-DD. Si dice "16-enero-2026"
  conviértela a "2026-01-16". Si no aparece, "".
- "hora_inicio": hora de inicio de la atención en formato HH:MM (24h). Si no aparece, "".
- "hora_fin": hora de finalización en formato HH:MM (24h). Si no aparece, "".
- "area": el área o sala del hospital. Devuelve EXACTAMENTE uno de estos valores:
  {", ".join(_AREAS)}. Si no puedes determinarla con seguridad, usa "".
- "equipo": el NOMBRE del equipo atendido (ej. "Lámpara cielítica").
- "marca": la MARCA del equipo (ej. "Dräger"). Si no aparece, "".
- "modelo": el MODELO del equipo (ej. "Polaris 100"). Si no aparece, "".
- "serie": el número de SERIE del equipo. Si no aparece, "".
- "tipo": el tipo de mantenimiento. Devuelve EXACTAMENTE uno de estos valores:
  {", ".join(_TIPOS)}. Si no puedes determinarlo, usa "".
- "problema": el problema identificado o el motivo de la atención, transcrito.
- "solucion": la solución sugerida o el trabajo realizado, transcrito.
- "resuelto": si el problema quedó resuelto. Devuelve EXACTAMENTE uno de:
  {", ".join(_RESUELTO)}. Si no puedes determinarlo, usa "".
- "impacto": el impacto esperado o beneficio real de la atención, transcrito.
- "observaciones": observaciones adicionales, transcritas.

Reglas:
- Transcribe la letra manuscrita lo mejor posible, respetando la ortografía correcta del español.
- Si un campo no aparece o no es legible, usa "" (cadena vacía). No inventes datos.
- Para "area", "tipo" y "resuelto" devuelve solo un valor EXACTO de las listas dadas, o "".
- Responde ÚNICAMENTE con el JSON."""


def _extraer_json(texto: str) -> dict:
    """Extrae el primer objeto JSON del texto de respuesta del modelo."""
    limpio = texto.strip()
    limpio = re.sub(r"^```(?:json)?", "", limpio).strip()
    limpio = re.sub(r"```$", "", limpio).strip()
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", limpio, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise ValueError("El modelo no devolvió un JSON reconocible.")


def _normalizar(datos: dict) -> dict:
    """Asegura que estén todas las claves, limpia valores y valida que
    area/tipo/resuelto sean de las listas permitidas (si no, "")."""
    resultado = {}
    for campo in CAMPOS_EXTRAIBLES:
        val = datos.get(campo, "")
        resultado[campo] = "" if val is None else str(val).strip()
    # Validar campos de lista: si la IA devolvió algo fuera de la lista,
    # se deja vacío para que el usuario lo elija manualmente.
    if resultado["area"] not in _AREAS:
        resultado["area"] = ""
    if resultado["tipo"] not in _TIPOS:
        resultado["tipo"] = ""
    if resultado["resuelto"] not in _RESUELTO:
        resultado["resuelto"] = ""
    return resultado


def extraer_de_imagen(imagen_bytes: bytes, mime_type: str, api_key: str,
                      modelo: str = "gemini-3.6-flash") -> dict:
    """
    Envía una imagen o PDF a Gemini y devuelve un dict con los campos de la
    atención para pre-rellenar el formulario de BitaLogs.

    imagen_bytes: contenido del archivo.
    mime_type: "image/jpeg", "image/png", "image/webp" o "application/pdf".
    api_key: clave de API de Gemini (la misma de ServiDox).
    """
    import requests

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{modelo}:generateContent")
    b64 = base64.b64encode(imagen_bytes).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {"text": _PROMPT},
                {"inline_data": {"mime_type": mime_type, "data": b64}},
            ]
        }],
        "generationConfig": {"maxOutputTokens": 2048},
    }
    resp = requests.post(url, params={"key": api_key},
                         json=payload, timeout=60)

    if resp.status_code != 200:
        detalle = ""
        try:
            detalle = resp.json().get("error", {}).get("message", "")
        except Exception:
            detalle = resp.text[:200]
        raise RuntimeError(f"Error de Gemini ({resp.status_code}): {detalle}")

    data = resp.json()
    try:
        texto = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError("Gemini no devolvió contenido. "
                           "Puede ser un límite de uso o un archivo no legible.")

    return _normalizar(_extraer_json(texto))


def preparar_archivo(nombre: str, contenido: bytes) -> tuple[bytes, str]:
    """
    Determina el mime_type a partir del nombre. Devuelve (bytes, mime_type).
    Lanza ValueError si el tipo no es soportado.
    """
    nombre_low = nombre.lower()
    if nombre_low.endswith((".jpg", ".jpeg")):
        return contenido, "image/jpeg"
    if nombre_low.endswith(".png"):
        return contenido, "image/png"
    if nombre_low.endswith(".webp"):
        return contenido, "image/webp"
    if nombre_low.endswith(".pdf"):
        return contenido, "application/pdf"
    raise ValueError(f"Tipo de archivo no soportado: {nombre}. "
                     "Usa JPG, PNG, WEBP o PDF.")
