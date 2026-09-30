# Acceso al sistema, permisos, conexión y notificaciones (v24)

## Puesta en marcha

```
tar -xf ajustes_sgsi_karim_v24.zip
docker compose restart web
docker compose exec web python manage.py migrate
docker compose exec web python manage.py configurar_accesos
docker compose exec web python manage.py test apps.accounts apps.dashboard_live
```

`configurar_accesos`:
- sincroniza los roles;
- da al rol **Administrador SGSI** permiso para ver, crear y editar en todos los módulos;
- pone en ese rol al **Gerente General** y al **Oficial / Jefe de Seguridad de la Información**, según su puesto en el organigrama o su correo;
- asigna **Usuario / Colaborador** a quien no tenga rol;
- si esos dos no tienen contraseña, **muestra en la terminal su usuario y su contraseña temporal** (una sola vez).

Con esas credenciales ingresan en `/ingresar/`, crean su propia contraseña y generan las del resto del personal desde **Accesos y permisos**.

## Quién puede qué

| | Gerente General y Oficial de Seguridad (Administrador SGSI) | Demás colaboradores |
|---|---|---|
| Editar | Todo lo editable | Lo que den sus roles y las casillas de su ficha |
| Asignar roles y permisos con casillas | Sí | No |
| Generar o restablecer credenciales | Sí, a una persona o a varias marcadas | No |
| Ubicar personas en el organigrama | Sí, desde la ficha de cada persona | No |
| Cambiar su propia contraseña | Siempre que quiera | Una vez. Después, con una solicitud que aprueba un administrador |
| Ver quién está conectado | Sí | Sí |
| Ver su perfil, conexiones y permisos | Sí | Sí |

Protecciones:
- Nadie puede quitarse su propio rol de administrador ni desactivar su cuenta.
- Siempre queda al menos un administrador.

## Contraseñas

- **Generadas automáticamente.** El usuario se forma con el correo corporativo (`jtorres`). La contraseña temporal tiene 14 caracteres legibles, por ejemplo `Kx7m-Qp4t-Wz9r`, sin caracteres que se confunden (0/O, 1/l/I).
- Se muestran **una sola vez** al administrador (en pantalla y en un Excel que solo se puede descargar una vez). En la base de datos solo queda el cifrado (PBKDF2 de Django); nadie puede volver a leerla.
- **Al primer ingreso** el sistema no deja usar nada hasta que la persona crea su propia contraseña: al menos 10 caracteres, sin datos personales ni palabras comunes, con un indicador de seguridad mientras escribe.
- **Solicitud de cambio:** el colaborador explica el motivo y la solicitud llega como notificación al Gerente General y al Oficial de Seguridad. Si la aprueban, el sistema genera una contraseña temporal para entregar; si la rechazan, la persona recibe la nota.

## Seguridad del ingreso

- **Todas las páginas exigen sesión** (`LoginRequiredMiddleware` de Django 5). Una pantalla nueva nunca queda abierta por olvido.
- **Bloqueo por fuerza bruta:** con 5 intentos fallidos en 15 minutos (por usuario o por dirección IP), el ingreso se bloquea 15 minutos.
- **Cierre por inactividad** a los 30 minutos (configurable con `SGSI_IDLE_MINUTES`). La consulta automática del tablero no cuenta como actividad.
- La sesión dura como máximo 8 horas. En producción, las cookies solo viajan por HTTPS (`prod.py`).
- **Auditoría:** cada ingreso, salida, intento fallido, generación de credenciales, cambio de contraseña, solicitud y cambio de permisos queda en el registro de auditoría con usuario, fecha e IP.

## Tiempo de conexión y conectados

- Cada ingreso crea una **sesión** con hora de inicio, última actividad, hora de cierre y motivo (cerró sesión, inactividad), además de la IP y el navegador.
- La última actividad se guarda como máximo una vez por minuto, para no recargar la base de datos.
- **Conectado** = actividad en los últimos 2 minutos. La barra superior muestra quiénes están conectados, para cualquier usuario.
- El perfil muestra las últimas conexiones y el tiempo conectado en los últimos 7 y 30 días. La ficha de cada persona en Accesos muestra lo mismo.
- Las sesiones abandonadas (navegador cerrado sin salir) se cierran solas en el registro, sin tareas programadas aparte.

## Notificaciones

Llegan solas a la campana de la barra superior, con un aviso emergente, cuando:
- alguien pide cambiar su contraseña (a los administradores);
- se aprueba o rechaza esa solicitud (a quien la pidió);
- cambian los permisos de una persona;
- se generan sus credenciales;
- la ubican en el organigrama;
- cambia la versión del Manual del SGSI (a los administradores).

## Por qué «tiempo real» con consultas cada 25 segundos y no con WebSockets

Los WebSockets requerirían agregar Redis, Django Channels y un servidor ASGI: tres piezas más que mantener y que se pueden caer. Para un equipo de decenas de personas, la consulta periódica es la opción más estable:
- **Una sola consulta** (`/api/pulso/`) trae conectados, notificaciones y solicitudes pendientes, y a la vez marca la presencia.
- Se **pausa si la pestaña está oculta**.
- Si el servidor no responde, **reintenta cada vez más espaciado** (hasta 3 minutos).
- Funciona con la instalación actual (Django, PostgreSQL y el servidor web) sin servicios nuevos.

Si en el futuro el sistema crece a cientos de usuarios simultáneos, el mismo diseño de datos (sesiones y notificaciones en PostgreSQL) permite pasar a WebSockets sin rehacer nada.

## Versión del Manual del SGSI

- La versión que aparece en cada cláusula ya no se adivina por el nombre del archivo. **Antes aparecía «0.2 (borrador)», que no era la versión real.**
- Ahora es un dato registrado. El punto de partida es la **v0.7 (borrador)**; la vigente del repositorio es la V0.6.
- Los administradores la cambian con **«Cambiar versión»** en cualquier cláusula: documento, versión, estado, fecha, elaboró, aprobó y **qué cambió**. Cada cambio queda en el historial y en la auditoría, y se avisa a los demás administradores.
