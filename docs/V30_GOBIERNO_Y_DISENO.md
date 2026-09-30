# v30: gobierno del SGSI (ISO/IEC 27001 y 27005) y ajustes de diseño

## Módulos nuevos: «Gobierno del SGSI» en el menú

| Módulo | Qué hace | Requisito |
|---|---|---|
| **Revisión por la Dirección** | Arma las entradas solas con los datos reales: acciones de la revisión anterior, medidas correctivas, auditorías, incidentes, indicadores, objetivos, riesgos y estado del tratamiento. La Dirección escribe los cambios internos y externos, las partes interesadas, la retroalimentación, las mejoras y las conclusiones, y registra decisiones con responsable y plazo. **Solo el Gerente General la aprueba**; aprobada, queda cerrada y cada responsable recibe su decisión como aviso. Se imprime o guarda en PDF. | 9.3.2 y 9.3.3 |
| **Aceptación de riesgos** | Calcula el riesgo residual con la misma tabla 5 × 4 de la metodología, a partir de la probabilidad y la consecuencia residuales del tratamiento. El propietario acepta el riesgo o pide más tratamiento, con justificación. Si el nivel cambia, la aceptación vence sola. | 6.1.3 f; 27005 8.6 |
| **Revisión de accesos** | Cada acceso a un sistema se mantiene, se modifica o se revoca. La siguiente revisión queda programada a 90 días y cada decisión se guarda con quién la tomó. | Control 5.18 |
| **Declaración de Aplicabilidad** | Documento con encabezado de control. Por cada control del Anexo A muestra su aplicabilidad, justificación, implementación y madurez, los riesgos que trata y los documentos que lo sustentan. Se imprime o guarda en PDF. | 6.1.3 d |

**Criterio de aceptación (propuesta a confirmar en la metodología V0.10):**
- Muy bajo, Bajo y Medio: los acepta el propietario del riesgo.
- Alto y Muy alto: solo el Gerente General.

El criterio está en `apps/governance/services.py` (`ACCEPTANCE_RULE`) y se cambia en un solo lugar.

## Diseño

- **Barra superior despejada:** tema, color y vista compacta pasaron al menú del usuario («Apariencia»). La barra queda con conectados, notificaciones y usuario.
- **Sin anillos de plantilla:** hallazgos, activos por clase y controles ahora son barras ordenadas de mayor a menor, con el total arriba.
- **Accesibilidad:** cada gráfico se anuncia a los lectores de pantalla con el título de su tarjeta.
- **Textos:** se reescribieron los que sonaban a sistema.
- **Error corregido:** la tarjeta de factores usaba una escala de 4 aunque el Excel 2026 usa 6.
- **Componentes comunes:** las pantallas nuevas usan los mismos paneles, tablas, estados y formularios de Accesos y Perfil. La unificación de las pantallas antiguas se hace en la limpieza del código, al consolidar las hojas de estilo.
