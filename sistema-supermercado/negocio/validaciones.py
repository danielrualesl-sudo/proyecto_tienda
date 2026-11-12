"""Validaciones reutilizables de tipos, rangos y campos obligatorios."""
import math
import re
from datetime import datetime

PATRON_CODIGO = re.compile(r"^[A-Z0-9][A-Z0-9\-]{1,14}$")


class ErrorValidacion(Exception):
    """Dato u operación que no cumple las reglas del negocio."""


def texto_obligatorio(valor, campo, max_len=60):
    texto = str(valor).strip()
    if not texto:
        raise ErrorValidacion(f"El campo '{campo}' es obligatorio.")
    if len(texto) > max_len:
        raise ErrorValidacion(f"El campo '{campo}' admite máximo {max_len} caracteres.")
    return texto


def codigo_producto(valor):
    texto = str(valor).strip().upper()
    if not texto:
        raise ErrorValidacion("El campo 'Código' es obligatorio.")
    if not PATRON_CODIGO.match(texto):
        raise ErrorValidacion("El código debe tener de 2 a 15 caracteres (letras, números o guion).")
    return texto


def _revisar_rango(numero, campo, minimo, maximo):
    if minimo is not None and numero < minimo:
        raise ErrorValidacion(f"'{campo}' no puede ser menor que {minimo}.")
    if maximo is not None and numero > maximo:
        raise ErrorValidacion(f"'{campo}' no puede ser mayor que {maximo}.")


def entero(valor, campo, minimo=None, maximo=None):
    texto = str(valor).strip()
    if not texto:
        raise ErrorValidacion(f"El campo '{campo}' es obligatorio.")
    try:
        numero = int(texto)
    except ValueError:
        raise ErrorValidacion(f"'{campo}' debe ser un número entero.") from None
    _revisar_rango(numero, campo, minimo, maximo)
    return numero


def decimal(valor, campo, minimo=None, maximo=None):
    texto = str(valor).strip().replace(",", ".")
    if not texto:
        raise ErrorValidacion(f"El campo '{campo}' es obligatorio.")
    try:
        numero = float(texto)
    except ValueError:
        raise ErrorValidacion(f"'{campo}' debe ser un número.") from None
    if not math.isfinite(numero):
        raise ErrorValidacion(f"'{campo}' no es un número válido.")
    numero = round(numero, 2)
    _revisar_rango(numero, campo, minimo, maximo)
    return numero


def fecha(valor, campo="Fecha"):
    try:
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ErrorValidacion(f"'{campo}' debe tener el formato AAAA-MM-DD (ej. 2026-11-30).") from None
