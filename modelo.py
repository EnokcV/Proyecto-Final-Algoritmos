
import json
import os
from datetime import datetime


RUTA_DATOS_POR_DEFECTO = os.path.join(os.path.dirname(__file__), "datos.json")
UMBRAL_POR_DEFECTO = 5


class ErrorInventario(Exception):
    """Error de negocio que puede mostrarse directamente al usuario."""


def _campo_texto(valor, nombre_campo):
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        raise ErrorInventario(f"El campo «{nombre_campo}» es obligatorio.")
    return texto


def _campo_precio(valor):
    texto = "" if valor is None else str(valor).strip().replace("$", "").replace(",", ".")
    try:
        numero = float(texto)
    except (ValueError, TypeError):
        raise ErrorInventario("El precio debe ser un numero mayor o igual a 0.")
    if numero != numero or numero in (float("inf"), float("-inf")) or numero < 0:
        raise ErrorInventario("El precio debe ser un numero mayor o igual a 0.")
    return round(numero, 2)


def _campo_entero(valor, nombre_campo, minimo=0):
    texto = "" if valor is None else str(valor).strip()
    try:
        numero = int(texto)
    except (ValueError, TypeError):
        raise ErrorInventario(f"��{nombre_campo}�� debe ser un nǧmero entero.")
    if numero < minimo:
        raise ErrorInventario(f"��{nombre_campo}�� debe ser mayor o igual a {minimo}.")
    return numero


class Producto:
    def __init__(self, clave, nombre, precio, cantidad):
        self.clave = clave
        self.nombre = nombre
        self.precio = precio
        self.cantidad = cantidad

    @property
    def valor(self):
        return round(self.precio * self.cantidad, 2)

    def a_dict(self):
        return {
            "clave": self.clave,
            "nombre": self.nombre,
            "precio": self.precio,
            "cantidad": self.cantidad,
        }

    @classmethod
    def desde_dict(cls, datos):
        return cls(
            clave=str(datos.get("clave", "")).strip(),
            nombre=str(datos.get("nombre", "")).strip(),
            precio=round(float(datos.get("precio", 0) or 0), 2),
            cantidad=int(datos.get("cantidad", 0) or 0),
        )


class Venta:
    def __init__(self, id, fecha, clave, nombre, cantidad, precio_unitario, total):
        self.id = id
        self.fecha = fecha
        self.clave = clave
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.total = total

    def a_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha,
            "clave": self.clave,
            "nombre": self.nombre,
            "cantidad": self.cantidad,
            "precio_unitario": self.precio_unitario,
            "total": self.total,
        }

    @classmethod
    def desde_dict(cls, datos):
        return cls(
            id=int(datos.get("id", 0) or 0),
            fecha=str(datos.get("fecha", "")).strip(),
            clave=str(datos.get("clave", "")).strip(),
            nombre=str(datos.get("nombre", "")).strip(),
            cantidad=int(datos.get("cantidad", 0) or 0),
            precio_unitario=round(float(datos.get("precio_unitario", 0) or 0), 2),
            total=round(float(datos.get("total", 0) or 0), 2),
        )


