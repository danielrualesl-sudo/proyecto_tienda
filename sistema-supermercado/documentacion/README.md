# Sistema de gestión de supermercado (Proyecto A)

Programación I · Proyecto final · Python + Tkinter + JSON · Arquitectura monolítica en capas.

## Requisitos
- Python 3.9 o superior (con Tkinter; viene incluido en el instalador oficial de Windows/macOS).
- Sin dependencias externas, sin internet, sin SQL.

## Ejecución
Desde la carpeta `sistema-supermercado`:

    python main.py

La primera vez (archivos JSON vacíos) se cargan 10 productos ficticios de ejemplo.

Pruebas automáticas de la lógica de negocio (no tocan `datos/`):

    python pruebas_negocio.py

## Estructura
| Carpeta / archivo | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada: carga datos, crea la ventana y las 6 pestañas |
| `interfaz/vistas.py` | Pantallas: Ventas, Productos, Inventario, Devoluciones, Caja, Reportes |
| `interfaz/utilidades_ui.py` | Tablas, campos, mensajes y `ejecutar_seguro` (muestra todo error al usuario) |
| `negocio/inventario.py` | Catálogo, mantenimiento, entradas/salidas, alertas de stock mínimo |
| `negocio/ventas.py` | Carrito, descuento e IVA, facturación, devoluciones, reportes |
| `negocio/caja.py` | Apertura, ingresos/egresos, cierre y diferencia |
| `negocio/validaciones.py` | Validación de tipos, rangos, obligatorios y fechas |
| `persistencia/gestor_json.py` | Lectura/escritura JSON y transacciones atómicas |
| `datos/*.json` | `productos.json`, `ventas.json`, `caja.json` |

## Flujo de datos
Interfaz (vistas) → funciones de negocio → `gestor_json.transaccion` → archivos JSON.

## Estrategia anti-corrupción (reto de alta complejidad)
Cada operación que modifica datos se ejecuta sobre una **copia** del estado. Solo si
todas las reglas se cumplen se escriben los tres JSON en archivos `.tmp` y se reemplazan
los originales con `os.replace`. Si algo falla, ni la memoria ni los archivos cambian.
Una venta modifica en la misma transacción: factura, inventario y caja.

## Reglas configurables
`negocio/ventas.py`: `IMPUESTO_PORCENTAJE = 19.0` y `DESCUENTO_MAXIMO = 50.0`.

## Efectivo esperado al cerrar caja
saldo inicial + ventas + ingresos − devoluciones − egresos.

## Trabajo colaborativo
Sugerencia de reparto: una persona toma `negocio/` + `persistencia/` y la otra `interfaz/`
+ documentación (manual, pruebas, diagrama). Usar ramas y `git pull` antes de cada sesión.
