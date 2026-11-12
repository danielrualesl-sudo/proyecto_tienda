"""Vistas (pantallas) de la aplicación. Cada una es un ttk.Frame con un
método actualizar() que vuelve a leer el estado y redibuja la pantalla.

Las vistas NO contienen reglas de negocio: llaman a las funciones del
paquete `negocio` y muestran el resultado o el error al usuario.
"""
import tkinter as tk
from datetime import date
from tkinter import ttk

from interfaz import utilidades_ui as ui
from negocio import caja, inventario, ventas
from negocio import validaciones as v


# ====================================================================== PRODUCTOS
class VistaProductos(ttk.Frame):
    CAMPOS = [
        ("codigo", "Código"), ("nombre", "Nombre"), ("categoria", "Categoría"),
        ("precio_compra", "Precio compra"), ("precio_venta", "Precio venta"),
        ("stock", "Stock inicial"), ("stock_minimo", "Stock mínimo"),
    ]

    def __init__(self, master, estado):
        super().__init__(master, padding=10)
        self.estado = estado
        self.vars, self.entradas = {}, {}
        self.codigo_sel = None
        self.var_busqueda = tk.StringVar()
        self.var_inactivos = tk.BooleanVar(value=False)
        self._construir()
        self.actualizar()

    def _construir(self):
        form = ttk.LabelFrame(self, text="Datos del producto", padding=8)
        form.pack(fill="x")
        for i, (clave, etiqueta) in enumerate(self.CAMPOS):
            var, entrada = ui.crear_campo(form, etiqueta, fila=i // 4, columna=(i % 4) * 2)
            self.vars[clave], self.entradas[clave] = var, entrada
        botones = ttk.Frame(form)
        botones.grid(row=2, column=0, columnspan=8, sticky="w", pady=(6, 0))
        ttk.Button(botones, text="Guardar nuevo", command=self.guardar_nuevo).pack(side="left", padx=3)
        ttk.Button(botones, text="Actualizar seleccionado", command=self.actualizar_seleccionado).pack(side="left", padx=3)
        ttk.Button(botones, text="Desactivar / Reactivar", command=self.alternar_activo).pack(side="left", padx=3)
        ttk.Button(botones, text="Limpiar formulario", command=self.limpiar).pack(side="left", padx=3)
        ttk.Label(botones, text="(el stock de un producto existente se cambia en Inventario)").pack(side="left", padx=8)

        busqueda = ttk.Frame(self)
        busqueda.pack(fill="x", pady=(10, 2))
        ttk.Label(busqueda, text="Buscar (código, nombre o categoría):").pack(side="left")
        ttk.Entry(busqueda, textvariable=self.var_busqueda, width=30).pack(side="left", padx=6)
        ttk.Checkbutton(busqueda, text="Mostrar desactivados", variable=self.var_inactivos,
                        command=self.actualizar).pack(side="left", padx=6)

        marco, self.tabla = ui.crear_tabla(self, [
            ("codigo", "Código", 80), ("nombre", "Nombre", 220), ("categoria", "Categoría", 110),
            ("compra", "P. compra", 90), ("venta", "P. venta", 90), ("stock", "Stock", 60),
            ("minimo", "Mínimo", 60), ("estado", "Estado", 80),
        ], alto=15)
        marco.pack(fill="both", expand=True)
        self.tabla.tag_configure("inactivo", foreground="gray")
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)
        self.var_busqueda.trace_add("write", lambda *_: self.actualizar())

    def _datos_formulario(self):
        return {clave: var.get() for clave, var in self.vars.items()}

    def guardar_nuevo(self):
        ok, _ = ui.ejecutar_seguro(lambda: inventario.crear_producto(self.estado, self._datos_formulario()))
        if ok:
            ui.mostrar_info("Producto registrado correctamente.")
            self.limpiar()
            self.actualizar()

    def actualizar_seleccionado(self):
        def accion():
            if not self.codigo_sel:
                raise v.ErrorValidacion("Seleccione un producto de la tabla para editarlo.")
            return inventario.editar_producto(self.estado, self.codigo_sel, self._datos_formulario())

        ok, _ = ui.ejecutar_seguro(accion)
        if ok:
            ui.mostrar_info("Producto actualizado correctamente.")
            self.actualizar()

    def alternar_activo(self):
        def accion():
            if not self.codigo_sel:
                raise v.ErrorValidacion("Seleccione un producto de la tabla.")
            producto = inventario.obtener_producto(self.estado, self.codigo_sel)
            nuevo = not producto["activo"]
            accion_txt = "reactivar" if nuevo else "desactivar"
            if not ui.confirmar(f"¿Desea {accion_txt} '{producto['nombre']}'?"):
                return None
            return inventario.cambiar_estado_producto(self.estado, producto["codigo"], nuevo)

        ok, resultado = ui.ejecutar_seguro(accion)
        if ok and resultado is not None:
            self.actualizar()

    def limpiar(self):
        self.codigo_sel = None
        for var in self.vars.values():
            var.set("")
        for clave in ("codigo", "stock"):
            self.entradas[clave].configure(state="normal")
        self.tabla.selection_remove(self.tabla.selection())

    def _al_seleccionar(self, _evento):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        producto = inventario.buscar_producto(self.estado, seleccion[0])
        if producto is None:
            return
        self.codigo_sel = producto["codigo"]
        for clave in self.vars:
            self.vars[clave].set(producto[clave])
        for clave in ("codigo", "stock"):
            self.entradas[clave].configure(state="readonly")

    def actualizar(self):
        productos = inventario.buscar_productos(
            self.estado, self.var_busqueda.get(), solo_activos=not self.var_inactivos.get())
        filas = []
        for p in productos:
            etiqueta = () if p["activo"] else ("inactivo",)
            filas.append((p["codigo"], (
                p["codigo"], p["nombre"], p["categoria"], ui.formato_moneda(p["precio_compra"]),
                ui.formato_moneda(p["precio_venta"]), p["stock"], p["stock_minimo"],
                "Activo" if p["activo"] else "Inactivo"), *etiqueta))
        ui.llenar_tabla(self.tabla, filas)


