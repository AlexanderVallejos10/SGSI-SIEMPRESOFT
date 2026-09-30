# Diseño del sistema (revisión v24)

Se revisó el diseño contra la guía de diseño de interfaces (frontend-design) y se corrigieron las señales típicas de una interfaz hecha con plantilla o con IA.

| Antes | Ahora |
|---|---|
| Etiquetas en MAYÚSCULAS sobre títulos, tablas, fichas y menú | Texto en minúscula normal; la jerarquía la da el tamaño y el peso de la letra |
| Datos unidos con puntos medios («A · B · C») | Frases normales con comas |
| Flechas «→» al final de los enlaces | El enlace dice lo que hace («Ver matriz») |
| Tipografía monoespaciada en etiquetas y códigos | Una sola familia, Instrument Sans, con cifras tabulares |
| Todo en tarjetas iguales, con el mismo radio y la misma sombra | Radios por jerarquía (paneles 10 px, controles 6 px, etiquetas 4 px), sin sombras decorativas |
| Apariciones animadas en cada sección y efectos al pasar el mouse en cada tarjeta, onda al presionar botones, pulso permanente | Movimiento solo como respuesta a una acción. En el tablero, un único momento: los gráficos se dibujan al cargar |
| Manchas de color difusas en el encabezado | Franja fina con los colores del logo, como en los documentos controlados de SiempreSoft |

## Elemento propio de SiempreSoft

El lenguaje de los **documentos controlados**: la franja con los colores del logo, el encabezado «Siempresoft EIRL / Uso interno» y los datos de control (documento, versión, elaboró, aprobó). La pantalla de ingreso lo retoma: documento para SGSI, nivel de confidencialidad «Uso interno» y el aviso de que cada ingreso queda registrado.

## Corregido también

En el tablero, el enlace «Editar» se superponía con «Cumple». Ahora está abajo a la derecha de cada tarjeta.