class Inventario:
    """Administra productos, ventas y su guardado en disco."""

    def __init__(self, ruta=None):
        self.ruta = str(ruta) if ruta is not None else RUTA_DATOS_POR_DEFECTO
        self.productos = {}
        self.ventas = []
        self.umbral_bajo_inventario = UMBRAL_POR_DEFECTO
        self.siguiente_id = 1
        self.aviso_carga = ""
        self.cargar()

    @staticmethod
    def _normalizar(clave):
        return str(clave).strip().casefold()

    def cargar(self):
        if not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, ValueError):
            base, ext = os.path.splitext(self.ruta)
            nombre_base = os.path.basename(self.ruta)
            respaldo = base + ".corrupto-" + datetime.now().strftime("%Y%m%d%H%M%S") + ext
            nombre_respaldo = os.path.basename(respaldo)
            try:
                os.replace(self.ruta, respaldo)
                self.aviso_carga = 'No se pudo leer "' + nombre_base + '". Se guardo una copia como "' + nombre_respaldo + '".'
            except OSError:
                self.aviso_carga = 'No se pudo leer "' + nombre_base + '".'
            return

        for elemento in datos.get("productos", []):
            try:
                producto = Producto.desde_dict(elemento)
            except (TypeError, ValueError):
                continue
            if not producto.clave or not producto.nombre:
                continue
            producto.cantidad = max(0, producto.cantidad)
            producto.precio = max(0.0, producto.precio)
            self.productos.setdefault(self._normalizar(producto.clave), producto)

        for elemento in datos.get("ventas", []):
            try:
                venta = Venta.desde_dict(elemento)
            except (TypeError, ValueError):
                continue
            self.ventas.append(venta)

        if self.ventas:
            self.siguiente_id = max(venta.id for venta in self.ventas) + 1

        try:
            umbral = int(datos.get("config", {}).get("umbral_bajo_inventario", UMBRAL_POR_DEFECTO))
        except (TypeError, ValueError):
            umbral = UMBRAL_POR_DEFECTO
        self.umbral_bajo_inventario = max(0, umbral)

    def guardar(self):
        datos = {
            "productos": [producto.a_dict() for producto in self.listar_productos()],
            "ventas": [venta.a_dict() for venta in self.ventas],
            "config": {"umbral_bajo_inventario": self.umbral_bajo_inventario},
        }
        carpeta = os.path.dirname(self.ruta)
        if carpeta and not os.path.exists(carpeta):
            os.makedirs(carpeta)
        temporal = self.ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
        os.replace(temporal, self.ruta)

    def buscar(self, clave):
        if clave is None:
            return None
        return self.productos.get(self._normalizar(clave))

    def obtener(self, clave):
        producto = self.buscar(clave)
        if producto is None:
            raise ErrorInventario(f"No existe un producto con la clave «{clave}».")
        return producto

    def listar_productos(self):
        return sorted(self.productos.values(), key=lambda producto: producto.clave.casefold())

    def agregar_producto(self, clave, nombre, precio, cantidad=0):
        clave_limpia = _campo_texto(clave, "clave")
        if self._normalizar(clave_limpia) in self.productos:
            raise ErrorInventario(f"Ya existe un producto con la clave «{clave_limpia}».")
        producto = Producto(
            clave=clave_limpia,
            nombre=_campo_texto(nombre, "nombre"),
            precio=_campo_precio(precio),
            cantidad=_campo_entero(cantidad, "cantidad"),
        )
        self.productos[self._normalizar(clave_limpia)] = producto
        self.guardar()
        return producto

    def editar_producto(self, clave, nombre, precio, cantidad):
        producto = self.obtener(clave)
        producto.nombre = _campo_texto(nombre, "nombre")
        producto.precio = _campo_precio(precio)
        producto.cantidad = _campo_entero(cantidad, "cantidad")
        self.guardar()
        return producto

    def eliminar_producto(self, clave):
        producto = self.obtener(clave)
        del self.productos[self._normalizar(producto.clave)]
        self.guardar()
        return producto

    def registrar_venta(self, clave, cantidad):
        producto = self.buscar(clave)
        if producto is None:
            raise ErrorInventario("Selecciona un producto válido para registrar la venta.")
        cantidad_vendida = _campo_entero(cantidad, "cantidad a vender", minimo=1)
        if cantidad_vendida > producto.cantidad:
            raise ErrorInventario(
                f"No hay existencias suficientes de «{producto.nombre}». "
                f"Disponible: {producto.cantidad}, solicitado: {cantidad_vendida}."
            )
        venta = Venta(
            id=self.siguiente_id,
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            clave=producto.clave,
            nombre=producto.nombre,
            cantidad=cantidad_vendida,
            precio_unitario=producto.precio,
            total=round(producto.precio * cantidad_vendida, 2),
        )
        producto.cantidad -= cantidad_vendida
        self.ventas.append(venta)
        self.siguiente_id += 1
        self.guardar()
        return venta

    def establecer_umbral(self, valor):
        self.umbral_bajo_inventario = _campo_entero(valor, "umbral", minimo=0)
        self.guardar()
        return self.umbral_bajo_inventario

    def productos_bajo_inventario(self, umbral=None):
        limite = self.umbral_bajo_inventario if umbral is None else _campo_entero(umbral, "umbral", minimo=0)
        productos = [producto for producto in self.listar_productos() if producto.cantidad <= limite]
        return sorted(productos, key=lambda producto: (producto.cantidad, producto.clave.casefold()))

    def totales(self):
        return {
            "total_vendido": round(sum(venta.total for venta in self.ventas), 2),
            "unidades_vendidas": sum(venta.cantidad for venta in self.ventas),
            "numero_ventas": len(self.ventas),
            "valor_inventario": round(sum(producto.valor for producto in self.productos.values()), 2),
            "numero_productos": len(self.productos),
            "unidades_en_inventario": sum(producto.cantidad for producto in self.productos.values()),
        }

    def historial_ventas(self, limite=None):
        ventas = sorted(self.ventas, key=lambda venta: venta.id, reverse=True)
        return ventas if limite is None else ventas[:limite]