# ====================================================================== INVENTARIO
class VistaInventario(ttk.Frame):
    def __init__(self, master, estado):
        super().__init__(master, padding=10)
        self.estado = estado
        self._construir()
        self.actualizar()

    def _construir(self):
        form = ttk.LabelFrame(self, text="Registrar entrada o salida", padding=8)
        form.pack(fill="x")
        self.var_codigo, _ = ui.crear_campo(form, "Código", 0, 0, ancho=12)
        ttk.Label(form, text="Tipo").grid(row=0, column=2, sticky="e", padx=(6, 2))
        self.var_tipo = tk.StringVar(value="entrada")
        ttk.Combobox(form, textvariable=self.var_tipo, values=("entrada", "salida"),
                     state="readonly", width=10).grid(row=0, column=3, sticky="w", padx=(0, 10))
        self.var_cantidad, _ = ui.crear_campo(form, "Cantidad", 0, 4, ancho=8)
        self.var_motivo, _ = ui.crear_campo(form, "Motivo", 0, 6, ancho=24)
        ttk.Button(form, text="Registrar", command=self.registrar).grid(row=0, column=8, padx=6)

        self.var_alerta = tk.StringVar()
        ttk.Label(self, textvariable=self.var_alerta, foreground="firebrick",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 2))
        marco, self.tabla = ui.crear_tabla(self, [
            ("codigo", "Código", 80), ("nombre", "Nombre", 250), ("stock", "Stock", 70),
            ("minimo", "Mínimo", 70), ("estado", "Estado", 110),
        ], alto=16)
        marco.pack(fill="both", expand=True)
        self.tabla.tag_configure("alerta", foreground="firebrick")
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)

    def _al_seleccionar(self, _evento):
        seleccion = self.tabla.selection()
        if seleccion:
            self.var_codigo.set(seleccion[0])

    def registrar(self):
        ok, producto = ui.ejecutar_seguro(lambda: inventario.registrar_movimiento(
            self.estado, self.var_codigo.get(), self.var_tipo.get(),
            self.var_cantidad.get(), self.var_motivo.get()))
        if not ok:
            return
        self.var_cantidad.set("")
        self.var_motivo.set("")
        self.actualizar()
        if producto["stock"] <= producto["stock_minimo"]:
            ui.mostrar_advertencia(
                f"'{producto['nombre']}' quedó con {producto['stock']} unidades "
                f"(mínimo {producto['stock_minimo']}). Conviene reponerlo.", "Alerta de stock")
        else:
            ui.mostrar_info("Movimiento registrado correctamente.")

    def actualizar(self):
        filas = []
        for p in inventario.listar_productos(self.estado):
            bajo = p["stock"] <= p["stock_minimo"]
            filas.append((p["codigo"], (p["codigo"], p["nombre"], p["stock"], p["stock_minimo"],
                                        "STOCK BAJO" if bajo else "OK"), *(("alerta",) if bajo else ())))
        ui.llenar_tabla(self.tabla, filas)
        n = len(inventario.productos_con_alerta(self.estado))
        self.var_alerta.set(f"⚠ {n} producto(s) con stock igual o inferior al mínimo." if n else "")


