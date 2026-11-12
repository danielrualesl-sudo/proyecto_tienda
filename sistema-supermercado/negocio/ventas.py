"""Reglas de negocio de carrito, cobro, facturación, devoluciones y reportes."""
from datetime import datetime

from negocio import caja, inventario
from negocio import validaciones as v
from persistencia import gestor_json

IMPUESTO_PORCENTAJE = 19.0   # IVA configurado
DESCUENTO_MAXIMO = 50.0      # % máximo de descuento permitido


def formato_factura(numero):
    return f"F-{int(numero):04d}"


# ---------------------------------------------------------------- carrito
def agregar_al_carrito(estado, carrito, codigo, cantidad):
    """carrito = {codigo: cantidad}. Suma la cantidad si ya estaba."""
    cantidad = v.entero(cantidad, "Cantidad", minimo=1)
    producto = inventario.obtener_producto(estado, codigo)
    if not producto["activo"]:
        raise v.ErrorValidacion(f"El producto '{producto['codigo']}' está desactivado.")
    nueva = carrito.get(producto["codigo"], 0) + cantidad
    if nueva > producto["stock"]:
        raise v.ErrorValidacion(
            f"Stock insuficiente de '{producto['nombre']}': disponible {producto['stock']}, "
            f"en carrito sería {nueva}."
        )
    carrito[producto["codigo"]] = nueva


def modificar_cantidad(estado, carrito, codigo, cantidad):
    codigo = str(codigo).strip().upper()
    if codigo not in carrito:
        raise v.ErrorValidacion("Ese producto no está en el carrito.")
    cantidad = v.entero(cantidad, "Cantidad", minimo=1)
    producto = inventario.obtener_producto(estado, codigo)
    if cantidad > producto["stock"]:
        raise v.ErrorValidacion(
            f"Stock insuficiente de '{producto['nombre']}': disponible {producto['stock']}."
        )
    carrito[codigo] = cantidad


def retirar_del_carrito(carrito, codigo):
    codigo = str(codigo).strip().upper()
    if codigo not in carrito:
        raise v.ErrorValidacion("Ese producto no está en el carrito.")
    del carrito[codigo]


def calcular_totales(estado, carrito, descuento_pct=0):
    """Subtotales, descuento, impuestos y total del carrito."""
    descuento_pct = v.decimal(descuento_pct if str(descuento_pct).strip() else 0,
                              "Descuento (%)", minimo=0, maximo=DESCUENTO_MAXIMO)
    lineas = []
    for codigo, cantidad in carrito.items():
        producto = inventario.obtener_producto(estado, codigo)
        lineas.append({
            "codigo": codigo, "nombre": producto["nombre"], "cantidad": cantidad,
            "precio_unitario": producto["precio_venta"],
            "subtotal": round(cantidad * producto["precio_venta"], 2), "devuelto": 0,
        })
    subtotal = round(sum(l["subtotal"] for l in lineas), 2)
    descuento = round(subtotal * descuento_pct / 100, 2)
    base = round(subtotal - descuento, 2)
    impuestos = round(base * IMPUESTO_PORCENTAJE / 100, 2)
    return {
        "lineas": lineas, "subtotal": subtotal,
        "descuento_pct": descuento_pct, "descuento": descuento,
        "impuesto_pct": IMPUESTO_PORCENTAJE, "impuestos": impuestos,
        "total": round(base + impuestos, 2),
    }


# ---------------------------------------------------------------- cobro
def procesar_venta(estado, carrito, descuento_pct, pago):
    """Cobra el carrito. Genera factura, descuenta stock y registra en caja.

    Todo ocurre en una sola transacción: si algo falla no se genera factura,
    no baja el stock y no se toca la caja.
    """
    if not carrito:
        raise v.ErrorValidacion("El carrito está vacío.")
    pago = v.decimal(pago, "Pago recibido", minimo=0)
    items = dict(carrito)

    def operacion(copia):
        totales = calcular_totales(copia, items, descuento_pct)
        if pago < totales["total"]:
            raise v.ErrorValidacion(
                f"Pago insuficiente: total {totales['total']:.2f}, recibido {pago:.2f}."
            )
        numero = max((f["numero"] for f in copia["ventas"]), default=0) + 1
        for linea in totales["lineas"]:
            producto = inventario.obtener_producto(copia, linea["codigo"])
            if not producto["activo"]:
                raise v.ErrorValidacion(f"El producto '{producto['codigo']}' está desactivado.")
            inventario.aplicar_movimiento_stock(
                producto, "venta", linea["cantidad"], f"Factura {formato_factura(numero)}")
        factura = {
            "numero": numero,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "detalle": totales["lineas"],
            "subtotal": totales["subtotal"],
            "descuento_pct": totales["descuento_pct"], "descuento": totales["descuento"],
            "impuesto_pct": totales["impuesto_pct"], "impuestos": totales["impuestos"],
            "total": totales["total"], "pago": pago,
            "cambio": round(pago - totales["total"], 2),
            "estado": "emitida", "devoluciones": [],
        }
        copia["ventas"].append(factura)
        caja.anotar_movimiento(copia, "venta", factura["total"], f"Factura {formato_factura(numero)}")
        return factura

    return gestor_json.transaccion(estado, operacion)


