
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


RUTA_DATOS_POR_DEFECTO = Path(__file__).with_name("datos.json")
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
    except ValueError as exc:
        raise ErrorInventario("El precio debe ser un número mayor o igual a 0.") from exc
    if not math.isfinite(numero) or numero < 0:
        raise ErrorInventario("El precio debe ser un número mayor o igual a 0.")
    return round(numero, 2)


def _campo_entero(valor, nombre_campo, minimo=0):
    texto = "" if valor is None else str(valor).strip()
    try:
        numero = int(texto)
    except ValueError as exc:
        raise ErrorInventario(f"«{nombre_campo}» debe ser un número entero.") from exc
    if numero < minimo:
        raise ErrorInventario(f"«{nombre_campo}» debe ser mayor o igual a {minimo}.")
    return numero


@dataclass
class Producto:
    clave: str
    nombre: str
    precio: float
    cantidad: int

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


@dataclass
class Venta:
    id: int
    fecha: str
    clave: str
    nombre: str
    cantidad: int
    precio_unitario: float
    total: float

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
        self.ruta = Path(ruta) if ruta is not None else RUTA_DATOS_POR_DEFECTO
        self.productos: dict[str, Producto] = {}
        self.ventas: list[Venta] = []
        self.umbral_bajo_inventario = UMBRAL_POR_DEFECTO
        self.siguiente_id = 1
        self.aviso_carga = ""
        self.cargar()

    @staticmethod
    def _normalizar(clave):
        return str(clave).strip().casefold()

    def cargar(self):
        if not self.ruta.exists():
            return
        try:
            with self.ruta.open("r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError):
            respaldo = self.ruta.with_name(
                f"{self.ruta.stem}.corrupto-{datetime.now():%Y%m%d%H%M%S}{self.ruta.suffix}"
            )
            try:
                os.replace(self.ruta, respaldo)
                self.aviso_carga = (
                    f"No se pudo leer «{self.ruta.name}». Se guardó una copia como «{respaldo.name}»."
                )
            except OSError:
                self.aviso_carga = f"No se pudo leer «{self.ruta.name}»."
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
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = self.ruta.with_name(self.ruta.name + ".tmp")
        with temporal.open("w", encoding="utf-8") as archivo:
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