# ====================================================================== VENTAS
class VistaVentas(ttk.Frame):
    def __init__(self, master, estado):
        super().__init__(master, padding=10)
        self.estado = estado
        self.carrito = {}          # solo códigos y cantidades, nunca referencias a dicts del estado
        self._construir()
        self.actualizar()

    def _construir(self):
        self.var_caja = tk.StringVar()
        ttk.Label(self, textvariable=self.var_caja, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True, pady=6)

        izq = ttk.LabelFrame(cuerpo, text="Catálogo", padding=6)
        izq.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.var_busqueda = tk.StringVar()
        ttk.Entry(izq, textvariable=self.var_busqueda).pack(fill="x")
        marco, self.tabla_cat = ui.crear_tabla(izq, [
            ("codigo", "Código", 70), ("nombre", "Nombre", 170),
            ("precio", "Precio", 90), ("stock", "Stock", 55)], alto=14)
        marco.pack(fill="both", expand=True, pady=4)
        self.tabla_cat.bind("<<TreeviewSelect>>", self._elegir_producto)
        fila = ttk.Frame(izq)
        fila.pack(fill="x")
        self.var_codigo, _ = ui.crear_campo(fila, "Código", 0, 0, ancho=10)
        self.var_cantidad, _ = ui.crear_campo(fila, "Cantidad", 0, 2, ancho=6, valor="1")
        ttk.Button(fila, text="Agregar al carrito", command=self.agregar).grid(row=0, column=4, padx=4)

        der = ttk.LabelFrame(cuerpo, text="Carrito y cobro", padding=6)
        der.pack(side="left", fill="both", expand=True)
        marco, self.tabla_car = ui.crear_tabla(der, [
            ("codigo", "Código", 70), ("nombre", "Nombre", 150), ("cantidad", "Cant.", 50),
            ("precio", "Precio", 85), ("subtotal", "Subtotal", 95)], alto=8)
        marco.pack(fill="both", expand=True)
        botones = ttk.Frame(der)
        botones.pack(fill="x", pady=4)
        ttk.Button(botones, text="Quitar", command=self.quitar).pack(side="left", padx=2)
        ttk.Button(botones, text="Cambiar cantidad (usa el campo Cantidad)",
                   command=self.cambiar_cantidad).pack(side="left", padx=2)
        ttk.Button(botones, text="Vaciar", command=self.vaciar).pack(side="left", padx=2)

        cobro = ttk.Frame(der)
        cobro.pack(fill="x")
        self.var_descuento, entrada_desc = ui.crear_campo(cobro, "Descuento (%)", 0, 0, ancho=8, valor="0")
        self.var_pago, entrada_pago = ui.crear_campo(cobro, "Pago recibido", 0, 2, ancho=12)
        entrada_desc.bind("<KeyRelease>", lambda _e: self.refrescar_carrito())
        entrada_pago.bind("<KeyRelease>", lambda _e: self.refrescar_carrito())

        self.var_aviso = tk.StringVar()
        ttk.Label(der, textvariable=self.var_aviso, foreground="firebrick").pack(anchor="w")
        self.var_subtotal, self.var_desc_val = tk.StringVar(), tk.StringVar()
        self.var_impuestos, self.var_total, self.var_cambio = tk.StringVar(), tk.StringVar(), tk.StringVar()
        totales = ttk.Frame(der)
        totales.pack(fill="x", pady=4)
        for i, (texto, var) in enumerate([
            ("Subtotal:", self.var_subtotal), ("Descuento:", self.var_desc_val),
            (f"Impuestos ({ventas.IMPUESTO_PORCENTAJE:g}%):", self.var_impuestos),
            ("TOTAL:", self.var_total), ("Cambio:", self.var_cambio)]):
            fuente = ("Segoe UI", 11, "bold") if texto == "TOTAL:" else None
            ttk.Label(totales, text=texto, font=fuente).grid(row=i, column=0, sticky="e")
            ttk.Label(totales, textvariable=var, font=fuente).grid(row=i, column=1, sticky="w", padx=8)
        ttk.Button(der, text="COBRAR", command=self.cobrar).pack(fill="x", pady=4)
        self.var_busqueda.trace_add("write", lambda *_: self._llenar_catalogo())

    # --- acciones
    def _elegir_producto(self, _evento):
        seleccion = self.tabla_cat.selection()
        if seleccion:
            self.var_codigo.set(seleccion[0])

    def _codigo_carrito(self):
        seleccion = self.tabla_car.selection()
        if not seleccion:
            raise v.ErrorValidacion("Seleccione un producto del carrito.")
        return seleccion[0]

    def agregar(self):
        ok, _ = ui.ejecutar_seguro(lambda: ventas.agregar_al_carrito(
            self.estado, self.carrito, self.var_codigo.get(), self.var_cantidad.get()))
        if ok:
            self.refrescar_carrito()

    def quitar(self):
        ok, _ = ui.ejecutar_seguro(lambda: ventas.retirar_del_carrito(self.carrito, self._codigo_carrito()))
        if ok:
            self.refrescar_carrito()

    def cambiar_cantidad(self):
        ok, _ = ui.ejecutar_seguro(lambda: ventas.modificar_cantidad(
            self.estado, self.carrito, self._codigo_carrito(), self.var_cantidad.get()))
        if ok:
            self.refrescar_carrito()

    def vaciar(self):
        self.carrito.clear()
        self.refrescar_carrito()

    def cobrar(self):
        ok, factura = ui.ejecutar_seguro(lambda: ventas.procesar_venta(
            self.estado, self.carrito, self.var_descuento.get(), self.var_pago.get()))
        if not ok:
            return
        ui.mostrar_info(
            f"Factura {ventas.formato_factura(factura['numero'])} generada.\n\n"
            f"Total: {ui.formato_moneda(factura['total'])}\n"
            f"Pago: {ui.formato_moneda(factura['pago'])}\n"
            f"Cambio: {ui.formato_moneda(factura['cambio'])}", "Venta registrada")
        self.carrito.clear()
        self.var_pago.set("")
        self.var_descuento.set("0")
        self.actualizar()

    # --- pantalla
    def refrescar_carrito(self):
        try:
            totales = ventas.calcular_totales(self.estado, self.carrito, self.var_descuento.get())
        except v.ErrorValidacion as error:
            self.var_aviso.set(str(error))
            totales = ventas.calcular_totales(self.estado, self.carrito, 0)
        else:
            self.var_aviso.set("")
        ui.llenar_tabla(self.tabla_car, [
            (l["codigo"], (l["codigo"], l["nombre"], l["cantidad"],
                           ui.formato_moneda(l["precio_unitario"]), ui.formato_moneda(l["subtotal"])))
            for l in totales["lineas"]])
        self.var_subtotal.set(ui.formato_moneda(totales["subtotal"]))
        self.var_desc_val.set(ui.formato_moneda(totales["descuento"]))
        self.var_impuestos.set(ui.formato_moneda(totales["impuestos"]))
        self.var_total.set(ui.formato_moneda(totales["total"]))
        try:
            pago = v.decimal(self.var_pago.get(), "Pago", minimo=0)
            self.var_cambio.set(ui.formato_moneda(pago - totales["total"]) if pago >= totales["total"] else "pago insuficiente")
        except v.ErrorValidacion:
            self.var_cambio.set("—")

    def _llenar_catalogo(self):
        productos = inventario.buscar_productos(self.estado, self.var_busqueda.get())
        ui.llenar_tabla(self.tabla_cat, [
            (p["codigo"], (p["codigo"], p["nombre"], ui.formato_moneda(p["precio_venta"]), p["stock"]))
            for p in productos])

    def actualizar(self):
        sesion = caja.sesion_abierta(self.estado)
        self.var_caja.set(f"Caja abierta (sesión {sesion['id']})" if sesion
                          else "⚠ Caja cerrada: abra la caja en la pestaña Caja para poder vender.")
        self.carrito = {c: q for c, q in self.carrito.items() if inventario.buscar_producto(self.estado, c)}
        self._llenar_catalogo()
        self.refrescar_carrito()


