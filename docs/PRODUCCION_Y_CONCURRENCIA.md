# Cómo atiende el sistema a varios usuarios a la vez (v26)

## En pocas palabras

- **Procesos e hilos (Gunicorn).** En producción, el sistema corre con varios procesos independientes y cada uno con 4 hilos: en un servidor de 2 a 4 núcleos atiende de 20 a 36 solicitudes a la vez. Si un proceso falla, los demás siguen y Gunicorn lo reemplaza solo.
- **Transacciones (PostgreSQL).** Cuando dos personas guardan al mismo tiempo, la base de datos resuelve el orden. Cada guardado importante va en una transacción: o se guarda completo o no se guarda. Algunas reglas las impone la propia base de datos, por ejemplo que cada persona tenga un solo puesto principal vigente o que haya una sola versión vigente del Manual.
- **Sesiones en la base de datos.** Cada usuario tiene su propia sesión. No importa qué proceso atienda cada clic.
- **«Tiempo real» sin conexiones abiertas.** Conectados y notificaciones se consultan cada 25 segundos con una solicitud muy pequeña. No hay conexiones permanentes que se caigan ni servicios adicionales.

## Desarrollo o producción

| | Desarrollo (hoy) | Producción |
|---|---|---|
| Comando | `docker compose up` | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` |
| Servidor | `runserver`: 1 proceso con hilos, para programar | Gunicorn: varios procesos con 4 hilos cada uno (`gunicorn.conf.py`) |
| Configuración | `config.settings.dev` | `config.settings.prod`: DEBUG apagado, cookies solo por HTTPS, redirección a HTTPS |
| Archivos estáticos | Los sirve Django | Se recopilan al arrancar y los sirve WhiteNoise |
| Salud | — | Revisión cada 30 s; si no responde, Docker lo reinicia |
| Respaldo | — | `pg_dump` diario en el volumen `db_backups`, 14 días |

**HTTPS es obligatorio en producción.** La configuración de producción redirige a HTTPS, así que el sistema debe publicarse detrás de un proxy con certificado (Nginx, Caddy o Azure Application Gateway).

**Respaldo fuera del servidor.** Los respaldos quedan en un volumen del mismo servidor; hay que copiarlos a otro lugar (por ejemplo, un almacenamiento de Azure) y probar una restauración cada mes:

```
docker compose exec backup sh -c "ls -lh /backups"
docker compose exec -T db pg_restore -U <usuario> -d <base_de_prueba> --clean < sgsi_AAAAMMDD_HHMM.dump
```

## Animación Lottie de la pantalla de ingreso

La pantalla de ingreso usa la animación oficial `static/lottie/sgsi-loader.json`. Para reproducirla hace falta la librería, que se descarga una sola vez:

```
curl -L -o static\vendor\lottie_light.min.js https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie_light.min.js
```

Sin la librería, la pantalla muestra la misma animación hecha en SVG. Con ella, también el cargador entre páginas usa el Lottie.
