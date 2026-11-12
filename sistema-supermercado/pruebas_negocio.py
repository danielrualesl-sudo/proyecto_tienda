"""Pruebas automáticas de la lógica de negocio (sin interfaz).

Ejecutar:  python pruebas_negocio.py
Usa una carpeta temporal: NO toca los archivos de la carpeta datos/.
Cada caso imprime: entrada, resultado esperado, resultado obtenido y OK/FALLO.
"""
import copy
import json
import tempfile
from pathlib import Path

from negocio import caja, inventario, ventas
from negocio.validaciones import ErrorValidacion
from persistencia import gestor_json

RESULTADOS = []


def caso(numero, nombre, esperado, accion):
    """accion() devuelve el resultado obtenido (texto) o lanza una excepción."""
    try:
        obtenido = accion()
    except ErrorValidacion as error:
        obtenido = f"Rechazado: {error}"
    except gestor_json.ErrorPersistencia as error:
        obtenido = f"Rechazado (archivo): {error}"
    ok = esperado in str(obtenido)
    RESULTADOS.append(ok)
    print(f"[{'OK' if ok else 'FALLO'}] C{numero:02d} {nombre}\n"
          f"       esperado: {esperado}\n       obtenido: {obtenido}")


def producto(codigo="A1", stock=10, venta=1000.0):
    return {"codigo": codigo, "nombre": f"Producto {codigo}", "categoria": "Prueba",
            "precio_compra": "600", "precio_venta": str(venta), "stock": str(stock),
            "stock_minimo": "3"}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        gestor_json.DIR_DATOS = Path(tmp)
        estado, _ = gestor_json.cargar_estado()
        n = 0

        def c(nombre, esperado, accion):
            nonlocal n
            n += 1
            caso(n, nombre, esperado, accion)

        factura_anterior = [{
            "numero_factura": "FAC-0001",
            "fecha": "2026-11-08 10:30:00",
            "detalle": [{
                "codigo": "P001", "nombre": "Arroz", "cantidad": 2,
                "precio_unitario": 4000, "subtotal": 8000,
            }],
            "descuento": 0, "impuestos": 0, "total": 8000, "estado": "completada",
        }]
        (Path(tmp) / "ventas.json").write_text(
            json.dumps(factura_anterior), encoding="utf-8")
        estado_anterior, _ = gestor_json.cargar_estado()
        c("Migrar factura anterior", "numero=1 devuelto=0 devoluciones=0",
          lambda: f"numero={estado_anterior['ventas'][0]['numero']} "
                  f"devuelto={estado_anterior['ventas'][0]['detalle'][0]['devuelto']} "
                  f"devoluciones={len(estado_anterior['ventas'][0]['devoluciones'])}")
        gestor_json.guardar_estado(estado)

        c("Registrar producto válido", "stock=10",
          lambda: f"stock={inventario.crear_producto(estado, producto())['stock']}")
        c("Registrar código repetido", "Ya existe",
          lambda: inventario.crear_producto(estado, producto()))
        c("El rechazo no altera datos", "productos=1", lambda: f"productos={len(estado['productos'])}")
        c("Precio de venta negativo", "no puede ser menor",
          lambda: inventario.crear_producto(estado, {**producto("A2"), "precio_venta": "-5"}))
        c("Nombre vacío", "obligatorio",
          lambda: inventario.crear_producto(estado, {**producto("A3"), "nombre": "  "}))
        c("Stock con texto", "número entero",
          lambda: inventario.crear_producto(estado, {**producto("A4"), "stock": "abc"}))
        c("Entrada de inventario +5", "stock=15",
          lambda: f"stock={inventario.registrar_movimiento(estado, 'A1', 'entrada', 5, 'Compra')['stock']}")
        c("Salida mayor al stock", "Stock insuficiente",
          lambda: inventario.registrar_movimiento(estado, "A1", "salida", 99))
        c("Salida -12 y alerta de stock mínimo", "stock=3 alerta=True",
          lambda: (lambda p: f"stock={p['stock']} alerta={p in inventario.productos_con_alerta(estado)}")(
              inventario.registrar_movimiento(estado, "A1", "salida", 12, "Merma")))
        inventario.registrar_movimiento(estado, "A1", "entrada", 7, "Reposición")  # stock = 10
        c("Vender sin caja abierta", "No hay una caja abierta",
          lambda: (ventas.agregar_al_carrito(estado, carrito := {}, "A1", 1),
                   ventas.procesar_venta(estado, carrito, 0, 5000))[1])
        c("Abrir caja con 50000", "saldo=50000.0",
          lambda: f"saldo={caja.abrir_caja(estado, 50000)['saldo_inicial']}")
        c("Abrir segunda caja", "Ya hay una caja abierta", lambda: caja.abrir_caja(estado, 10))

        carrito = {}
        ventas.agregar_al_carrito(estado, carrito, "A1", 2)
        c("Venta exitosa (2 u., IVA 19%)", "total=2380.0 cambio=620.0 stock=8",
          lambda: (lambda f: f"total={f['total']} cambio={f['cambio']} "
                             f"stock={inventario.buscar_producto(estado, 'A1')['stock']}")(
              ventas.procesar_venta(estado, carrito, 0, 3000)))
        c("Factura consecutiva", "F-0001", lambda: ventas.formato_factura(estado["ventas"][0]["numero"]))

        c("Vender más que el stock", "Stock insuficiente",
          lambda: ventas.agregar_al_carrito(estado, {}, "A1", 50))
        c("Sin factura ni cambio de stock tras el rechazo", "facturas=1 stock=8",
          lambda: f"facturas={len(estado['ventas'])} stock={inventario.buscar_producto(estado, 'A1')['stock']}")
        c("Cantidad inválida (0)", "no puede ser menor",
          lambda: ventas.agregar_al_carrito(estado, {}, "A1", 0))
        c("Cantidad inválida (texto)", "número entero",
          lambda: ventas.agregar_al_carrito(estado, {}, "A1", "x"))
        c("Pago insuficiente", "Pago insuficiente",
          lambda: ventas.procesar_venta(estado, {"A1": 1}, 0, 100))
        c("Descuento 10% + IVA", "total=1071.0",
          lambda: f"total={ventas.calcular_totales(estado, {'A1': 1}, 10)['total']}")
        c("Descuento sobre el máximo", "no puede ser mayor",
          lambda: ventas.calcular_totales(estado, {'A1': 1}, 90))
        ventas.procesar_venta(estado, {"A1": 1}, 10, 2000)  # factura 2, total 1071

        c("Devolución parcial (1 u. de factura 1)", "reembolso=1190.0 estado=devolucion parcial stock=8",
          lambda: (lambda r: f"reembolso={r} estado={ventas.buscar_factura(estado, 1)['estado']} "
                             f"stock={inventario.buscar_producto(estado, 'A1')['stock']}")(
              ventas.registrar_devolucion(estado, 1, {"A1": 1})))
        c("Devolver más de lo vendido", "Solo se pueden devolver 1",
          lambda: ventas.registrar_devolucion(estado, 1, {"A1": 5}))
        c("Factura inexistente", "No existe la factura",
          lambda: ventas.registrar_devolucion(estado, 99, {"A1": 1}))

        # Falla de escritura: el estado en memoria no debe cambiar
        original = gestor_json.guardar_estado
        antes = copy.deepcopy(estado)

        def guardar_falla(_):
            raise gestor_json.ErrorPersistencia("disco lleno (simulado)")

        gestor_json.guardar_estado = guardar_falla
        c("Falla al guardar una venta", "Rechazado (archivo)",
          lambda: ventas.procesar_venta(estado, {"A1": 1}, 0, 5000))
        gestor_json.guardar_estado = original
        c("Tras la falla, datos intactos", "iguales=True", lambda: f"iguales={estado == antes}")

        c("Persistencia: recargar desde disco", "iguales=True",
          lambda: f"iguales={gestor_json.cargar_estado()[0] == estado}")
        c("Reporte por fechas (hoy)", "facturas=2 unidades=2 ingresos=2261.0",
          lambda: (lambda r: f"facturas={r['num_facturas']} unidades={r['unidades']} ingresos={r['ingresos']}")(
              ventas.reporte_ventas(estado, "2000-01-01", "2999-12-31")))
        c("Reporte con fecha inválida", "AAAA-MM-DD", lambda: ventas.reporte_ventas(estado, "31/12/2026", "2999-12-31"))

        # Caja: 50000 + 2380 + 1071 - 1190 = 52261
        c("Cierre con efectivo menor", "esperado=52261.0 diferencia=-261.0",
          lambda: (lambda s: f"esperado={s['valor_esperado']} diferencia={s['diferencia']}")(
              caja.cerrar_caja(estado, 52000)))
        c("Cerrar sin caja abierta", "No hay una caja abierta", lambda: caja.cerrar_caja(estado, 10))

        # Archivo dañado
        (Path(tmp) / "productos.json").write_text("{ no es json", encoding="utf-8")
        c("Archivo JSON dañado al iniciar", "avisos=1 productos=0",
          lambda: (lambda r: f"avisos={len(r[1])} productos={len(r[0]['productos'])}")(gestor_json.cargar_estado()))

    aprobados = sum(RESULTADOS)
    print(f"\nResumen: {aprobados}/{len(RESULTADOS)} casos aprobados.")
    return aprobados == len(RESULTADOS)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
