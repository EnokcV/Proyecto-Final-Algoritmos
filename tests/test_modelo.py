import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modelo import ErrorInventario, Inventario


class InventarioBase(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / "datos.json"
        self.inventario = Inventario(self.ruta)


class PruebasProductos(InventarioBase):
    def test_agregar_y_buscar_sin_distinguir_mayusculas(self):
        self.inventario.agregar_producto("A-01", "Café molido", "125.50", "10")

        producto = self.inventario.buscar("a-01")

        self.assertIsNotNone(producto)
        self.assertEqual(producto.nombre, "Café molido")
        self.assertEqual(producto.precio, 125.50)
        self.assertEqual(producto.cantidad, 10)

    def test_clave_duplicada_es_rechazada(self):
        self.inventario.agregar_producto("A-01", "Café", 100, 5)

        with self.assertRaises(ErrorInventario):
            self.inventario.agregar_producto("a-01", "Otro café", 90, 3)

    def test_datos_invalidos_son_rechazados(self):
        with self.assertRaises(ErrorInventario):
            self.inventario.agregar_producto("", "Sin clave", 10, 1)
        with self.assertRaises(ErrorInventario):
            self.inventario.agregar_producto("B-01", "", 10, 1)
        with self.assertRaises(ErrorInventario):
            self.inventario.agregar_producto("B-02", "Producto", "abc", 1)
        with self.assertRaises(ErrorInventario):
            self.inventario.agregar_producto("B-03", "Producto", -5, 1)
        with self.assertRaises(ErrorInventario):
            self.inventario.agregar_producto("B-04", "Producto", 10, -1)

    def test_editar_y_eliminar_producto(self):
        self.inventario.agregar_producto("A-01", "Café", 100, 5)

        editado = self.inventario.editar_producto("A-01", "Café gourmet", 120, 8)
        self.assertEqual(editado.nombre, "Café gourmet")
        self.assertEqual(editado.precio, 120)
        self.assertEqual(editado.cantidad, 8)

        self.inventario.eliminar_producto("A-01")
        self.assertIsNone(self.inventario.buscar("A-01"))
        self.assertEqual(self.inventario.listar_productos(), [])


class PruebasVentas(InventarioBase):
    def setUp(self):
        super().setUp()
        self.inventario.agregar_producto("A-01", "Café", "50.50", "10")

    def test_venta_descuenta_existencias_y_calcula_total(self):
        venta = self.inventario.registrar_venta("a-01", "3")

        self.assertEqual(venta.cantidad, 3)
        self.assertEqual(venta.total, 151.50)
        self.assertEqual(self.inventario.buscar("A-01").cantidad, 7)
        self.assertEqual(len(self.inventario.historial_ventas()), 1)

    def test_no_permite_existencias_negativas(self):
        with self.assertRaises(ErrorInventario):
            self.inventario.registrar_venta("A-01", "11")

        self.assertEqual(self.inventario.buscar("A-01").cantidad, 10)

    def test_vender_todo_el_stock_es_permitido(self):
        self.inventario.registrar_venta("A-01", "10")

        self.assertEqual(self.inventario.buscar("A-01").cantidad, 0)
        with self.assertRaises(ErrorInventario):
            self.inventario.registrar_venta("A-01", "1")

    def test_cantidad_invalida_es_rechazada(self):
        for cantidad in ("0", "-2", "dos", ""):
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(ErrorInventario):
                    self.inventario.registrar_venta("A-01", cantidad)

    def test_producto_inexistente_es_rechazado(self):
        with self.assertRaises(ErrorInventario):
            self.inventario.registrar_venta("NO-EXISTE", "1")


class PruebasReportes(InventarioBase):
    def test_totales_del_negocio(self):
        self.inventario.agregar_producto("A-01", "Café", "50", "10")
        self.inventario.agregar_producto("A-02", "Pan", "20", "4")
        self.inventario.registrar_venta("A-01", "2")
        self.inventario.registrar_venta("A-02", "1")

        totales = self.inventario.totales()

        self.assertEqual(totales["total_vendido"], 120)
        self.assertEqual(totales["unidades_vendidas"], 3)
        self.assertEqual(totales["numero_ventas"], 2)
        self.assertEqual(totales["numero_productos"], 2)
        self.assertEqual(totales["unidades_en_inventario"], 11)
        self.assertEqual(totales["valor_inventario"], 460)

    def test_productos_bajo_inventario_respeta_umbral(self):
        self.inventario.agregar_producto("A-01", "Café", "50", "2")
        self.inventario.agregar_producto("A-02", "Pan", "20", "8")
        self.inventario.agregar_producto("A-03", "Leche", "30", "0")

        bajos = self.inventario.productos_bajo_inventario(2)
        self.assertEqual([producto.clave for producto in bajos], ["A-03", "A-01"])

        self.inventario.establecer_umbral(0)
        bajos = self.inventario.productos_bajo_inventario()
        self.assertEqual([producto.clave for producto in bajos], ["A-03"])

    def test_historial_es_el_mas_reciente_primero(self):
        self.inventario.agregar_producto("A-01", "Café", "50", "10")
        primera = self.inventario.registrar_venta("A-01", "1")
        segunda = self.inventario.registrar_venta("A-01", "2")

        historial = self.inventario.historial_ventas()

        self.assertEqual([venta.id for venta in historial], [segunda.id, primera.id])


class PruebasPersistencia(InventarioBase):
    def test_los_cambios_sobreviven_al_reinicio(self):
        self.inventario.agregar_producto("A-01", "Café", "50", "10")
        self.inventario.registrar_venta("A-01", "4")
        self.inventario.establecer_umbral(3)

        recargado = Inventario(self.ruta)

        self.assertEqual(recargado.buscar("A-01").cantidad, 6)
        self.assertEqual(len(recargado.historial_ventas()), 1)
        self.assertEqual(recargado.umbral_bajo_inventario, 3)
        self.assertEqual(recargado.siguiente_id, 2)

    def test_archivo_danado_se_respalda(self):
        self.ruta.write_text("{ esto no es json", encoding="utf-8")

        inventario = Inventario(self.ruta)

        self.assertTrue(inventario.aviso_carga)
        self.assertEqual(inventario.listar_productos(), [])
        self.assertFalse(self.ruta.exists())


if __name__ == "__main__":
    unittest.main()
