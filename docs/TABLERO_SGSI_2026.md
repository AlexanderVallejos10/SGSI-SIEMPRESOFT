# Tablero del SGSI (v22)

## Tecnologías que usa, y dónde se ven

| Tecnología | Dónde se ve |
|---|---|
| **D3.js v7.9** (incluido en `static/vendor/d3`, funciona sin internet) | Todos los gráficos: barras apiladas de incidentes, líneas con área de medidas, mapa de calor de riesgos, donas, barras agrupadas de OSI, matriz EFI/EFE y micrográficos de los indicadores clave |
| **API JSON y carga asíncrona** | La página aparece al instante con **esqueletos animados**. Los datos llegan por `/dashboard-sgsi/datos.json` |
| **Actualización en tiempo real** | Consulta la API cada 30 s (se pausa si la pestaña está oculta). Si algo cambió, redibuja con transición y muestra una **notificación** («Incidentes: 93 → 94»). Indicador «En vivo» arriba |
| **Web Animations API** | Aparición escalonada de cada sección al hacer scroll, filtro de OESI con reacomodo animado (técnica FLIP), notificaciones |
| **Carga diferida (lazy loading)** | Cada sección se dibuja solo cuando entra en pantalla, y una sola vez |
| **Microinteracciones** | Onda al presionar botones, tooltips en cada gráfico, leyendas que ocultan o muestran series, resaltado en cruz (fila y columna) en las matrices, celdas que rebotan al cambiarlas, halo pulsante en la posición estratégica |
| **Glassmorphism** | Barra superior fija de vidrio esmerilado (`backdrop-filter`), con pestañas e indicador deslizante |
| **Paralaje** | El fondo del encabezado se mueve más lento que el contenido |
| **Temas personalizables** | Claro, oscuro o del sistema (ya existentes) **más color de acento** (verde SiempreSoft, azul, naranja, violeta) y **densidad** (cómoda o compacta), guardados en el navegador |
| **Tipografía moderna** | **Instrument Sans** para la interfaz y **Geist Mono** para códigos, incluidas en `static/fonts` (licencia OFL). Escala fluida con `clamp()` y números tabulares |
| **Diseño responsivo** | CSS Grid con `minmax(0, 1fr)` y **container queries**: cada tarjeta se adapta a su propio ancho. Probado a 1440 px y a 390 px (celular) sin desbordes |
| **Rendimiento y accesibilidad** | La API devuelve una «versión» del contenido: si no cambió nada, responde en pocos bytes y no se redibuja. Solo se redibuja al cambiar el ancho. Respeta «reducir movimiento» del sistema operativo |

**Nota honesta:** GSAP y Chart.js no se pudieron incluir porque este entorno no tiene internet para descargarlos. La misma función la cumplen D3.js (gráficos) y la Web Animations API nativa del navegador (animaciones), que no dependen de nada externo. Tampoco se usan WebSockets: requieren Django Channels y un servidor Redis. La consulta cada 30 s con versión logra el mismo efecto con la infraestructura actual.

## Qué muestra

1. **Resumen:** seis indicadores clave con su micrográfico:
   - indicadores del SGSI y OESI, con un segmento verde o rojo por cada uno;
   - riesgos por nivel;
   - tendencia anual de incidentes;
   - tendencia de medidas implementadas;
   - cobertura documental.
2. **Indicadores del SGSI** (hoja «Dashboard SGSI»): valor, meta, gráfico de viñeta, si conviene subir o bajar, responsable, periodo y plan de acción.
3. **OESI:** los 9 objetivos, con un filtro Todos / Cumplen / No cumplen.
4. **Estado del SGSI:** mapa de calor de riesgos, incidentes por año y severidad, medidas por año, hallazgos de auditoría, activos, documentos del Manual, controles del Anexo A y vulnerabilidades.
5. **Alineación:** puntaje por OSI y las matrices OEE y EPI vs OSI, editables con un clic.
6. **Posición estratégica:** matriz EFI/EFE (escala del Excel) y factores MEFI/MEFE.

## Archivos

- `apps/dashboard_live/views.py`: `home` (armazón) y `dashboard_data` (API).
- `apps/dashboard_live/overview.py`: estado de los módulos, en caché 5 minutos.
- `apps/dashboard_live/importer.py`: lectura adaptable del Excel (2021 y 2026).
- `templates/dashboard_live/home.html`, `static/css/sgsi_dashboard.css` y `static/js/sgsi_dashboard.js`.
- `static/vendor/d3/` (licencia ISC) y `static/fonts/` (licencia OFL).
