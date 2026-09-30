# Cambio 02: riesgos según Karim, mapa interactivo, organigrama y cargador Lottie

## Riesgos (reunión con Karim)
- El tratamiento separa el **control del Anexo A** (ISO/IEC 27001:2022, 93 controles) de la actividad a implementar.
- Cada opción exige lo suyo:
  - Elección de controles: control del Anexo A.
  - Transferencia: tercero, responsabilidades del tercero, y contrato o evidencia.
  - Evitar: cómo se evita el riesgo.
  - Aceptar: justificación.
- El formulario de tratamiento muestra solo los campos de la opción elegida.
- Cada riesgo tiene un tipo de identificación: eventos, activos o proyecto. La matriz filtra por ese tipo.

## Importador
- Lee las columnas por el encabezado, así acepta la matriz 2026 (15 columnas) y la matriz modelo (19 columnas).
- Omite las filas en blanco que ya traen ID (R59–R76 en la matriz modelo).
- Recorta con aviso los textos que exceden el campo (R50 tiene 289 caracteres). El original queda en la fila fuente.
- Un ID existente se actualiza. El proceso se reubica y la evaluación anterior queda como historial.
- Orden de carga: primero la matriz 2026 y después la matriz modelo.
- Casos que quedan observados en vez de fallar:
  - «Ambos» se vincula a OSE, con observación.
  - «Facturación electrónica PSE» no tiene nodo en el mapa V0.15 y queda por vincular.
  - Los errores de tipeo en nombres de proceso se vinculan por similitud, con observación.

## Mapa de procesos
- Mismo aspecto que el PDF V0.15:
  - franjas con pestaña celeste;
  - marco rojo del alcance con su título;
  - cajas rectas, con línea discontinua para los procesos externos;
  - flechas verdes entre franjas;
  - leyenda de tres elementos.
- **Cliente / PSE** y **Cliente / PSE / SUNAT** son partes interesadas: nodos reales (categorías «entrada» y «salida») que envían y reciben flujos. Se pueden agregar otras, como proveedores, y aparecen como otra columna.
- Relaciones del PDF:
  - Cliente → OSE y Comercial.
  - Comercial → Éxito.
  - Éxito → OSE e Ingeniería.
  - Ingeniería ↔ Operaciones.
  - OSE, Éxito y Operaciones → SUNAT.
- Las líneas salen del borde de cada caja con tramos rectos. Una relación en ambos sentidos se dibuja como una sola flecha doble.
- La coordenada vertical se guarda relativa a la franja (migración `processes 0004`). Por eso:
  - cada franja crece según sus procesos;
  - el marco del alcance se calcula con los procesos marcados «dentro del alcance».
- Cambiar la categoría de un proceso (por ejemplo, de apoyo a operativo):
  - Al arrastrarlo desde el borde izquierdo de su caja, el aviso indica la nueva categoría; se confirma con «Guardar cambios».
  - Desde «Editar», se ubica solo en un lugar libre de la nueva franja.
  - En los dos casos las relaciones se conservan.
- Las partes interesadas no se pueden arrastrar a una franja de procesos.
- Cliente / PSE y Cliente / PSE / SUNAT se crean solos al migrar (`processes 0005`), con sus flechas, si todavía no existen.
- Relaciones desde el mapa:
  - Al pasar el mouse sobre una caja o una columna aparece un punto en su borde. Se arrastra hasta otro proceso para crear la flecha.
  - Un clic sobre una flecha permite retirarla.
  - En el panel de detalle, «Nueva relación desde aquí» abre el formulario con el origen ya elegido.
  - Una relación retirada se reactiva si se vuelve a crear.
- Las flechas de las partes interesadas bordean las cajas que tengan en el camino.
- Además:
  - distintivo de riesgos por proceso;
  - búsqueda (tecla /) y resaltados;
  - relaciones marcadas al pasar el mouse;
  - enlace directo `/procesos/?proceso=<id>`.

## Organigrama
- Solo cambia el tamaño de letra (`organization_refresh.css`): el diseño, los colores y las funciones son los mismos.
- Las funciones no cambian. Para volver al aspecto anterior, quite la línea de `organization_refresh.css` en `chart.html`.