# ====================================================================== DEVOLUCIONES
class VistaDevoluciones(ttk.Frame):
    def __init__(self, master, estado):
        super().__init__(master, padding=10)
        self.estado = estado
        self.numero_actual = None
        self._construir()
        self.actualizar()

    def _construir(self):
        top = ttk.LabelFrame(self, text="Buscar factura", padding=8)
        top.pack(fill="x")
        self.var_numero, _ = ui.crear_campo(top, "Número de factura", 0, 0, ancho=10)
        ttk.Button(top, text="Buscar", command=self.buscar).grid(row=0, column=2, padx=6)
        self.var_info = tk.StringVar(value="Escriba un número o elija una factura del historial.")
        ttk.Label(top, textvariable=self.var_info).grid(row=0, column=3, padx=10)

        marco, self.tabla = ui.crear_tabla(self, [
            ("codigo", "Código", 80), ("nombre", "Producto", 240), ("vendido", "Vendido", 80),
            ("devuelto", "Devuelto", 80), ("disponible", "Disponible", 90)], alto=6)
        marco.pack(fill="x", pady=8)
        fila = ttk.Frame(self)
        fila.pack(fill="x")
        self.var_cantidad, _ = ui.crear_campo(fila, "Cantidad a devolver", 0, 0, ancho=8, valor="1")
        ttk.Button(fila, text="Registrar devolución de la línea seleccionada",
                   command=self.registrar).grid(row=0, column=2, padx=6)

        ttk.Label(self, text="Historial de facturas", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 2))
        marco, self.tabla_hist = ui.crear_tabla(self, [
            ("numero", "Factura", 90), ("fecha", "Fecha", 150), ("total", "Total", 110), ("estado", "Estado", 140)], alto=8)
        marco.pack(fill="both", expand=True)
        self.tabla_hist.bind("<<TreeviewSelect>>", self._elegir_factura)

    def _elegir_factura(self, _evento):
        seleccion = self.tabla_hist.selection()
        if seleccion:
            self.var_numero.set(seleccion[0])
            self.buscar()

    def buscar(self):
        ok, factura = ui.ejecutar_seguro(lambda: ventas.obtener_factura(self.estado, self.var_numero.get()))
        if not ok:
            self.numero_actual = None
            ui.llenar_tabla(self.tabla, [])
            return
        self.numero_actual = factura["numero"]
        self._mostrar_factura()

    def _mostrar_factura(self):
        factura = ventas.buscar_factura(self.estado, self.numero_actual)
        if factura is None:
            return
        self.var_info.set(f"{ventas.formato_factura(factura['numero'])} · {factura['fecha']} · "
                          f"Total {ui.formato_moneda(factura['total'])} · {factura['estado']}")
        ui.llenar_tabla(self.tabla, [
            (l["codigo"], (l["codigo"], l["nombre"], l["cantidad"], l.get("devuelto", 0),
                           l["cantidad"] - l.get("devuelto", 0))) for l in factura["detalle"]])

    def registrar(self):
        def accion():
            if self.numero_actual is None:
                raise v.ErrorValidacion("Primero busque una factura.")
            seleccion = self.tabla.selection()
            if not seleccion:
                raise v.ErrorValidacion("Seleccione la línea de la factura que desea devolver.")
            return ventas.registrar_devolucion(
                self.estado, self.numero_actual, {seleccion[0]: self.var_cantidad.get()})

        ok, reembolso = ui.ejecutar_seguro(accion)
        if ok:
            ui.mostrar_info(f"Devolución registrada.\nValor a reembolsar: {ui.formato_moneda(reembolso)}")
            self._mostrar_factura()
            self.actualizar()

    def actualizar(self):
        ui.llenar_tabla(self.tabla_hist, [
            (str(f["numero"]), (ventas.formato_factura(f["numero"]), f["fecha"],
                                ui.formato_moneda(f["total"]), f["estado"]))
            for f in reversed(self.estado["ventas"])])
        if self.numero_actual is not None:
            self._mostrar_factura()


