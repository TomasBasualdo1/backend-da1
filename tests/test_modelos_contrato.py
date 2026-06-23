import unittest
from datetime import date, datetime, time
from app.schemas import (
    EstadoMulta,
    EstadoSubasta,
    EstadoPago,
    EstadoSesionSubasta,
    EstadoArticulo,
    EstadoEvaluacionArticulo,
    EstadoVerificacionMedioPagoInput,
    TipoNotificacion,
    TipoStreamEvent,
    SubastaDetallePublica,
    SubastaDetalle,
    SubastaListadoPublico,
    SubastaListado,
    ItemCatalogoPublico,
    ItemCatalogo,
    Moneda,
    Subastado,
    StreamEvent,
)


class TestModelosContrato(unittest.TestCase):
    def test_imports_startup(self):
        # Verify that all renamed schemas can be imported and are defined
        self.assertIsNotNone(EstadoMulta)
        self.assertIsNotNone(EstadoSubasta)
        self.assertIsNotNone(EstadoPago)
        self.assertIsNotNone(EstadoSesionSubasta)
        self.assertIsNotNone(EstadoArticulo)
        self.assertIsNotNone(EstadoEvaluacionArticulo)
        self.assertIsNotNone(EstadoVerificacionMedioPagoInput)
        self.assertIsNotNone(TipoNotificacion)
        self.assertIsNotNone(TipoStreamEvent)

    def test_enum_valid_values(self):
        # Validate that enums accept canonical database values
        self.assertEqual(EstadoMulta.pendiente.value, "pendiente")
        self.assertEqual(EstadoMulta.pagada.value, "pagada")

        self.assertEqual(EstadoSubasta.abierta.value, "abierta")
        self.assertEqual(EstadoSubasta.cerrada.value, "cerrada")

        self.assertEqual(EstadoPago.pendiente.value, "pendiente")
        self.assertEqual(EstadoPago.pagado.value, "pagado")
        self.assertEqual(EstadoPago.vencido.value, "vencido")

        self.assertEqual(EstadoSesionSubasta.activa.value, "activa")
        self.assertEqual(EstadoSesionSubasta.finalizada.value, "finalizada")

        self.assertEqual(EstadoArticulo.pendiente.value, "pendiente")
        self.assertEqual(EstadoArticulo.en_inspeccion.value, "en_inspeccion")
        self.assertEqual(EstadoArticulo.aprobado.value, "aprobado")
        self.assertEqual(EstadoArticulo.rechazado.value, "rechazado")
        self.assertEqual(EstadoArticulo.devuelto.value, "devuelto")

        self.assertEqual(EstadoEvaluacionArticulo.aprobado.value, "aprobado")
        self.assertEqual(EstadoEvaluacionArticulo.rechazado.value, "rechazado")

        self.assertEqual(EstadoVerificacionMedioPagoInput.validado.value, "validado")
        self.assertEqual(EstadoVerificacionMedioPagoInput.rechazado.value, "rechazado")

        self.assertEqual(TipoNotificacion.pago.value, "pago")
        self.assertEqual(TipoNotificacion.subasta.value, "subasta")
        self.assertEqual(TipoNotificacion.sistema.value, "sistema")

        self.assertEqual(TipoStreamEvent.puja.value, "puja")
        self.assertEqual(TipoStreamEvent.item.value, "item")
        self.assertEqual(TipoStreamEvent.cierre.value, "cierre")

    def test_detalle_publico_item_no_vendido(self):
        # detail public with item not sold passes through SubastaDetallePublica and serializes subastado: "no"
        item = ItemCatalogoPublico(
            id=1,
            descripcion="Item de prueba",
            mejorOfertaActual=150.0,
            subastado=Subastado.no,
            fotos=["https://example.com/item.jpg"]
        )
        detalle = SubastaDetallePublica(
            id=10,
            fecha=date(2026, 7, 20),
            hora=time(14, 0, 0),
            estado=EstadoSubasta.abierta,
            categoria="comun",
            ubicacion="Buenos Aires",
            moneda=Moneda.ARS,
            catalogo=[item]
        )
        serialized = detalle.model_dump(mode="json")
        self.assertEqual(serialized["catalogo"][0]["subastado"], "no")
        self.assertEqual(serialized["moneda"], "ARS")

    def test_detalle_autenticado_item_vendido_y_no_vendido(self):
        # detail authenticated with item sold/unsold passes through SubastaDetalle
        item_no_vendido = ItemCatalogo(
            id=1,
            descripcion="Item 1",
            precioBase=100.0,
            mejorOfertaActual=120.0,
            limiteMinimo=101.0,
            limiteMaximo=120.0,
            subastado=Subastado.no,
            fotos=[]
        )
        item_vendido = ItemCatalogo(
            id=2,
            descripcion="Item 2",
            precioBase=200.0,
            mejorOfertaActual=250.0,
            limiteMinimo=201.0,
            limiteMaximo=250.0,
            subastado=Subastado.si,
            fotos=[]
        )
        detalle = SubastaDetalle(
            id=10,
            fecha=date(2026, 7, 20),
            hora=time(14, 0, 0),
            estado=EstadoSubasta.abierta,
            categoria="oro",
            ubicacion="Buenos Aires",
            moneda=Moneda.USD,
            catalogo=[item_no_vendido, item_vendido]
        )
        serialized = detalle.model_dump(mode="json")
        self.assertEqual(serialized["catalogo"][0]["subastado"], "no")
        self.assertEqual(serialized["catalogo"][1]["subastado"], "si")

    def test_listados_moneda_real(self):
        # public and authenticated listings serialize with database currency, not hardcoded to USD
        listado_ars = SubastaListado(
            id=1,
            fecha=date(2026, 7, 20),
            hora=time(14, 0, 0),
            estado=EstadoSubasta.abierta,
            categoria="comun",
            ubicacion="Buenos Aires",
            moneda=Moneda.ARS
        )
        listado_publico_usd = SubastaListadoPublico(
            id=2,
            fecha=date(2026, 7, 21),
            hora=time(15, 0, 0),
            estado=EstadoSubasta.cerrada,
            categoria="especial",
            ubicacion="Online",
            moneda=Moneda.USD
        )
        self.assertEqual(listado_ars.model_dump(mode="json")["moneda"], "ARS")
        self.assertEqual(listado_publico_usd.model_dump(mode="json")["moneda"], "USD")

    def test_stream_event_cierre(self):
        # StreamEvent accepts type: 'cierre'
        event = StreamEvent(
            type=TipoStreamEvent.cierre,
            fechaHora=datetime(2026, 6, 23, 12, 0, 0),
            data=None
        )
        self.assertEqual(event.type, TipoStreamEvent.cierre)
        self.assertEqual(event.model_dump(mode="json")["type"], "cierre")


if __name__ == "__main__":
    unittest.main()
