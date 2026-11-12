"""Reglas de negocio de la caja: apertura, movimientos y cierre."""
from datetime import datetime

from negocio import validaciones as v
from persistencia import gestor_json

TIPOS_SUMAN = {"venta", "ingreso"}
TIPOS_RESTAN = {"devolucion", "egreso"}


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sesion_abierta(estado):
    """Devuelve la sesión de caja abierta o None."""
    for sesion in reversed(estado["caja"]):
        if sesion["estado"] == "abierta":
            return sesion
    return None


def efectivo_esperado(sesion):
    """Saldo inicial + ventas + ingresos - devoluciones - egresos."""
    total = sesion["saldo_inicial"]
    for mov in sesion["movimientos"]:
        total += mov["monto"] if mov["tipo"] in TIPOS_SUMAN else -mov["monto"]
    return round(total, 2)


def resumen_sesion(sesion):
    """Totales por tipo de movimiento de una sesión."""
    resumen = {tipo: 0.0 for tipo in sorted(TIPOS_SUMAN | TIPOS_RESTAN)}
    for mov in sesion["movimientos"]:
        resumen[mov["tipo"]] = round(resumen[mov["tipo"]] + mov["monto"], 2)
    return resumen


def anotar_movimiento(estado, tipo, monto, descripcion):
    """Agrega un movimiento a la sesión abierta (en memoria, sin guardar).

    La usan ventas y devoluciones dentro de su propia transacción.
    """
    if tipo not in TIPOS_SUMAN | TIPOS_RESTAN:
        raise v.ErrorValidacion(f"Tipo de movimiento de caja desconocido: '{tipo}'.")
    sesion = sesion_abierta(estado)
    if sesion is None:
        raise v.ErrorValidacion("No hay una caja abierta. Abra la caja antes de operar.")
    if monto <= 0:
        raise v.ErrorValidacion("El monto del movimiento debe ser mayor que cero.")
    sesion["movimientos"].append(
        {"fecha": _ahora(), "tipo": tipo, "monto": round(monto, 2), "descripcion": descripcion}
    )


def abrir_caja(estado, saldo_inicial):
    saldo = v.decimal(saldo_inicial, "Saldo inicial", minimo=0)

    def operacion(copia):
        if sesion_abierta(copia) is not None:
            raise v.ErrorValidacion("Ya hay una caja abierta; ciérrela antes de abrir otra.")
        siguiente = max((s["id"] for s in copia["caja"]), default=0) + 1
        sesion = {
            "id": siguiente, "estado": "abierta", "apertura": _ahora(),
            "saldo_inicial": saldo, "movimientos": [],
            "cierre": None, "valor_esperado": None,
            "valor_declarado": None, "diferencia": None,
        }
        copia["caja"].append(sesion)
        return sesion

    return gestor_json.transaccion(estado, operacion)


def registrar_movimiento_manual(estado, tipo, monto, descripcion):
    """Ingreso o egreso de efectivo (por ejemplo, pago a un proveedor)."""
    if tipo not in ("ingreso", "egreso"):
        raise v.ErrorValidacion("El tipo debe ser 'ingreso' o 'egreso'.")
    monto = v.decimal(monto, "Monto", minimo=0)
    descripcion = v.texto_obligatorio(descripcion, "Descripción", 80)

    def operacion(copia):
        sesion = sesion_abierta(copia)
        if sesion is not None and tipo == "egreso" and monto > efectivo_esperado(sesion):
            raise v.ErrorValidacion("El egreso supera el efectivo disponible en caja.")
        anotar_movimiento(copia, tipo, monto, descripcion)

    return gestor_json.transaccion(estado, operacion)


def cerrar_caja(estado, valor_declarado):
    declarado = v.decimal(valor_declarado, "Efectivo declarado", minimo=0)

    def operacion(copia):
        sesion = sesion_abierta(copia)
        if sesion is None:
            raise v.ErrorValidacion("No hay una caja abierta para cerrar.")
        esperado = efectivo_esperado(sesion)
        sesion.update({
            "estado": "cerrada", "cierre": _ahora(),
            "valor_esperado": esperado, "valor_declarado": declarado,
            "diferencia": round(declarado - esperado, 2),
        })
        return sesion

    return gestor_json.transaccion(estado, operacion)