# ---------------------------------------------------------------- facturas y devoluciones
def buscar_factura(estado, numero):
    for factura in estado["ventas"]:
        if factura["numero"] == numero:
            return factura
    return None


def obtener_factura(estado, numero):
    numero = v.entero(numero, "Número de factura", minimo=1)
    factura = buscar_factura(estado, numero)
    if factura is None:
        raise v.ErrorValidacion(f"No existe la factura {formato_factura(numero)}.")
    return factura


def registrar_devolucion(estado, numero, items):
    """items = {codigo: cantidad}. Devuelve el valor reembolsado."""
    numero = v.entero(numero, "Número de factura", minimo=1)
    if not items:
        raise v.ErrorValidacion("Indique al menos un producto a devolver.")

    def operacion(copia):
        factura = obtener_factura(copia, numero)
        if factura["estado"] == "devuelta":
            raise v.ErrorValidacion("Esa factura ya fue devuelta por completo.")
        lineas = {l["codigo"]: l for l in factura["detalle"]}
        reembolso = 0.0
        devueltos = {}
        for codigo, cantidad in items.items():
            codigo = str(codigo).strip().upper()
            linea = lineas.get(codigo)
            if linea is None:
                raise v.ErrorValidacion(f"El producto '{codigo}' no pertenece a esa factura.")
            cantidad = v.entero(cantidad, "Cantidad a devolver", minimo=1)
            disponible = linea["cantidad"] - linea.get("devuelto", 0)
            if cantidad > disponible:
                raise v.ErrorValidacion(
                    f"Solo se pueden devolver {disponible} unidad(es) de '{codigo}'."
                )
            producto = inventario.buscar_producto(copia, codigo)
            if producto is not None:
                inventario.aplicar_movimiento_stock(
                    producto, "devolucion", cantidad, f"Devolución {formato_factura(numero)}")
            linea["devuelto"] = linea.get("devuelto", 0) + cantidad
            devueltos[codigo] = cantidad
            factor = (1 - factura["descuento_pct"] / 100) * (1 + factura["impuesto_pct"] / 100)
            reembolso += cantidad * linea["precio_unitario"] * factor
        reembolso = round(reembolso, 2)
        factura["devoluciones"].append({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": devueltos, "monto": reembolso,
        })
        completa = all(l["devuelto"] == l["cantidad"] for l in factura["detalle"])
        factura["estado"] = "devuelta" if completa else "devolucion parcial"
        caja.anotar_movimiento(copia, "devolucion", reembolso,
                               f"Devolución {formato_factura(numero)}")
        return reembolso

    return gestor_json.transaccion(estado, operacion)


# ---------------------------------------------------------------- reportes
def reporte_ventas(estado, desde, hasta):
    """Ventas netas (descontando devoluciones) entre dos fechas inclusive."""
    d1, d2 = v.fecha(desde, "Desde"), v.fecha(hasta, "Hasta")
    if d1 > d2:
        raise v.ErrorValidacion("La fecha inicial no puede ser posterior a la final.")
    facturas, unidades = [], {}
    ingresos = 0.0
    for factura in estado["ventas"]:
        dia = datetime.strptime(factura["fecha"][:10], "%Y-%m-%d").date()
        if not d1 <= dia <= d2:
            continue
        facturas.append(factura)
        ingresos += factura["total"] - sum(d["monto"] for d in factura["devoluciones"])
        for linea in factura["detalle"]:
            neto = linea["cantidad"] - linea.get("devuelto", 0)
            datos = unidades.setdefault(linea["codigo"], {"nombre": linea["nombre"], "unidades": 0})
            datos["unidades"] += neto
    ranking = sorted(
        ({"codigo": c, **d} for c, d in unidades.items() if d["unidades"] > 0),
        key=lambda x: (-x["unidades"], x["codigo"]),
    )
    return {
        "facturas": facturas, "num_facturas": len(facturas),
        "ingresos": round(ingresos, 2),
        "unidades": sum(d["unidades"] for d in unidades.values()),
        "mas_vendidos": ranking[:10],
    }
