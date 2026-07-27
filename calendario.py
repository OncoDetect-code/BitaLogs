"""
Calendario de la práctica profesional — BitaLogs.

Define las 10 semanas de la práctica (lunes a viernes) y la lógica para:
  - mapear una fecha a su Semana N y Día N
  - calcular horas acumuladas asumiendo 8 h/día laborable (L-V)
  - listar las semanas y sus rangos para los filtros

Reglas actuales (modificables en un solo lugar):
  - Inicio: lunes 20 de julio de 2026 (Semana 1)
  - Fin:    viernes 25 de septiembre de 2026 (Semana 10, Día 5)
  - Jornada: 8 horas por día laborable, de lunes a viernes
  - Feriados: por ahora NO se descuentan (HORAS_POR_DIA fijo L-V).
    Si más adelante quieres descontarlos, agrega las fechas a FERIADOS
    y pon DESCONTAR_FERIADOS = True.
"""

from datetime import date, timedelta

# ----------------------------------------------------------------- Parámetros
INICIO_PRACTICA = date(2026, 7, 20)   # lunes, Semana 1
TOTAL_SEMANAS = 10
HORAS_POR_DIA = 8
DIAS_LABORABLES = 5                    # lunes(0) .. viernes(4)

# Feriados de Honduras dentro del período (informativo por ahora).
# Ejemplo: Día de la Independencia. NO se descuentan mientras
# DESCONTAR_FERIADOS sea False.
FERIADOS = {
    date(2026, 9, 15): "Día de la Independencia",
}
DESCONTAR_FERIADOS = False

# Nombres de días en español
_DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
            "Sábado", "Domingo"]
_MESES_ES = ["", "ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt(d: date) -> str:
    """Fecha corta legible: '20 jul 2026'."""
    return f"{d.day} {_MESES_ES[d.month]} {d.year}"


def lunes_de_semana(n: int) -> date:
    """Fecha del lunes de la Semana n (1-indexado)."""
    return INICIO_PRACTICA + timedelta(weeks=n - 1)


def viernes_de_semana(n: int) -> date:
    """Fecha del viernes de la Semana n."""
    return lunes_de_semana(n) + timedelta(days=4)


def rango_semana(n: int) -> tuple[date, date]:
    """(lunes, viernes) de la Semana n."""
    return lunes_de_semana(n), viernes_de_semana(n)


def etiqueta_semana(n: int) -> str:
    """'Semana 1 (20 jul - 24 jul 2026)'."""
    lun, vie = rango_semana(n)
    return f"Semana {n} ({_fmt(lun)} - {_fmt(vie)})"


def es_dia_laborable(d: date) -> bool:
    """True si es lunes-viernes (y, si se activara, no feriado)."""
    if d.weekday() >= DIAS_LABORABLES:
        return False
    if DESCONTAR_FERIADOS and d in FERIADOS:
        return False
    return True


def semana_de_fecha(d: date):
    """
    Devuelve el número de semana (1..10) al que pertenece la fecha,
    o None si la fecha cae fuera del período de práctica.
    """
    if d < INICIO_PRACTICA:
        return None
    delta_dias = (d - INICIO_PRACTICA).days
    n = delta_dias // 7 + 1
    if 1 <= n <= TOTAL_SEMANAS:
        return n
    return None


def dia_de_semana_num(d: date):
    """
    Día de la semana laboral como número 1..5 (Lun=1 .. Vie=5),
    o None si es fin de semana o fuera de período.
    """
    if semana_de_fecha(d) is None:
        return None
    wd = d.weekday()
    if wd >= DIAS_LABORABLES:
        return None
    return wd + 1


def etiqueta_dia(d: date) -> str:
    """'Día 1 · Lunes 20 jul' relativo a su semana."""
    dn = dia_de_semana_num(d)
    nombre = _DIAS_ES[d.weekday()]
    if dn is None:
        return f"{nombre} {_fmt(d)}"
    return f"Día {dn} · {nombre} {_fmt(d)}"


def fecha_de_semana_dia(semana: int, dia: int) -> date:
    """Fecha exacta dada Semana n (1..10) y Día d (1..5)."""
    return lunes_de_semana(semana) + timedelta(days=dia - 1)


def horas_hasta(d: date) -> int:
    """
    Horas acumuladas de práctica DESDE el inicio HASTA la fecha d
    (inclusive), contando solo días laborables a HORAS_POR_DIA cada uno.
    """
    if d < INICIO_PRACTICA:
        return 0
    fin = min(d, viernes_de_semana(TOTAL_SEMANAS))
    dias = 0
    cur = INICIO_PRACTICA
    while cur <= fin:
        if es_dia_laborable(cur):
            dias += 1
        cur += timedelta(days=1)
    return dias * HORAS_POR_DIA


def horas_totales_practica() -> int:
    """Horas totales al terminar la práctica completa."""
    return horas_hasta(viernes_de_semana(TOTAL_SEMANAS))


def horas_por_semana_acumuladas() -> list[dict]:
    """
    Lista con, por cada semana: número, etiqueta, horas de esa semana
    y horas acumuladas al cierre de esa semana. Útil para gráficas.
    """
    filas = []
    for n in range(1, TOTAL_SEMANAS + 1):
        lun, vie = rango_semana(n)
        dias_lab = sum(
            1 for i in range(5) if es_dia_laborable(lun + timedelta(days=i)))
        horas_semana = dias_lab * HORAS_POR_DIA
        filas.append({
            "semana": n,
            "etiqueta": f"Semana {n}",
            "rango": f"{_fmt(lun)} - {_fmt(vie)}",
            "horas_semana": horas_semana,
            "horas_acumuladas": horas_hasta(vie),
        })
    return filas


def lista_semanas() -> list[int]:
    """[1, 2, ..., 10]."""
    return list(range(1, TOTAL_SEMANAS + 1))


def fin_practica() -> date:
    return viernes_de_semana(TOTAL_SEMANAS)


if __name__ == "__main__":
    # Verificación rápida del calendario
    print("Inicio:", _fmt(INICIO_PRACTICA), _DIAS_ES[INICIO_PRACTICA.weekday()])
    print("Fin:   ", _fmt(fin_practica()), _DIAS_ES[fin_practica().weekday()])
    print("Horas totales:", horas_totales_practica())
    print()
    for f in horas_por_semana_acumuladas():
        print(f"S{f['semana']:>2}  {f['rango']:<26}  "
              f"{f['horas_semana']} h  | acum {f['horas_acumuladas']} h")