## Cargador Lottie
- El dibujo es un escudo que se traza y un visto de validación: `static/lottie/sgsi-loader.json`.
- Aparece al navegar entre páginas si la carga tarda, y en el mapa mientras se organizan los procesos.
- Necesita `static/vendor/lottie_light.min.js`. Sin ese archivo se ve el mismo escudo animado en SVG, así que nada se rompe.
- Respeta la preferencia de movimiento reducido del sistema.

## Cláusulas 4 a 10 y Anexo A
- **Velocidad.** Cada página de cláusula hacía cientos de consultas: por cada documento sustentatorio volvía a leer todos los documentos, y un `select_related` anulaba la precarga. Ahora el índice de nombres se arma una vez y se reutiliza hasta que cambie algún documento o archivo (`apps/dashboard/selectors.py`).
- **PDF.** `artifact_view` entrega por rangos, así el visor muestra la primera página sin esperar el archivo completo. También envía ETag y caché privada de una hora, así un PDF ya abierto no se descarga otra vez (`apps/dashboard/file_serving.py`).
- **Matriz de requisitos** (`clause_detail.html`, `get_clause_matrix`):
  - La página se lee como la matriz VerificacionNorma: Cláusula, Descripción, Documento sustentatorio y Estado.
  - Las secciones (4., 4.1., 6.1.2.) van en gris y se pliegan; los requisitos a), b) y los subpuntos 1), 2) van sangrados.
  - Ahora se muestran también los documentos de las filas de sección, como 4.1 → Partes Interesadas o 8.2 → Cuadro de evaluación de riesgos, que antes el sistema omitía.
  - Arriba, una tarjeta por subcláusula con su avance; un clic filtra la matriz a esa subcláusula.
  - Filtros: búsqueda y Todos / Con documento / Falta documento.
  - Al elegir una fila, el panel lateral muestra:
    - el requisito completo y su estado;
    - cada documento con sus acciones: Ver (PDF en panel), Tabla, Ficha, Descargar;
    - los subpuntos, si los tiene;
    - lo que dice el Manual del SGSI.
  - Se navega con ↑ ↓ y cada fila tiene enlace directo (`#req-<id>`).
  - En una subcláusula (por ejemplo 4.1), el panel abre directamente con lo que se requiere.
- **Manual del SGSI v0.6** (`apps/dashboard/manual_sgsi.py`): cada cláusula muestra lo que exige el manual y enlaza al módulo donde se trabaja (organigrama, mapa, riesgos, Anexo A, documentos, auditorías). Si cambia el manual, se actualiza ese archivo.
- **Declaración de Aplicabilidad:**
  - el Anexo A muestra cuántos riesgos usa cada control;
  - avisa cuando un control figura como «no aplicable» y algún tratamiento lo elige;
  - la ficha de cada control lista los riesgos que lo justifican.
- **Menú lateral:** el número de cláusula va en columna, sin iconos de relleno.

## Manual v0.7, documentos y versiones
- **Guía por cláusula.** Se actualizó al Manual del SGSI v0.7 (14/09/2026). Incorpora la Política de IA, la protección de datos personales, la nube y los proveedores críticos, y las nuevas entradas de la revisión por la dirección.
- **Encabezado de cada cláusula.** Sigue el formato de sus documentos controlados: empresa, clasificación, documento de referencia, versión, fecha, quién elaboró y quién aprobó.
- **4.1 vacío en la matriz general.** La matriz solo miraba VerificacionNorma. Ahora también muestra los documentos asignados a cada sección desde la ficha del documento (`Document.sgsi_sections`), así 4.1 muestra lo mismo en la vista general y al entrar a 4.1.
- **Ficha de documento** (`document_detail.html`, `document_workspace.py`):
  - Vista previa de la versión vigente: el PDF se carga al abrir la pestaña, con el cargador; el Excel se ve como hoja.
  - Historial de versiones con estado, fecha, autor, motivo del cambio y archivos.
  - Trazabilidad con secciones del Manual y controles del Anexo A.
  - **Subir nueva versión** (arrastrar o elegir el archivo):
    - la versión, el estado y el motivo del cambio son obligatorios;
    - no se puede repetir un número de versión;
    - si la nueva queda «Vigente», la vigente anterior pasa a «Obsoleta» y queda en el historial;
    - los archivos de versión se sirven por rangos y con caché, igual que los artefactos.
- **Visor de Excel** (`_sheet_grid.html`, `read_xlsx_grid`): letras de columna y número real de fila como en Excel, pestañas de hojas abajo, encabezados fijos, números alineados a la derecha y búsqueda dentro de la hoja.