# ====================================================================== REPORTES
class VistaReportes(ttk.Frame):
    def __init__(self, master, estado):
        super().__init__(master, padding=10)
        self.estado = estado
        self._construir()

    def _construir(self):
        form = ttk.LabelFrame(self, text="Intervalo de fechas (AAAA-MM-DD)", padding=8)
        form.pack(fill="x")
        hoy = date.today()
        self.var_desde, _ = ui.crear_campo(form, "Desde", 0, 0, ancho=12, valor=hoy.replace(day=1).isoformat())
        self.var_hasta, _ = ui.crear_campo(form, "Hasta", 0, 2, ancho=12, valor=hoy.isoformat())
        ttk.Button(form, text="Consultar", command=self.consultar).grid(row=0, column=4, padx=6)

        self.var_resumen = tk.StringVar(value="Pulse «Consultar» para generar el reporte.")
        ttk.Label(self, textvariable=self.var_resumen, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=8)

        ttk.Label(self, text="Productos más vendidos (unidades netas)").pack(anchor="w")
        marco, self.tabla_top = ui.crear_tabla(self, [
            ("codigo", "Código", 90), ("nombre", "Producto", 260), ("unidades", "Unidades", 90)], alto=6)
        marco.pack(fill="x", pady=(0, 8))
        ttk.Label(self, text="Facturas del intervalo").pack(anchor="w")
        marco, self.tabla_fact = ui.crear_tabla(self, [
            ("numero", "Factura", 90), ("fecha", "Fecha", 150), ("total", "Total", 110), ("estado", "Estado", 140)], alto=8)
        marco.pack(fill="both", expand=True)

    def consultar(self):
        ok, r = ui.ejecutar_seguro(lambda: ventas.reporte_ventas(
            self.estado, self.var_desde.get(), self.var_hasta.get()))
        if not ok:
            return
        self.var_resumen.set(f"Facturas: {r['num_facturas']}   ·   Ingresos netos: "
                             f"{ui.formato_moneda(r['ingresos'])}   ·   Unidades vendidas: {r['unidades']}")
        ui.llenar_tabla(self.tabla_top, [(d["codigo"], (d["codigo"], d["nombre"], d["unidades"]))
                                         for d in r["mas_vendidos"]])
        ui.llenar_tabla(self.tabla_fact, [
            (str(f["numero"]), (ventas.formato_factura(f["numero"]), f["fecha"],
                                ui.formato_moneda(f["total"]), f["estado"])) for f in r["facturas"]])

    def actualizar(self):
        pass  # el reporte se genera solo cuando el usuario pulsa «Consultar»


