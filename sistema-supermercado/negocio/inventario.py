"""Reglas de negocio del catálogo y del inventario."""
from datetime import datetime

from negocio import validaciones as v
from persistencia import gestor_json

SUMAN = {"entrada", "devolucion"}
RESTAN = {"salida", "venta"}
MAX_MOVIMIENTOS_GUARDADOS = 50


def buscar_producto(estado, codigo):
    codigo = str(codigo).strip().upper()
    for producto in estado["productos"]:
        if producto["codigo"] == codigo:
            return producto
    return None


def obtener_producto(estado, codigo):
    producto = buscar_producto(estado, codigo)
    if producto is None:
        raise v.ErrorValidacion(f"No existe un producto con el código '{str(codigo).strip().upper()}'.")
    return producto


def listar_productos(estado, solo_activos=True):
    return [p for p in estado["productos"] if p["activo"] or not solo_activos]


def buscar_productos(estado, texto="", solo_activos=True):
    texto = str(texto).strip().lower()
    return [
        p for p in listar_productos(estado, solo_activos)
        if not texto or texto in p["codigo"].lower()
        or texto in p["nombre"].lower() or texto in p["categoria"].lower()
    ]


def productos_con_alerta(estado):
    """Productos activos con stock menor o igual al mínimo."""
    return [p for p in listar_productos(estado) if p["stock"] <= p["stock_minimo"]]


def _validar_datos(datos, incluir_stock):
    limpio = {
        "nombre": v.texto_obligatorio(datos.get("nombre", ""), "Nombre"),
        "categoria": v.texto_obligatorio(datos.get("categoria", ""), "Categoría", 40),
        "precio_compra": v.decimal(datos.get("precio_compra", ""), "Precio de compra", minimo=0),
        "precio_venta": v.decimal(datos.get("precio_venta", ""), "Precio de venta", minimo=0),
        "stock_minimo": v.entero(datos.get("stock_minimo", ""), "Stock mínimo", minimo=0),
    }
    if limpio["precio_venta"] <= 0:
        raise v.ErrorValidacion("El precio de venta debe ser mayor que cero.")
    if incluir_stock:
        limpio["stock"] = v.entero(datos.get("stock", ""), "Stock", minimo=0)
    return limpio


def crear_producto(estado, datos):
    codigo = v.codigo_producto(datos.get("codigo", ""))
    limpio = _validar_datos(datos, incluir_stock=True)

    def operacion(copia):
        if buscar_producto(copia, codigo) is not None:
            raise v.ErrorValidacion(f"Ya existe un producto con el código '{codigo}'.")
        producto = {"codigo": codigo, **limpio, "activo": True, "movimientos": []}
        copia["productos"].append(producto)
        return producto

    return gestor_json.transaccion(estado, operacion)


def editar_producto(estado, codigo, datos):
    """Edita datos del producto. El stock solo cambia con movimientos."""
    limpio = _validar_datos(datos, incluir_stock=False)

    def operacion(copia):
        producto = obtener_producto(copia, codigo)
        producto.update(limpio)
        return producto

    return gestor_json.transaccion(estado, operacion)


def cambiar_estado_producto(estado, codigo, activo):
    def operacion(copia):
        producto = obtener_producto(copia, codigo)
        producto["activo"] = bool(activo)
        return producto

    return gestor_json.transaccion(estado, operacion)


def aplicar_movimiento_stock(producto, tipo, cantidad, motivo=""):
    """Modifica el stock en memoria (sin guardar). La usan inventario y ventas."""
    if tipo in SUMAN:
        nuevo = producto["stock"] + cantidad
    elif tipo in RESTAN:
        nuevo = producto["stock"] - cantidad
        if nuevo < 0:
            raise v.ErrorValidacion(
                f"Stock insuficiente de '{producto['nombre']}': "
                f"disponible {producto['stock']}, solicitado {cantidad}."
            )
    else:
        raise v.ErrorValidacion(f"Tipo de movimiento desconocido: '{tipo}'.")
    producto["stock"] = nuevo
    historial = producto.setdefault("movimientos", [])
    historial.append({
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo": tipo, "cantidad": cantidad, "motivo": motivo,
    })
    producto["movimientos"] = historial[-MAX_MOVIMIENTOS_GUARDADOS:]


def registrar_movimiento(estado, codigo, tipo, cantidad, motivo=""):
    """Registra una entrada o salida manual de inventario."""
    if tipo not in ("entrada", "salida"):
        raise v.ErrorValidacion("El tipo debe ser 'entrada' o 'salida'.")
    cantidad = v.entero(cantidad, "Cantidad", minimo=1)
    motivo = str(motivo).strip()

    def operacion(copia):
        producto = obtener_producto(copia, codigo)
        if not producto["activo"]:
            raise v.ErrorValidacion("El producto está desactivado; reactívelo antes de moverlo.")
        aplicar_movimiento_stock(producto, tipo, cantidad, motivo or tipo.capitalize())
        return producto

    return gestor_json.transaccion(estado, operacion)
