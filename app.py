import tkinter as tk
from tkinter import messagebox

from modelo import ErrorInventario, Inventario


def dinero(valor):
    return "$" + format(valor, ",.2f")


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Inventario y Ventas")
        self.geometry("980x680")
        self.inventario = Inventario()
        self._clave_seleccionada = None
        self._productos_visibles = []
        self._ventas_recientes = []

        self._crear_interfaz()
        self.actualizar_todo()

        if self.inventario.aviso_carga:
            self._mensaje(self.inventario.aviso_carga, error=True)

    def _crear_interfaz(self):
        titulo = tk.Label(self, text="Simulador de Inventario y Ventas", font=("Arial", 16, "bold"))
        titulo.pack(pady=(10, 2))
        subtitulo = tk.Label(self, text="Registra productos, controla existencias y consulta resultados.")
        subtitulo.pack(pady=(0, 8))

        contenedor = tk.Frame(self)
        contenedor.pack(fill="both", expand=True, padx=10, pady=5)

        panel_izq = tk.Frame(contenedor)
        panel_izq.pack(side="left", fill="both", expand=True, padx=(0, 8))

        panel_der = tk.Frame(contenedor)
        panel_der.pack(side="right", fill="both", expand=True)

        self._crear_seccion_inventario(panel_izq)
        self._crear_seccion_ventas(panel_der)
        self._crear_seccion_reportes(panel_der)

        self.var_estado = tk.StringVar()
        self.var_estado.set("Listo.")
        self.etiqueta_estado = tk.Label(self, textvariable=self.var_estado, anchor="w", relief="sunken")
        self.etiqueta_estado.pack(fill="x", side="bottom")

    def _crear_seccion_inventario(self, padre):
        marco = tk.LabelFrame(padre, text="Inventario", padx=8, pady=8)
        marco.pack(fill="both", expand=True)

        form = tk.Frame(marco)
        form.pack(fill="x")

        tk.Label(form, text="Clave:").grid(row=0, column=0, sticky="w")
        self.var_clave = tk.StringVar()
        tk.Entry(form, textvariable=self.var_clave, width=12).grid(row=0, column=1, sticky="w", padx=(4, 10))

        tk.Label(form, text="Nombre:").grid(row=0, column=2, sticky="w")
        self.var_nombre = tk.StringVar()
        tk.Entry(form, textvariable=self.var_nombre, width=24).grid(row=0, column=3, sticky="w", padx=(4, 10))

        tk.Label(form, text="Precio:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.var_precio = tk.StringVar()
        tk.Entry(form, textvariable=self.var_precio, width=12).grid(row=1, column=1, sticky="w", padx=(4, 10), pady=(4, 0))

        tk.Label(form, text="Cantidad:").grid(row=1, column=2, sticky="w", pady=(4, 0))
        self.var_cantidad = tk.StringVar()
        self.var_cantidad.set("0")
        tk.Entry(form, textvariable=self.var_cantidad, width=12).grid(row=1, column=3, sticky="w", padx=(4, 10), pady=(4, 0))

        botones = tk.Frame(marco)
        botones.pack(fill="x", pady=(8, 4))
        tk.Button(botones, text="Agregar", command=self._agregar_producto).pack(side="left")
        tk.Button(botones, text="Guardar cambios", command=self._guardar_cambios).pack(side="left", padx=4)
        tk.Button(botones, text="Eliminar", command=self._eliminar_producto).pack(side="left", padx=4)
        tk.Button(botones, text="Limpiar", command=self._limpiar_formulario).pack(side="left", padx=4)

        nota = tk.Label(marco, text="La clave identifica al producto y no se cambia al editar.", fg="gray")
        nota.pack(anchor="w")

        busqueda = tk.Frame(marco)
        busqueda.pack(fill="x", pady=(6, 2))
        tk.Label(busqueda, text="Buscar:").pack(side="left")
        self.var_busqueda = tk.StringVar()
        self.var_busqueda.trace("w", lambda *args: self._refrescar_inventario())
        tk.Entry(busqueda, textvariable=self.var_busqueda, width=24).pack(side="left", padx=4)
        self.etiqueta_conteo = tk.Label(busqueda, text="", fg="gray")
        self.etiqueta_conteo.pack(side="right")

        lista_frame = tk.Frame(marco)
        lista_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.lista_inventario = tk.Listbox(lista_frame, height=18, exportselection=False)
        self.lista_inventario.pack(side="left", fill="both", expand=True)
        scroll = tk.Scrollbar(lista_frame, orient="vertical", command=self.lista_inventario.yview)
        scroll.pack(side="right", fill="y")
        self.lista_inventario.config(yscrollcommand=scroll.set)
        self.lista_inventario.bind("<<ListboxSelect>>", self._seleccionar_producto)

    def _crear_seccion_ventas(self, padre):
        marco = tk.LabelFrame(padre, text="Ventas", padx=8, pady=8)
        marco.pack(fill="both", expand=True)

        fila = tk.Frame(marco)
        fila.pack(fill="x")
        tk.Label(fila, text="Producto:").grid(row=0, column=0, sticky="w")
        self.var_producto_venta = tk.StringVar()
        self.var_producto_venta.set("")
        self.menu_productos = tk.OptionMenu(fila, self.var_producto_venta, "")
        self.menu_productos.config(width=28)
        self.menu_productos.grid(row=0, column=1, sticky="w", padx=4)
        self.var_producto_venta.trace("w", lambda *args: self._actualizar_resumen_venta())

        tk.Label(fila, text="Cantidad:").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.var_cantidad_venta = tk.StringVar()
        self.var_cantidad_venta.set("1")
        tk.Entry(fila, textvariable=self.var_cantidad_venta, width=8).grid(row=0, column=3, sticky="w", padx=4)
        self.var_cantidad_venta.trace("w", lambda *args: self._actualizar_resumen_venta())

        tk.Button(fila, text="Registrar venta", command=self._registrar_venta).grid(row=0, column=4, padx=6)

        self.etiqueta_resumen_venta = tk.Label(marco, text="Selecciona un producto para vender.", fg="gray", anchor="w", justify="left")
        self.etiqueta_resumen_venta.pack(fill="x", pady=(6, 4))

        tk.Label(marco, text="Ultimas ventas:").pack(anchor="w")
        lista_frame = tk.Frame(marco)
        lista_frame.pack(fill="both", expand=True)
        self.lista_ventas = tk.Listbox(lista_frame, height=8, exportselection=False)
        self.lista_ventas.pack(side="left", fill="both", expand=True)
        scroll = tk.Scrollbar(lista_frame, orient="vertical", command=self.lista_ventas.yview)
        scroll.pack(side="right", fill="y")
        self.lista_ventas.config(yscrollcommand=scroll.set)

    def _crear_seccion_reportes(self, padre):
        marco = tk.LabelFrame(padre, text="Reportes", padx=8, pady=8)
        marco.pack(fill="both", expand=True, pady=(8, 0))

        tarjetas = tk.Frame(marco)
        tarjetas.pack(fill="x")
        self.var_total_vendido = tk.StringVar()
        self.var_total_vendido.set("$0.00")
        self.var_unidades_vendidas = tk.StringVar()
        self.var_unidades_vendidas.set("0")
        self.var_numero_ventas = tk.StringVar()
        self.var_numero_ventas.set("0")
        self.var_valor_inventario = tk.StringVar()
        self.var_valor_inventario.set("$0.00")

        self._tarjeta(tarjetas, "Total vendido", self.var_total_vendido, 0)
        self._tarjeta(tarjetas, "Unidades vendidas", self.var_unidades_vendidas, 1)
        self._tarjeta(tarjetas, "Numero de ventas", self.var_numero_ventas, 2)
        self._tarjeta(tarjetas, "Valor inventario", self.var_valor_inventario, 3)

        umbral = tk.Frame(marco)
        umbral.pack(fill="x", pady=(6, 2))
        tk.Label(umbral, text="Umbral bajo inventario:").pack(side="left")
        self.var_umbral = tk.StringVar()
        self.var_umbral.set(str(self.inventario.umbral_bajo_inventario))
        tk.Entry(umbral, textvariable=self.var_umbral, width=6).pack(side="left", padx=4)
        tk.Button(umbral, text="Aplicar", command=self._aplicar_umbral).pack(side="left")

        bajos_frame = tk.Frame(marco)
        bajos_frame.pack(fill="both", expand=True, pady=(4, 0))
        izquierda = tk.Frame(bajos_frame)
        izquierda.pack(side="left", fill="both", expand=True, padx=(0, 6))
        derecha = tk.Frame(bajos_frame)
        derecha.pack(side="right", fill="both", expand=True)

        tk.Label(izquierda, text="Productos por agotarse:").pack(anchor="w")
        self.lista_bajos = tk.Listbox(izquierda, height=6, exportselection=False)
        self.lista_bajos.pack(fill="both", expand=True)

        tk.Label(derecha, text="Historial de ventas:").pack(anchor="w")
        self.lista_historial = tk.Listbox(derecha, height=6, exportselection=False)
        self.lista_historial.pack(fill="both", expand=True)

    def _tarjeta(self, padre, titulo, variable, columna):
        f = tk.Frame(padre, relief="groove", bd=1, padx=6, pady=4)
        f.grid(row=0, column=columna, sticky="nsew", padx=3)
        padre.columnconfigure(columna, weight=1)
        tk.Label(f, text=titulo, fg="gray").pack(anchor="w")
        tk.Label(f, textvariable=variable, font=("Arial", 11, "bold")).pack(anchor="w")

    def _mensaje(self, texto, error=False):
        self.var_estado.set(texto)
        if error:
            self.etiqueta_estado.config(fg="red")
        else:
            self.etiqueta_estado.config(fg="green")

    def _limpiar_formulario(self):
        self.var_clave.set("")
        self.var_nombre.set("")
        self.var_precio.set("")
        self.var_cantidad.set("0")
        self._clave_seleccionada = None
        self.lista_inventario.selection_clear(0, tk.END)

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
        self._mensaje('Producto "' + producto.nombre + '" agregado con la clave ' + producto.clave + ".")

    def _seleccionar_producto(self, event=None):
        seleccion = self.lista_inventario.curselection()
        if not seleccion:
            return
        indice = seleccion[0]
        if indice < 0 or indice >= len(self._productos_visibles):
            return
        producto = self._productos_visibles[indice]
        self._clave_seleccionada = producto.clave
        self.var_clave.set(producto.clave)
        self.var_nombre.set(producto.nombre)
        self.var_precio.set(format(producto.precio, ".2f"))
        self.var_cantidad.set(str(producto.cantidad))

    def _guardar_cambios(self):
        if not self._clave_seleccionada:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la lista para editarlo.", parent=self)
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
        self._mensaje('Producto "' + producto.nombre + '" actualizado.')

    def _eliminar_producto(self):
        if not self._clave_seleccionada:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la lista para eliminarlo.", parent=self)
            return
        producto = self.inventario.buscar(self._clave_seleccionada)
        if producto is None:
            return
        confirmar = messagebox.askyesno(
            "Eliminar producto",
            'Eliminar "' + producto.nombre + '" (' + producto.clave + ')?\nEl historial de ventas se conserva.',
            parent=self,
        )
        if not confirmar:
            return
        self.inventario.eliminar_producto(producto.clave)
        self._limpiar_formulario()
        self.actualizar_todo()
        self._mensaje('Producto "' + producto.nombre + '" eliminado.')

    def _texto_opcion_producto(self, producto):
        return producto.clave + " - " + producto.nombre + " (stock: " + str(producto.cantidad) + ")"

    def _producto_venta_actual(self):
        valor = self.var_producto_venta.get().strip()
        if not valor:
            return None
        clave = valor.split(" - ", 1)[0].strip()
        return self.inventario.buscar(clave)

    def _actualizar_resumen_venta(self):
        producto = self._producto_venta_actual()
        if producto is None:
            self.etiqueta_resumen_venta.config(text="Selecciona un producto para vender.", fg="gray")
            return
        try:
            cantidad = int(self.var_cantidad_venta.get())
        except ValueError:
            cantidad = 0
        total = producto.precio * cantidad if cantidad > 0 else 0
        texto = "Precio: " + dinero(producto.precio) + " | Disponible: " + str(producto.cantidad) + " | Total estimado: " + dinero(total)
        color = "red" if cantidad > producto.cantidad else "gray"
        self.etiqueta_resumen_venta.config(text=texto, fg=color)

    def _registrar_venta(self):
        producto = self._producto_venta_actual()
        clave = producto.clave if producto else ""
        try:
            venta = self.inventario.registrar_venta(clave, self.var_cantidad_venta.get())
        except ErrorInventario as error:
            messagebox.showerror("Venta no registrada", str(error), parent=self)
            return
        self.var_cantidad_venta.set("1")
        self.actualizar_todo()
        self._mensaje("Venta #" + str(venta.id) + " registrada: " + str(venta.cantidad) + " x " + venta.nombre + " = " + dinero(venta.total) + ".")

    def _aplicar_umbral(self):
        try:
            umbral = self.inventario.establecer_umbral(self.var_umbral.get())
        except ErrorInventario as error:
            messagebox.showerror("Umbral invalido", str(error), parent=self)
            return
        self.actualizar_todo()
        self._mensaje("Umbral de bajo inventario actualizado a " + str(umbral) + ".")

    def _refrescar_inventario(self):
        filtro = self.var_busqueda.get().strip().lower()
        self.lista_inventario.delete(0, tk.END)
        productos = self.inventario.listar_productos()
        visibles = []
        umbral = self.inventario.umbral_bajo_inventario
        for producto in productos:
            if filtro and filtro not in producto.clave.lower() and filtro not in producto.nombre.lower():
                continue
            visibles.append(producto)
            marca = " [BAJO]" if producto.cantidad <= umbral else ""
            linea = producto.clave + " | " + producto.nombre + " | " + dinero(producto.precio) + " | cant: " + str(producto.cantidad) + " | valor: " + dinero(producto.valor) + marca
            self.lista_inventario.insert(tk.END, linea)
        self._productos_visibles = visibles
        self.etiqueta_conteo.config(text=str(len(visibles)) + " producto(s) de " + str(len(productos)))

    def _refrescar_ventas(self):
        productos = self.inventario.listar_productos()
        opciones = []
        for p in productos:
            opciones.append(self._texto_opcion_producto(p))
        menu = self.menu_productos["menu"]
        menu.delete(0, "end")
        if opciones:
            for opcion in opciones:
                menu.add_command(label=opcion, command=lambda v=opcion: self.var_producto_venta.set(v))
            if self.var_producto_venta.get() not in opciones:
                self.var_producto_venta.set(opciones[0])
        else:
            menu.add_command(label="", command=lambda: self.var_producto_venta.set(""))
            self.var_producto_venta.set("")

        self.lista_ventas.delete(0, tk.END)
        for venta in self.inventario.historial_ventas(limite=20):
            linea = venta.fecha + " | " + venta.clave + " | " + venta.nombre + " | " + str(venta.cantidad) + " x " + dinero(venta.precio_unitario) + " = " + dinero(venta.total)
            self.lista_ventas.insert(tk.END, linea)
        self._actualizar_resumen_venta()

    def _refrescar_reportes(self):
        totales = self.inventario.totales()
        self.var_total_vendido.set(dinero(totales["total_vendido"]))
        self.var_unidades_vendidas.set(str(totales["unidades_vendidas"]))
        self.var_numero_ventas.set(str(totales["numero_ventas"]))
        self.var_valor_inventario.set(dinero(totales["valor_inventario"]))
        self.var_umbral.set(str(self.inventario.umbral_bajo_inventario))

        self.lista_bajos.delete(0, tk.END)
        for producto in self.inventario.productos_bajo_inventario():
            self.lista_bajos.insert(tk.END, producto.clave + " | " + producto.nombre + " | cant: " + str(producto.cantidad))

        self.lista_historial.delete(0, tk.END)
        for venta in self.inventario.historial_ventas():
            self.lista_historial.insert(tk.END, venta.fecha + " | " + venta.clave + " | " + str(venta.cantidad) + " | " + dinero(venta.total))

    def actualizar_todo(self):
        self._refrescar_inventario()
        self._refrescar_ventas()
        self._refrescar_reportes()


def main():
    app = Aplicacion()
    app.mainloop()


if __name__ == "__main__":
    main()
