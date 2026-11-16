"""Interfaz gráfica del simulador de inventario y ventas."""

import tkinter as tk
from tkinter import messagebox, ttk

from modelo import ErrorInventario, Inventario


COLOR_TEXTO = "#1d2a33"
COLOR_SECUNDARIO = "#5b6770"
COLOR_BORDE = "#d5dbe1"
COLOR_ALERTA = "#a1261d"
COLOR_EXITO = "#245c3f"


def dinero(valor):
    return f"${valor:,.2f}"


def plural(cantidad, singular, terminacion="s"):
    return f"{cantidad} {singular}{'' if cantidad == 1 else terminacion}"


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Inventario y Ventas")
        self.geometry("1040x700")
        self.minsize(960, 640)
        self.inventario = Inventario()
        self._clave_seleccionada = None
        self._opciones_venta = {}

        self._configurar_estilos()
        self._crear_encabezado()
        self._crear_pestanas()
        self._crear_barra_estado()
        self.actualizar_todo()

        if self.inventario.aviso_carga:
            self._mensaje(self.inventario.aviso_carga, error=True)

    def _configurar_estilos(self):
        estilo = ttk.Style(self)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure(".", font=("Segoe UI", 10))
        estilo.configure("TButton", padding=(10, 5))
        estilo.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10))
        estilo.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        estilo.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        self.configure(background="#eef1f4")

    def _crear_encabezado(self):
        encabezado = tk.Frame(self, background="white", highlightbackground=COLOR_BORDE, highlightthickness=1)
        encabezado.pack(fill="x")
        tk.Label(
            encabezado,
            text="Simulador de Inventario y Ventas",
            background="white",
            foreground=COLOR_TEXTO,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=20, pady=(14, 0))
        tk.Label(
            encabezado,
            text="Registra productos, controla existencias y consulta tus resultados.",
            background="white",
            foreground=COLOR_SECUNDARIO,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=20, pady=(0, 12))

    def _crear_barra_estado(self):
        self.var_estado = tk.StringVar(value="Listo.")
        self.etiqueta_estado = tk.Label(
            self,
            textvariable=self.var_estado,
            anchor="w",
            background="#dde3e8",
            foreground="#33424d",
            padx=14,
            pady=5,
        )
        self.etiqueta_estado.pack(fill="x", side="bottom")

    def _crear_pestanas(self):
        cuaderno = ttk.Notebook(self)
        cuaderno.pack(fill="both", expand=True, padx=16, pady=12)

        pestana_inventario = ttk.Frame(cuaderno, padding=14)
        pestana_ventas = ttk.Frame(cuaderno, padding=14)
        pestana_reportes = ttk.Frame(cuaderno, padding=14)

        cuaderno.add(pestana_inventario, text="Inventario")
        cuaderno.add(pestana_ventas, text="Ventas")
        cuaderno.add(pestana_reportes, text="Reportes")

        self._crear_tab_inventario(pestana_inventario)
        self._crear_tab_ventas(pestana_ventas)
        self._crear_tab_reportes(pestana_reportes)

    def _crear_tab_inventario(self, contenedor):
        formulario = ttk.LabelFrame(contenedor, text="Datos del producto", padding=12)
        formulario.pack(fill="x")

        self.var_clave = tk.StringVar()
        self.var_nombre = tk.StringVar()
        self.var_precio = tk.StringVar()
        self.var_cantidad = tk.StringVar(value="0")

        campos = (
            ("Clave", self.var_clave, 16),
            ("Nombre", self.var_nombre, 34),
            ("Precio ($)", self.var_precio, 14),
            ("Cantidad", self.var_cantidad, 12),
        )
        for columna, (etiqueta, variable, ancho) in enumerate(campos):
            ttk.Label(formulario, text=etiqueta).grid(row=0, column=columna, sticky="w")
            ttk.Entry(formulario, textvariable=variable, width=ancho).grid(
                row=1, column=columna, sticky="we", padx=(0, 14), pady=(3, 0)
            )
            formulario.columnconfigure(columna, weight=1 if etiqueta == "Nombre" else 0)

        botones = ttk.Frame(formulario)
        botones.grid(row=2, column=0, columnspan=4, sticky="we", pady=(14, 0))
        ttk.Button(botones, text="Agregar producto", command=self._agregar_producto).pack(side="left")
        ttk.Button(botones, text="Guardar cambios", command=self._guardar_cambios).pack(side="left", padx=8)
        ttk.Button(botones, text="Limpiar formulario", command=self._limpiar_formulario).pack(side="left")
        ttk.Button(botones, text="Eliminar seleccionado", command=self._eliminar_producto).pack(side="right")

        ttk.Label(
            formulario,
            text="La clave identifica al producto y no se modifica al editarlo. Las existencias se capturan como cantidad total disponible.",
            foreground=COLOR_SECUNDARIO,
            font=("Segoe UI", 9),
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))

        marco_tabla = ttk.LabelFrame(contenedor, text="Existencias", padding=12)
        marco_tabla.pack(fill="both", expand=True, pady=(12, 0))

        barra = ttk.Frame(marco_tabla)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Label(barra, text="Buscar:").pack(side="left")
        self.var_busqueda = tk.StringVar()
        self.var_busqueda.trace_add("write", lambda *_: self._refrescar_inventario())
        ttk.Entry(barra, textvariable=self.var_busqueda, width=32).pack(side="left", padx=(8, 0))
        self.etiqueta_conteo = ttk.Label(barra, text="", foreground=COLOR_SECUNDARIO)
        self.etiqueta_conteo.pack(side="right")

        contenedor_tabla = ttk.Frame(marco_tabla)
        contenedor_tabla.pack(fill="both", expand=True)

        columnas = ("clave", "nombre", "precio", "cantidad", "valor")
        self.tabla_inventario = ttk.Treeview(
            contenedor_tabla, columns=columnas, show="headings", selectmode="browse"
        )
        encabezados = {
            "clave": ("Clave", 110, "w"),
            "nombre": ("Nombre", 320, "w"),
            "precio": ("Precio", 110, "e"),
            "cantidad": ("Existencias", 110, "e"),
            "valor": ("Valor", 120, "e"),
        }
        for columna, (titulo, ancho, alineacion) in encabezados.items():
            self.tabla_inventario.heading(columna, text=titulo)
            self.tabla_inventario.column(columna, width=ancho, anchor=alineacion, stretch=columna == "nombre")
        self.tabla_inventario.tag_configure("bajo", foreground=COLOR_ALERTA)
        self.tabla_inventario.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(contenedor_tabla, orient="vertical", command=self.tabla_inventario.yview)
        scroll.pack(side="right", fill="y")
        self.tabla_inventario.configure(yscrollcommand=scroll.set)
        self.tabla_inventario.bind("<<TreeviewSelect>>", self._seleccionar_producto)

    def _crear_tab_ventas(self, contenedor):
        registro = ttk.LabelFrame(contenedor, text="Registrar venta", padding=12)
        registro.pack(fill="x")

        ttk.Label(registro, text="Producto").grid(row=0, column=0, sticky="w")
        ttk.Label(registro, text="Cantidad").grid(row=0, column=1, sticky="w", padx=(14, 0))

        self.var_producto_venta = tk.StringVar()
        self.combo_productos = ttk.Combobox(
            registro, textvariable=self.var_producto_venta, state="readonly", width=52
        )
        self.combo_productos.grid(row=1, column=0, sticky="we", padx=(0, 14), pady=(3, 0))
        self.combo_productos.bind("<<ComboboxSelected>>", lambda _evento: self._actualizar_resumen_venta())

        self.var_cantidad_venta = tk.StringVar(value="1")
        self.var_cantidad_venta.trace_add("write", lambda *_: self._actualizar_resumen_venta())
        ttk.Spinbox(registro, from_=1, to=999999, width=10, textvariable=self.var_cantidad_venta).grid(
            row=1, column=1, sticky="w", pady=(3, 0)
        )
        ttk.Button(registro, text="Registrar venta", command=self._registrar_venta).grid(
            row=1, column=2, sticky="e", padx=(14, 0), pady=(3, 0)
        )
        registro.columnconfigure(0, weight=1)

        self.etiqueta_resumen_venta = ttk.Label(
            registro,
            text="Selecciona un producto para vender.",
            foreground=COLOR_SECUNDARIO,
        )
        self.etiqueta_resumen_venta.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))

        marco_historial = ttk.LabelFrame(contenedor, text="Últimas ventas", padding=12)
        marco_historial.pack(fill="both", expand=True, pady=(12, 0))

        contenedor_tabla = ttk.Frame(marco_historial)
        contenedor_tabla.pack(fill="both", expand=True)

        columnas = ("fecha", "clave", "nombre", "cantidad", "precio", "total")
        self.tabla_ventas = ttk.Treeview(contenedor_tabla, columns=columnas, show="headings", height=8)
        encabezados = {
            "fecha": ("Fecha", 150, "w"),
            "clave": ("Clave", 100, "w"),
            "nombre": ("Producto", 300, "w"),
            "cantidad": ("Cantidad", 90, "e"),
            "precio": ("Precio unitario", 130, "e"),
            "total": ("Total", 120, "e"),
        }
        for columna, (titulo, ancho, alineacion) in encabezados.items():
            self.tabla_ventas.heading(columna, text=titulo)
            self.tabla_ventas.column(columna, width=ancho, anchor=alineacion, stretch=columna == "nombre")
        self.tabla_ventas.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(contenedor_tabla, orient="vertical", command=self.tabla_ventas.yview)
        scroll.pack(side="right", fill="y")
        self.tabla_ventas.configure(yscrollcommand=scroll.set)

    def _crear_tab_reportes(self, contenedor):
        resumen = ttk.Frame(contenedor)
        resumen.pack(fill="x")

        self.tarjetas = {}
        tarjetas = (
            ("total", "Total vendido"),
            ("unidades", "Unidades vendidas"),
            ("ventas", "Número de ventas"),
            ("inventario", "Valor del inventario"),
        )
        for indice, (clave, titulo) in enumerate(tarjetas):
            tarjeta = tk.Frame(
                resumen, background="white", highlightbackground=COLOR_BORDE, highlightthickness=1
            )
            tarjeta.grid(row=0, column=indice, sticky="nsew", padx=(0 if indice == 0 else 8, 0))
            resumen.columnconfigure(indice, weight=1)
            tk.Label(
                tarjeta,
                text=titulo,
                background="white",
                foreground=COLOR_SECUNDARIO,
                font=("Segoe UI", 9),
            ).pack(anchor="w", padx=14, pady=(10, 0))
            valor = tk.Label(
                tarjeta,
                text="—",
                background="white",
                foreground=COLOR_TEXTO,
                font=("Segoe UI", 15, "bold"),
            )
            valor.pack(anchor="w", padx=14, pady=(2, 12))
            self.tarjetas[clave] = valor

        controles = ttk.Frame(contenedor)
        controles.pack(fill="x", pady=(14, 0))
        ttk.Label(controles, text="Umbral de bajo inventario:").pack(side="left")
        self.var_umbral = tk.StringVar(value=str(self.inventario.umbral_bajo_inventario))
        ttk.Spinbox(controles, from_=0, to=999999, width=8, textvariable=self.var_umbral).pack(
            side="left", padx=(8, 8)
        )
        ttk.Button(controles, text="Aplicar", command=self._aplicar_umbral).pack(side="left")
        ttk.Label(
            controles,
            text="Se marcan como bajo inventario los productos con existencias iguales o menores al umbral.",
            foreground=COLOR_SECUNDARIO,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(14, 0))

        detalle = ttk.Frame(contenedor)
        detalle.pack(fill="both", expand=True, pady=(12, 0))
        detalle.columnconfigure(0, weight=2)
        detalle.columnconfigure(1, weight=3)
        detalle.rowconfigure(0, weight=1)

        marco_bajo = ttk.LabelFrame(detalle, text="Productos por agotarse", padding=10)
        marco_bajo.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        contenedor_bajo = ttk.Frame(marco_bajo)
        contenedor_bajo.pack(fill="both", expand=True)
        columnas_bajo = ("clave", "nombre", "cantidad")
        self.tabla_bajo = ttk.Treeview(contenedor_bajo, columns=columnas_bajo, show="headings")
        for columna, (titulo, ancho) in {
            "clave": ("Clave", 90),
            "nombre": ("Producto", 200),
            "cantidad": ("Existencias", 90),
        }.items():
            self.tabla_bajo.heading(columna, text=titulo)
            self.tabla_bajo.column(
                columna, width=ancho, anchor="e" if columna == "cantidad" else "w", stretch=columna == "nombre"
            )
        self.tabla_bajo.pack(side="left", fill="both", expand=True)
        scroll_bajo = ttk.Scrollbar(contenedor_bajo, orient="vertical", command=self.tabla_bajo.yview)
        scroll_bajo.pack(side="right", fill="y")
        self.tabla_bajo.configure(yscrollcommand=scroll_bajo.set)

        marco_historial = ttk.LabelFrame(detalle, text="Historial de ventas", padding=10)
        marco_historial.grid(row=0, column=1, sticky="nsew")

        contenedor_historial = ttk.Frame(marco_historial)
        contenedor_historial.pack(fill="both", expand=True)
        columnas_historial = ("fecha", "clave", "nombre", "cantidad", "total")
        self.tabla_historial = ttk.Treeview(
            contenedor_historial, columns=columnas_historial, show="headings"
        )
        for columna, (titulo, ancho) in {
            "fecha": ("Fecha", 140),
            "clave": ("Clave", 90),
            "nombre": ("Producto", 220),
            "cantidad": ("Cant.", 60),
            "total": ("Total", 100),
        }.items():
            self.tabla_historial.heading(columna, text=titulo)
            self.tabla_historial.column(
                columna,
                width=ancho,
                anchor="e" if columna in ("cantidad", "total") else "w",
                stretch=columna == "nombre",
            )
        self.tabla_historial.pack(side="left", fill="both", expand=True)
        scroll_historial = ttk.Scrollbar(
            contenedor_historial, orient="vertical", command=self.tabla_historial.yview
        )
        scroll_historial.pack(side="right", fill="y")
        self.tabla_historial.configure(yscrollcommand=scroll_historial.set)

    def _mensaje(self, texto, error=False):
        self.var_estado.set(texto)
        self.etiqueta_estado.configure(foreground=COLOR_ALERTA if error else COLOR_EXITO)

    @staticmethod
    def _vaciar_tabla(tabla):
        for elemento in tabla.get_children():
            tabla.delete(elemento)

    def _limpiar_formulario(self, mensaje=None):
        self.var_clave.set("")
        self.var_nombre.set("")
        self.var_precio.set("")
        self.var_cantidad.set("0")
        self._clave_seleccionada = None
        self.tabla_inventario.selection_remove(self.tabla_inventario.selection())
        if mensaje:
            self._mensaje(mensaje)

    def _agregar_producto(self):
        try:
            producto = self.inventario.agregar_producto(
                self.var_clave.get(),
                self.var_nombre.get(),
                self.var_precio.get(),
                self.var_cantidad.get().strip() or "0",
            )
        except ErrorInventario as error:
            messagebox.showerror("No se pudo agregar el producto", str(error), parent=self)
            return
        self._limpiar_formulario()
        self.actualizar_todo()
        self._mensaje(f"Producto «{producto.nombre}» agregado con la clave {producto.clave}.")

    def _seleccionar_producto(self, _evento=None):
        seleccion = self.tabla_inventario.selection()
        if not seleccion:
            return
        clave = self.tabla_inventario.item(seleccion[0], "values")[0]
        producto = self.inventario.buscar(clave)
        if producto is None:
            return
        self._clave_seleccionada = producto.clave
        self.var_clave.set(producto.clave)
        self.var_nombre.set(producto.nombre)
        self.var_precio.set(f"{producto.precio:.2f}")
        self.var_cantidad.set(str(producto.cantidad))

    def _guardar_cambios(self):
        if not self._clave_seleccionada:
            messagebox.showinfo(
                "Selecciona un producto",
                "Elige un producto de la tabla para editar su nombre, precio o existencias.",
                parent=self,
            )
            return
        try:
            producto = self.inventario.editar_producto(
                self._clave_seleccionada,
                self.var_nombre.get(),
                self.var_precio.get(),
                self.var_cantidad.get(),
            )
        except ErrorInventario as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self)
            return
        self._limpiar_formulario()
        self.actualizar_todo()
        self._mensaje(f"Producto «{producto.nombre}» actualizado.")

    def _eliminar_producto(self):
        if not self._clave_seleccionada:
            messagebox.showinfo(
                "Selecciona un producto",
                "Elige un producto de la tabla para eliminarlo.",
                parent=self,
            )
            return
        producto = self.inventario.buscar(self._clave_seleccionada)
        if producto is None:
            return
        confirmacion = messagebox.askyesno(
            "Eliminar producto",
            f"¿Eliminar «{producto.nombre}» ({producto.clave})?\n\nEl historial de ventas se conservará.",
            parent=self,
        )
        if not confirmacion:
            return
        self.inventario.eliminar_producto(producto.clave)
        self._limpiar_formulario()
        self.actualizar_todo()
        self._mensaje(f"Producto «{producto.nombre}» eliminado.")

    def _producto_venta_actual(self):
        clave = self._opciones_venta.get(self.var_producto_venta.get())
        return self.inventario.buscar(clave) if clave else None

    def _actualizar_resumen_venta(self):
        producto = self._producto_venta_actual()
        if producto is None:
            self.etiqueta_resumen_venta.configure(
                text="Selecciona un producto para vender.", foreground=COLOR_SECUNDARIO
            )
            return
        try:
            cantidad = int(self.var_cantidad_venta.get())
        except ValueError:
            cantidad = 0
        total = producto.precio * cantidad if cantidad > 0 else 0
        self.etiqueta_resumen_venta.configure(
            text=(
                f"Precio unitario: {dinero(producto.precio)}    ·    "
                f"Disponible: {producto.cantidad}    ·    "
                f"Total estimado: {dinero(total)}"
            ),
            foreground=COLOR_ALERTA if cantidad > producto.cantidad else COLOR_SECUNDARIO,
        )

    def _registrar_venta(self):
        clave = self._opciones_venta.get(self.var_producto_venta.get())
        try:
            venta = self.inventario.registrar_venta(clave, self.var_cantidad_venta.get())
        except ErrorInventario as error:
            messagebox.showerror("Venta no registrada", str(error), parent=self)
            return
        self.var_cantidad_venta.set("1")
        self.actualizar_todo()
        self._mensaje(
            f"Venta #{venta.id} registrada: {venta.cantidad} × {venta.nombre} = {dinero(venta.total)}."
        )

    def _aplicar_umbral(self):
        try:
            umbral = self.inventario.establecer_umbral(self.var_umbral.get())
        except ErrorInventario as error:
            messagebox.showerror("Umbral inválido", str(error), parent=self)
            return
        self.actualizar_todo()
        self._mensaje(f"Umbral de bajo inventario actualizado a {umbral}.")

    def _refrescar_inventario(self):
        filtro = self.var_busqueda.get().strip().casefold()
        self._vaciar_tabla(self.tabla_inventario)
        productos = self.inventario.listar_productos()
        visibles = [
            producto
            for producto in productos
            if not filtro or filtro in producto.clave.casefold() or filtro in producto.nombre.casefold()
        ]
        umbral = self.inventario.umbral_bajo_inventario
        for producto in visibles:
            etiquetas = ("bajo",) if producto.cantidad <= umbral else ()
            self.tabla_inventario.insert(
                "",
                "end",
                values=(
                    producto.clave,
                    producto.nombre,
                    dinero(producto.precio),
                    producto.cantidad,
                    dinero(producto.valor),
                ),
                tags=etiquetas,
            )
        self.etiqueta_conteo.configure(
            text=f"{plural(len(visibles), 'producto')} de {len(productos)}"
        )

    def _refrescar_ventas(self):
        productos = self.inventario.listar_productos()
        self._opciones_venta = {}
        opciones = []
        for producto in productos:
            texto = f"{producto.clave} · {producto.nombre} (stock: {producto.cantidad})"
            self._opciones_venta[texto] = producto.clave
            opciones.append(texto)
        self.combo_productos.configure(values=opciones)
        if self.var_producto_venta.get() not in self._opciones_venta:
            self.var_producto_venta.set("")

        self._vaciar_tabla(self.tabla_ventas)
        for venta in self.inventario.historial_ventas(limite=20):
            self.tabla_ventas.insert(
                "",
                "end",
                values=(
                    venta.fecha,
                    venta.clave,
                    venta.nombre,
                    venta.cantidad,
                    dinero(venta.precio_unitario),
                    dinero(venta.total),
                ),
            )
        self._actualizar_resumen_venta()

    def _refrescar_reportes(self):
        totales = self.inventario.totales()
        self.tarjetas["total"].configure(text=dinero(totales["total_vendido"]))
        self.tarjetas["unidades"].configure(text=f"{totales['unidades_vendidas']:,}")
        self.tarjetas["ventas"].configure(text=f"{totales['numero_ventas']:,}")
        self.tarjetas["inventario"].configure(text=dinero(totales["valor_inventario"]))
        self.var_umbral.set(str(self.inventario.umbral_bajo_inventario))

        self._vaciar_tabla(self.tabla_bajo)
        for producto in self.inventario.productos_bajo_inventario():
            self.tabla_bajo.insert(
                "",
                "end",
                values=(producto.clave, producto.nombre, producto.cantidad),
            )

        self._vaciar_tabla(self.tabla_historial)
        for venta in self.inventario.historial_ventas():
            self.tabla_historial.insert(
                "",
                "end",
                values=(venta.fecha, venta.clave, venta.nombre, venta.cantidad, dinero(venta.total)),
            )

    def actualizar_todo(self):
        self._refrescar_inventario()
        self._refrescar_ventas()
        self._refrescar_reportes()


def main():
    aplicacion = Aplicacion()
    aplicacion.mainloop()


if __name__ == "__main__":
    main()
