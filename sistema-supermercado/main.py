"""Punto de entrada del Sistema de Supermercado.

Ejecutar desde la carpeta sistema-supermercado:   python main.py
Arquitectura monolítica en capas: interfaz -> negocio -> persistencia.
"""
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from interfaz.vistas import (VistaCaja, VistaDevoluciones, VistaInventario,
                             VistaProductos, VistaReportes, VistaVentas)
from persistencia import gestor_json


class Aplicacion(tk.Tk):
    PESTANAS = (
        ("Ventas", VistaVentas),
        ("Productos", VistaProductos),
        ("Inventario", VistaInventario),
        ("Devoluciones", VistaDevoluciones),
        ("Caja", VistaCaja),
        ("Reportes", VistaReportes),
    )

    def __init__(self, estado):
        super().__init__()
        self.title("Sistema de gestión de supermercado")
        self.geometry("1150x700")
        self.minsize(980, 620)
        self.estado = estado
        self.cuaderno = ttk.Notebook(self)
        self.cuaderno.pack(fill="both", expand=True, padx=6, pady=6)
        self.vistas = []
        for titulo, clase in self.PESTANAS:
            vista = clase(self.cuaderno, estado)
            self.cuaderno.add(vista, text=f"  {titulo}  ")
            self.vistas.append(vista)
        self.cuaderno.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

    def _al_cambiar_pestana(self, _evento):
        """Cada vez que se entra a una pestaña se redibuja con datos frescos."""
        self.vistas[self.cuaderno.index(self.cuaderno.select())].actualizar()


def cargar_datos():
    """Carga los JSON; si es la primera vez, siembra productos de ejemplo."""
    estado, avisos = gestor_json.cargar_estado()
    if not estado["productos"] and not estado["ventas"] and not estado["caja"]:
        gestor_json.sembrar_datos_ejemplo(estado)
    return estado, avisos


def main():
    try:
        estado, avisos = cargar_datos()
    except gestor_json.ErrorPersistencia as error:
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("No se pudo iniciar", str(error))
        raiz.destroy()
        sys.exit(1)

    app = Aplicacion(estado)
    if avisos:
        messagebox.showwarning("Aviso al cargar los datos", "\n\n".join(avisos))
    app.mainloop()


if __name__ == "__main__":
    main()
