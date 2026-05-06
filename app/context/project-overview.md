# Project Overview: Sistema de Subastas

## Resumen Ejecutivo

Aplicación móvil para la participación online en subastas y la consignación de artículos[cite: 3]. El sistema opera bajo la modalidad de subasta dinámica ascendente[cite: 9], conectando postores verificados con el catálogo de la empresa.

## Core Business Logic

- **Mecanismo de Subasta:** Se parte de un precio base y gana el mayor postor[cite: 6].
- **Reglas de Puja:** Las ofertas deben superar la mejor puja en al menos un 1% del valor base, con un tope máximo del 20% (límites que no aplican a categorías oro y platino)[cite: 33, 35, 37].
- **Categorización de Usuarios:** Los usuarios pasan por una verificación externa y se clasifican en: común, especial, plata, oro y platino[cite: 13, 14]. Esta categoría, junto con la validación de medios de pago, define a qué subastas pueden acceder[cite: 24, 25].
- **Medios de Pago:** Soporte para cuentas bancarias, tarjetas de crédito y cheques certificados[cite: 17]. Si un usuario no posee los fondos al ganar, se le aplica una multa del 10% del valor ofertado[cite: 45].
- **Consignación:** Los usuarios pueden proponer artículos (mínimo 6 fotos y declaración de origen lícito)[cite: 54, 55, 56]. Si se acepta, la empresa fija un precio base, comisión y un seguro asociado a la póliza[cite: 63, 69].

## Fases de Entrega

1. Maquetado, wireframes (Figma) y diseño de API (Swagger)[cite: 76, 77, 79].
2. Backend y Frontend al 50% con al menos un circuito integrado[cite: 82, 83].
3. Aplicación 100% funcional y trazable con backend en línea[cite: 86, 87, 89].
