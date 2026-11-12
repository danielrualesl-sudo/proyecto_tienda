"""Utilidades compartidas por las vistas de Tkinter."""
import tkinter as tk
from tkinter import messagebox, ttk

from negocio.validaciones import ErrorValidacion
from persistencia.gestor_json import ErrorPersistencia


def formato_moneda(valor):
    return f"${valor:,.2f}"


def mostrar_info(mensaje, titulo="Información"):
    messagebox.showinfo(titulo, mensaje)


def mostrar_advertencia(mensaje, titulo="Atención"):
    messagebox.showwarning(titulo, mensaje)


def mostrar_error(mensaje, titulo="Error"):
    messagebox.showerror(titulo, mensaje)


def confirmar(mensaje, titulo="Confirmar"):
    return messagebox.askyesno(titulo, mensaje)


def ejecutar_seguro(accion):
    """Ejecuta `accion()` y muestra al usuario cualquier error.

    Devuelve (True, resultado) si todo salió bien o (False, None) si falló.
    Ninguna excepción se silencia: siempre se informa en pantalla.
    """
    try:
        resultado = accion()
    except ErrorValidacion as error:
        mostrar_advertencia(str(error), "Dato u operación no válidos")
    except ErrorPersistencia as error:
        mostrar_error(f"{error}\n\nNo se realizó ningún cambio.", "Error de archivo")
    except Exception as error:  # error imprevisto: se informa, no se oculta
        mostrar_error(f"{type(error).__name__}: {error}", "Error inesperado")
    else:
        return True, resultado
    return False, None


def crear_campo(padre, etiqueta, fila, columna=0, ancho=18, valor=""):
    """Etiqueta + Entry en una cuadrícula. Devuelve (variable, entrada)."""
    ttk.Label(padre, text=etiqueta).grid(row=fila, column=columna, sticky="e", padx=(6, 2), pady=3)
    variable = tk.StringVar(value=valor)
    entrada = ttk.Entry(padre, textvariable=variable, width=ancho)
    entrada.grid(row=fila, column=columna + 1, sticky="w", padx=(0, 10), pady=3)
    return variable, entrada


def crear_tabla(padre, columnas, alto=10):
    """columnas = [(id, titulo, ancho)]. Devuelve (contenedor, treeview)."""
    contenedor = ttk.Frame(padre)
    tabla = ttk.Treeview(contenedor, columns=[c[0] for c in columnas],
                         show="headings", height=alto, selectmode="browse")
    for ident, titulo, ancho in columnas:
        tabla.heading(ident, text=titulo)
        tabla.column(ident, width=ancho, anchor="w")
    barra = ttk.Scrollbar(contenedor, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return contenedor, tabla


def llenar_tabla(tabla, filas):
    """filas = [(iid, valores, etiqueta_opcional)]. El iid evita que Tk
    convierta códigos como '001' en números."""
    tabla.delete(*tabla.get_children())
    for iid, valores, *etiqueta in filas:
        tabla.insert("", "end", iid=iid, values=valores, tags=tuple(etiqueta))