## Documentos que exige el Manual en cada numeral
- La página de cada numeral y la de «Todos los requisitos» muestran primero lo que exige el Manual del SGSI v0.7, con el formato de sus tablas: Documento, Ubicación según el Manual, En el sistema y Acciones.
- La lista sale solo del Manual (`MANUAL_DOCUMENTS` en `manual_sgsi.py`):
  - con su ubicación en 4.1, 4.2, 4.3, 8.2 y 8.3;
  - sin ubicación cuando el Manual solo menciona el documento en el texto (5.1, 6.1, 7.4, 9.2, etc.).
  - Nada se agrega de fuera del Manual.
- Cada documento se relaciona con los archivos de la empresa, en este orden:
  1. los documentos vigentes del módulo 4.1;
  2. las fichas de documentos;
  3. los archivos importados.
  - Si no hay coincidencia, figura como «No está cargado en el sistema».
- **Registrar y subir archivo:** crea la ficha del documento (código `MAN-<numeral>-NN`), la asigna al numeral y abre la subida de la primera versión.
- **Registrar para versionar:** si el archivo ya existe pero no tiene ficha, lo toma como primera versión vigente.
- En la matriz, el panel de cada sección muestra también lo que exige el Manual para ese numeral.

## Marco general y página por numerales
- **Menú lateral** (`base.html`, `shell.css`, `shell.js`):
  - Logo real de SiempreSoft; con el menú reducido queda solo el isotipo.
  - Íconos SVG propios de trazo fino (`partials/icons.html`), en lugar de los símbolos de texto.
  - El botón hamburguesa reduce el menú a íconos y números, y el sistema recuerda la elección.
  - En pantallas angostas el menú se abre sobre el contenido.
  - La página actual queda marcada y su cláusula abierta.
- **Barras de desplazamiento:** una sola, la de la página. La del menú es fina y solo aparece al pasar el mouse. Se quitaron los desplazamientos internos de la página de cláusulas.
- **Página de cláusula o numeral:** una tarjeta por numeral con lo que exige el Manual, su ubicación y el archivo en el sistema. Debajo, plegados, los requisitos de la norma de ese numeral según VerificacionNorma. Se quitaron las tarjetas, la matriz y el panel lateral que repetían la misma información.
- **Navegación:** una barra fija con los numerales (4.1, 4.2…) y su avance marca en cuál se está leyendo.
- **Movimiento:** las tarjetas aparecen suavemente al desplazarse y los requisitos se abren con altura animada. Se respeta «reducir movimiento» del sistema.

## Identidad SiempreSoft y animaciones
- Se eliminó «aValue» de la barra superior y del título del Dashboard. Quedan menciones solo en archivos `.bak`, que son copias antiguas y el sistema no usa.
- **Cargador de marca:** los tres discos del logo (naranja, amarillo y verde) suben en secuencia y se dibujan sus uniones.
  - Lottie en `static/lottie/sgsi-loader.json`; sin la librería queda el mismo dibujo en SVG.
- **Barra de progreso** fina en la parte superior, con los colores del logo, al cambiar de página. El cargador completo aparece solo si la carga pasa de 1,2 s.
- **Esqueleto de documento** (`partials/doc_skeleton.html`) mientras carga el visor de PDF, en la cláusula y en la ficha.
- **Botón ocupado:** al enviar un formulario, el botón muestra un giro circular y no admite un segundo clic.
- **Página por numerales:**
  - avance con barras que se llenan al entrar;
  - numerales como pestañas con su barra;
  - número del numeral sin recuadro;
  - títulos en mayúscula normal;
  - colores de SiempreSoft en lugar del azul genérico.
- **Menú:** el ícono se desplaza levemente al pasar el mouse, y la página actual se marca con el verde de la marca.

## Tema claro/oscuro, organigrama interactivo y visor de PDF (v11)
- **Tema** (`theme.css`, `theme.js`):
  - Usa `color-scheme` con `light-dark()`. Los colores fijos de todas las hojas de estilo se convirtieron a pares claro/oscuro con un script (`light-dark(claro, oscuro)`).
  - El selector de la barra superior ofrece claro, oscuro o sistema, y se guarda en el navegador.
  - El cambio se anima con la View Transitions API, como un círculo que se abre desde el botón.
  - Hay logo para fondo oscuro: `siempresoft-logo-dark.png`.
