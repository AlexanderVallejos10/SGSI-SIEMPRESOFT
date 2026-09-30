# Fotos de perfil, ingreso animado y tablero sobrio (v27)

## Fotos de perfil

- Cada persona cambia su foto en **Mi perfil**. El Gerente General y el Oficial de Seguridad pueden cambiar la de cualquiera desde **Accesos y permisos**, y la persona recibe un aviso.
- Sin foto se muestran las **iniciales del nombre y el apellido** (por ejemplo, MG).
- La foto aparece en la barra superior, en los conectados, en Accesos y en el perfil.
- **Seguridad:**
  - se aceptan solo JPG, PNG o WebP de hasta 5 MB, reconocidos por su contenido y no por la extensión;
  - con Pillow, la foto se vuelve a codificar a 512 × 512, lo que elimina metadatos (ubicación GPS, cámara) y cualquier contenido extraño;
  - el archivo recibe un nombre aleatorio y solo se ve con sesión iniciada;
  - cada cambio queda en la auditoría.

**Fotos iniciales.** Las de Milton Guevara, Karim Salazar, Fidel Espinoza y Jorge Contreras están en `apps/accounts/data/fotos/`, con nitidez mejorada (ampliación de calidad y enfoque suave, sin retocar los rostros). Las de Karim y Jorge están encuadradas en rostro y hombros para que se reconozcan en tamaño pequeño.

```
docker compose exec web python manage.py cargar_fotos_colaboradores
```

Agregue `apps/accounts/data/fotos/` al `.gitignore`: son fotos de personas.

**Pillow.** Se agregó a `requirements/base.txt`. Para instalarlo hay que reconstruir la imagen del contenedor:

```
docker compose build web
docker compose up -d
```

## Pantalla de ingreso

- **Los 93 controles del Anexo A** de la ISO/IEC 27001:2022, en un bloque por tema con los colores de la marca: organizacionales (37) en naranja, personas (8) en amarillo, físicos (14) en verde y tecnológicos (34) en tinta.
- **Al abrir**, los controles se verifican uno por uno.
- **Cada 2,8 segundos** uno se destaca y se lee su nombre, por ejemplo «A.8.24 Uso de criptografía».
- **Cada 7 segundos** una revisión recorre todos los controles.
- **Al pasar el mouse**, cada cuadro muestra su control.
- **Al presionar «Ingresar»**, una onda recorre los controles y los discos del isotipo saltan mientras se verifica.

Está hecho con la Web Animations API del navegador, el mismo motor que usan GSAP o Lottie, sin librerías externas. Se pausa si la pestaña está oculta y respeta la opción de reducir el movimiento. El isotipo usa el Lottie oficial si `static/vendor/lottie_light.min.js` existe.

## Tablero sobrio

- **Los datos van en grises de tinta.** El **rojo** se reserva para lo que no cumple o es de riesgo alto, y la **arena** para lo que requiere atención. El color de acento queda solo para enlaces y selección.
- **«Cumple» ya no va en verde**; solo «No cumple» se destaca.
- **El indicador de cada medición** es una barra fina de extremos rectos, con la meta como una línea delgada que la cruza.
- **Las escalas van de claro a oscuro** según la gravedad (Muy bajo, Bajo, Medio, Alto, Muy alto).