# ====================================================================== CAJA
class VistaCaja(ttk.Frame):
    def __init__(self, master, estado):
        super().__init__(master, padding=10)
        self.estado = estado
        self._construir()
        self.actualizar()

    def _construir(self):
        self.var_estado = tk.StringVar()
        ttk.Label(self, textvariable=self.var_estado, font=("Segoe UI", 11, "bold")).pack(anchor="w")

        apertura = ttk.LabelFrame(self, text="Apertura", padding=8)
        apertura.pack(fill="x", pady=4)
        self.var_saldo, _ = ui.crear_campo(apertura, "Saldo inicial", 0, 0, ancho=14)
        ttk.Button(apertura, text="Abrir caja", command=self.abrir).grid(row=0, column=2, padx=6)

        mov = ttk.LabelFrame(self, text="Ingresos y egresos de efectivo", padding=8)
        mov.pack(fill="x", pady=4)
        ttk.Label(mov, text="Tipo").grid(row=0, column=0, sticky="e", padx=(6, 2))
        self.var_tipo = tk.StringVar(value="ingreso")
        ttk.Combobox(mov, textvariable=self.var_tipo, values=("ingreso", "egreso"),
                     state="readonly", width=9).grid(row=0, column=1, padx=(0, 10))
        self.var_monto, _ = ui.crear_campo(mov, "Monto", 0, 2, ancho=12)
        self.var_desc, _ = ui.crear_campo(mov, "Descripción", 0, 4, ancho=28)
        ttk.Button(mov, text="Registrar", command=self.registrar).grid(row=0, column=6, padx=6)

        marco, self.tabla_mov = ui.crear_tabla(self, [
            ("fecha", "Fecha", 150), ("tipo", "Tipo", 100), ("monto", "Monto", 110), ("desc", "Descripción", 300)], alto=7)
        marco.pack(fill="x", pady=4)
        self.var_esperado = tk.StringVar()
        ttk.Label(self, textvariable=self.var_esperado).pack(anchor="w")

        cierre = ttk.LabelFrame(self, text="Cierre", padding=8)
        cierre.pack(fill="x", pady=4)
        self.var_declarado, _ = ui.crear_campo(cierre, "Efectivo declarado", 0, 0, ancho=14)
        ttk.Button(cierre, text="Cerrar caja", command=self.cerrar).grid(row=0, column=2, padx=6)

        ttk.Label(self, text="Historial de sesiones", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))
        marco, self.tabla_ses = ui.crear_tabla(self, [
            ("id", "Sesión", 60), ("apertura", "Apertura", 140), ("cierre", "Cierre", 140),
            ("esperado", "Esperado", 100), ("declarado", "Declarado", 100), ("diferencia", "Diferencia", 100)], alto=5)
        marco.pack(fill="both", expand=True)

    def abrir(self):
        ok, sesion = ui.ejecutar_seguro(lambda: caja.abrir_caja(self.estado, self.var_saldo.get()))
        if ok:
            self.var_saldo.set("")
            ui.mostrar_info(f"Caja abierta (sesión {sesion['id']}).")
            self.actualizar()

    def registrar(self):
        ok, _ = ui.ejecutar_seguro(lambda: caja.registrar_movimiento_manual(
            self.estado, self.var_tipo.get(), self.var_monto.get(), self.var_desc.get()))
        if ok:
            self.var_monto.set("")
            self.var_desc.set("")
            self.actualizar()

    def cerrar(self):
        if caja.sesion_abierta(self.estado) is not None and not ui.confirmar(
                "¿Cerrar la caja con el efectivo declarado? Esta acción no se puede deshacer."):
            return
        ok, sesion = ui.ejecutar_seguro(lambda: caja.cerrar_caja(self.estado, self.var_declarado.get()))
        if not ok:
            return
        dif = sesion["diferencia"]
        veredicto = "La caja cuadra." if dif == 0 else ("Sobrante" if dif > 0 else "Faltante")
        ui.mostrar_info(
            f"Esperado: {ui.formato_moneda(sesion['valor_esperado'])}\n"
            f"Declarado: {ui.formato_moneda(sesion['valor_declarado'])}\n"
            f"Diferencia: {ui.formato_moneda(dif)}  →  {veredicto}", "Caja cerrada")
        self.var_declarado.set("")
        self.actualizar()

    def actualizar(self):
        sesion = caja.sesion_abierta(self.estado)
        if sesion is None:
            self.var_estado.set("Caja cerrada")
            self.var_esperado.set("")
            ui.llenar_tabla(self.tabla_mov, [])
        else:
            self.var_estado.set(f"Caja abierta · sesión {sesion['id']} · saldo inicial "
                                f"{ui.formato_moneda(sesion['saldo_inicial'])}")
            self.var_esperado.set(f"Efectivo esperado ahora: {ui.formato_moneda(caja.efectivo_esperado(sesion))}")
            ui.llenar_tabla(self.tabla_mov, [
                (None, (m["fecha"], m["tipo"], ui.formato_moneda(m["monto"]), m["descripcion"]))
                for m in sesion["movimientos"]])
        ui.llenar_tabla(self.tabla_ses, [
            (str(s["id"]), (s["id"], s["apertura"], s["cierre"] or "—",
                            ui.formato_moneda(s["valor_esperado"]) if s["valor_esperado"] is not None else "—",
                            ui.formato_moneda(s["valor_declarado"]) if s["valor_declarado"] is not None else "—",
                            ui.formato_moneda(s["diferencia"]) if s["diferencia"] is not None else "—"))
            for s in reversed(self.estado["caja"])])
