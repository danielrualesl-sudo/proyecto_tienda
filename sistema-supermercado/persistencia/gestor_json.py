"""Capa de persistencia: lectura y escritura segura de los archivos JSON.

Estrategia anti-corrupción: cada guardado escribe primero archivos
temporales (.tmp) y SOLO cuando todos se escribieron bien los reemplaza
sobre los originales con os.replace (operación atómica). Si algo falla,
los archivos originales quedan intactos.
"""
import copy
import json
import os
from pathlib import Path

DIR_DATOS = Path(__file__).resolve().parent.parent / "datos"
ARCHIVOS = {
    "productos": "productos.json",
    "ventas": "ventas.json",
    "caja": "caja.json",
}

PRODUCTOS_EJEMPLO = [
    ("P001", "Arroz 1 kg", "Granos", 3200, 4200, 40, 10),
    ("P002", "Aceite de girasol 1 L", "Despensa", 9500, 12500, 25, 8),
    ("P003", "Leche entera 1 L", "Lácteos", 3400, 4300, 30, 12),
    ("P004", "Huevos x30", "Lácteos", 14000, 17500, 15, 5),
    ("P005", "Pan tajado", "Panadería", 4200, 5600, 20, 6),
    ("P006", "Gaseosa 1.5 L", "Bebidas", 4000, 5500, 35, 10),
    ("P007", "Jabón de manos", "Aseo", 2800, 3900, 18, 6),
    ("P008", "Papel higiénico x4", "Aseo", 7000, 9800, 22, 8),
    ("P009", "Café molido 250 g", "Despensa", 8500, 11500, 12, 5),
    ("P010", "Azúcar 1 kg", "Granos", 3000, 3900, 4, 8),
]


class ErrorPersistencia(Exception):
    """Problema al leer o escribir los archivos de datos."""


def _ruta(clave):
    return Path(DIR_DATOS) / ARCHIVOS[clave]


def cargar_json(ruta):
    """Lee un archivo JSON. Un archivo inexistente o vacío equivale a []."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            contenido = archivo.read()
        if not contenido.strip():
            return []
        return json.loads(contenido)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as error:
        raise ErrorPersistencia(
            f"El archivo '{Path(ruta).name}' está dañado ({error.msg}, línea {error.lineno})."
        ) from error
    except OSError as error:
        raise ErrorPersistencia(f"No se pudo leer '{Path(ruta).name}': {error}") from error


def cargar_estado():
    """Carga los tres archivos. Devuelve (estado, avisos).

    Si un archivo está dañado se guarda una copia '.corrupto' y se inicia
    vacío, informando al usuario mediante la lista de avisos.
    """
    try:
        Path(DIR_DATOS).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ErrorPersistencia(f"No se pudo crear la carpeta de datos: {error}") from error

    estado, avisos = {}, []
    for clave in ARCHIVOS:
        ruta = _ruta(clave)
        try:
            datos = cargar_json(ruta)
            if not isinstance(datos, list):
                raise ErrorPersistencia(f"El archivo '{ruta.name}' no contiene una lista.")
        except ErrorPersistencia as error:
            copia = ruta.with_name(ruta.name + ".corrupto")
            try:
                os.replace(ruta, copia)
            except OSError:
                pass
            avisos.append(f"{error} Se guardó una copia como '{copia.name}' y se inició vacío.")
            datos = []
        estado[clave] = datos
    return estado, avisos


def guardar_estado(estado):
    """Guarda los tres archivos de forma atómica (todo o nada)."""
    temporales = []
    try:
        Path(DIR_DATOS).mkdir(parents=True, exist_ok=True)
        for clave in ARCHIVOS:
            destino = _ruta(clave)
            temporal = destino.with_name(destino.name + ".tmp")
            temporales.append((temporal, destino))
            with open(temporal, "w", encoding="utf-8") as archivo:
                json.dump(estado[clave], archivo, ensure_ascii=False, indent=2)
                archivo.flush()
                os.fsync(archivo.fileno())
        for temporal, destino in temporales:
            os.replace(temporal, destino)
    except (OSError, TypeError, ValueError) as error:
        raise ErrorPersistencia(f"No se pudo guardar la información: {error}") from error
    finally:
        for temporal, _ in temporales:
            try:
                temporal.unlink(missing_ok=True)
            except OSError:
                pass


def transaccion(estado, operacion):
    """Ejecuta `operacion(copia)` sobre una copia del estado y la confirma.

    Si la operación lanza una excepción o el guardado falla, el estado en
    memoria y los archivos permanecen exactamente como estaban.
    """
    copia = copy.deepcopy(estado)
    resultado = operacion(copia)
    guardar_estado(copia)
    estado.clear()
    estado.update(copia)
    return resultado


def sembrar_datos_ejemplo(estado):
    """Carga productos ficticios para la demostración."""

    def operacion(copia):
        for codigo, nombre, categoria, compra, venta, stock, minimo in PRODUCTOS_EJEMPLO:
            copia["productos"].append({
                "codigo": codigo, "nombre": nombre, "categoria": categoria,
                "precio_compra": float(compra), "precio_venta": float(venta),
                "stock": stock, "stock_minimo": minimo, "activo": True,
                "movimientos": [],
            })

    transaccion(estado, operacion)