- **Barras de desplazamiento:** queda una sola, la de la página. El menú no muestra barra. Se quitaron las alturas máximas de 4.1, 4.2, el visor de Excel, el dashboard en vivo y la hoja de cálculo.
- **Organigrama** (`org_chart.js`, `org_chart.css`, `organization:position_trace`):
  - Lienzo sin cuadrícula que se encuadra solo al abrir.
  - Rueda o pellizco para acercar, arrastre para moverse, doble clic para encuadrar y teclas + − 0 y flechas.
  - Búsqueda con salto al resultado (Enter pasa al siguiente) y filtro por área.
  - Las ramas muestran cuántos puestos tienen a cargo.
  - Clic en un puesto:
    - resalta la cadena de mando;
    - abre un panel con personas, puestos a cargo, procesos (dueño o participa), riesgos, tratamientos, documentos de los que es propietario y autorizaciones.
- **Visor de PDF** (`partials/pdf_viewer.html`, `pdf_viewer.js`):
  - Usa PDF.js 5.6 (Mozilla, Apache 2.0), incluido en `static/vendor/pdfjs/`.
  - Barra propia con página, zoom, ajuste al ancho, pantalla completa, descarga y pestaña nueva. Ctrl + rueda también hace zoom.
  - Las páginas se dibujan a medida que se ven.
  - Si PDF.js no carga, usa el visor del navegador sin su barra.
  - Se usa en 4.1, en la ficha de documento y en el panel de las cláusulas.

## Versiones futuras y numerales como 4.1 (v12)
- **Nada queda atado a una versión.** Los nombres se comparan sin el número de versión ni marcas como «BORRADOR» o «(1)». Por eso «Metodologia…_V0.9», «…_V0.10» y un futuro «…_V0.11» se reconocen como el mismo documento. «ORGANIGRAMA V. 21» también se entiende.
- **Siempre gana la más reciente:**
  - si hay varios archivos sueltos del mismo documento, se muestra el de versión más alta (`version_rank`);
  - si el documento ya tiene ficha, manda su versión vigente.
- **Versión del Manual:** se toma del Manual cargado en el sistema (su ficha o el número en el nombre del archivo). La tabla indica de dónde sale; si no hay ninguno, usa la guía v0.7.
- **Lista de lo que exige el Manual:**
  - ahora está en la base de datos: `ManualDocumentRequirement`, migración `documents.0008`, cargada con lo del v0.7;
  - se edita en /admin/, en «Documentos exigidos por el Manual»;
  - cuando salga el Manual v0.8 se agregan, cambian o desactivan filas sin tocar código.
- **Numerales (4.3, 5.1, 6.1…)** con el mismo esquema que 4.1 (`_manual_doc_card.html`):
  - una tarjeta por documento, con archivo vigente, ubicación según el Manual y botones Abrir, Descargar y Subir nueva versión;
  - el PDF abierto en el visor o la vista previa del Excel;
  - historial de versiones.
- **Subir nueva versión:**
  - si el archivo existe pero aún no tiene ficha, se crea la ficha con ese archivo como versión vigente y se abre la subida de la nueva;
  - la anterior queda en el historial como obsoleta;
  - en 4.1 lleva a la subida propia de ese módulo.
- La vista «Todos los requisitos» de cada cláusula mantiene la tabla resumen.

## Pantalla de carga entre páginas (v13)
- Al cambiar de página aparece la pantalla con los tres discos de SiempreSoft y el texto «Cargando», en lugar de la línea de colores de la parte superior, que se retiró.
- La pantalla espera 200 ms antes de mostrarse, para no parpadear cuando la página siguiente carga al instante.
- Se ve en tema claro y oscuro, y los discos son algo más grandes que en el visor de documentos.

## Correcciones (v14)
- **Página 4.1 sin alguno de sus tres documentos:** ya no se cae con un error 500. El enlace «Subir nueva versión» solo se arma si el documento existe. Esto pasaba en la base de pruebas, que arranca vacía.
- **Pruebas:** usaban /sgsi/4.1/ y /sgsi/4.3/, pero en el sistema esas direcciones las atienden el módulo de contexto (4.1) y el mapa de procesos (4.3). Ahora las pruebas usan 4.4 y 6.1, que sí atiende la página de cláusulas.
- **Migraciones:** `scripts/entrypoint.sh` aplica las migraciones cada vez que arranca el contenedor. Por eso un `migrate` manual después de reiniciar dice «No migrations to apply», y no es un error.
