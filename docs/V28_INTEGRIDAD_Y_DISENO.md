# v28: una persona, un código; color unificado; ingreso con GSAP

## Personas y activos duplicados

**Qué pasaba.** El paso de unificación anterior solo cubría a los colaboradores creados por la carga (código `COL-`). Si una persona ya existía con otro nombre o código («Milton Guevara» y «Milton Guevara Santisteban»), podían quedar dos cuentas: la foto en una, y el puesto del organigrama o los activos en la otra. Además, varias pantallas dibujaban sus propias iniciales en lugar de la foto, y la persona figuraba «por verificar» aunque ya tuviera acceso.

**Qué se hizo.**

1. **`python manage.py unificar_personas`** muestra qué cuentas y activos son duplicados; con `--aplicar` los unifica:
   - Misma persona = mismo correo, o el mismo primer nombre y al menos un apellido en común («Milton Guevara» = «Milton Guevara Santisteban»; «Milton Pérez» no).
   - Queda la cuenta con más uso real: contraseña o ingresos, rol de administrador, correo, foto y código propio.
   - Todo lo que apuntaba a la duplicada pasa a la que queda: puestos, activos, movimientos, riesgos, auditoría, sesiones, roles y permisos. Se completan datos vacíos (por ejemplo, el apellido más completo) y la duplicada se elimina.
   - Si dos cuentas del grupo tienen contraseña propia y correos distintos, no se tocan: se informan para revisarlas a mano.
   - Activos con códigos equivalentes (SS1-CPU-012 y SS1-CPU-12) se unifican igual, con sus movimientos y revisiones.
   - Todo ocurre en una transacción y queda en la auditoría.
2. La **carga total** (`cargar_todo_siempresoft`) usa la misma unificación, y el cargador de activos reconoce códigos equivalentes. Volver a cargar nunca recrea duplicados.
3. **La foto o las iniciales aparecen en todas partes**: organigrama, activos (lista y ficha), perfil, conectados, accesos y barra superior. Todo enlaza al mismo perfil.
4. **«Por verificar» se resuelve solo:** al generar credenciales o guardar permisos, la persona queda «Activo» y verificada. Una migración marca así a quien ya recibió credenciales o ya ingresó.

## Tablero

- **La posición estratégica se verificó con el Excel 2026 real.** MEFI 4,79 (fortalezas 3,79 y debilidades 1,00) y MEFE 6,17 (oportunidades 3,17 y amenazas 3,00). Resultado: **posición fuerte para crecer y construir**.
- **Error corregido:** el tablero tenía los ejes invertidos respecto de la hoja EFIEFE de Karim. Ahora el eje horizontal es EFE (6 a la izquierda) y el vertical es EFI (6 arriba), como en el Excel.
- **Error corregido:** el comando antiguo `seed_dashboard_live` cargaba el Excel de 2021 («_3») con la etiqueta «2026». Ahora usa el Excel 2026 y toma la versión del nombre del archivo. La carga total reetiqueta las versiones mal marcadas.
- **Colores:**
  - verde para lo que cumple y para los niveles bajos, ámbar para lo medio, rojo para lo alto;
  - las series de datos usan el **color elegido en la barra superior**.

## Un solo color en todo el sistema

164 colores azules fijos y 17 transparencias azules, repartidos en 21 hojas de estilo (organigrama, procesos, cláusulas, registros, activos, contexto, documentos), se reemplazaron por el color de acento. Todas las pantallas siguen la paleta elegida (verde SiempreSoft por defecto).

## Pantalla de ingreso

- Vuelve la composición de la v26, ahora con movimiento:
  - la franja se dibuja y el título entra palabra por palabra;
  - el isotipo de SiempreSoft en gran tamaño cae con rebote, flota y sigue al puntero;
  - el isotipo del formulario salta cada pocos segundos;
  - el botón es magnético;
  - el formulario se sacude si la contraseña es incorrecta;
  - los discos saltan mientras se verifica.
- **GSAP**, el estándar profesional de animación web (gratuito, con SplitText y DrawSVG), y **Lottie** se instalan una sola vez:

```
docker compose exec web python manage.py instalar_recursos_visuales
```

Quedan dentro del sistema, en `static/vendor/`, con su huella SHA-256 registrada: si alguien altera un archivo, el comando lo detecta. Sin ellos, la pantalla usa una versión equivalente con la animación nativa del navegador.
