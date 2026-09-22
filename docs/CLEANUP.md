# Registro de limpieza estructural

Fecha: 2026-09-22. Base: ZIP SGSI-SIEMPRESOFT-main recibido para revisión.

## Cambios

- Retirados 32 scripts históricos de instalación, parche y reparación de la raíz.
- Renombrado `apps/dashboard/user_profile_v67.py` a `user_profile.py` y actualizado su import.
- Actualizados README, arquitectura y pendientes para describir el código existente.
- Añadida guía de mantenimiento y ampliadas exclusiones del contexto Docker.
- Conservados todos los modelos, migraciones, comandos de gestión, plantillas y recursos activos.

Los scripts retirados generaban o sobrescribían código que ya está presente en las apps.
No se encontraron referencias a ellos en el arranque o en los módulos de aplicación.
Algunos contienen documentos empresariales incrustados o instaladores anidados;
no se ejecutaron ni se incorporaron esas fuentes al nuevo código.
El ZIP original conserva íntegramente esos scripts y sus contenidos. En el repositorio
original, el historial anterior al commit de limpieza también permite recuperarlos.

Esta limpieza no cambia el esquema ni corrige las brechas funcionales y de permisos.
No elimina aplicaciones por tener nombres históricos ni afirma cumplimiento de auditoría.

## Inventario retirado

SHA-256 permite cotejar cada archivo con el respaldo original.

| Archivo | SHA-256 |
| --- | --- |
| `fix_controls_admin_v61b.py` | `75800a1d3ac4858d1aea20d94273c1834a770fbd97ebda4dab06f6b481d17bb5` |
| `fix_dashboard_duplicate_app.py` | `bb101172783f61b4d75d304e55ccb5f25fbff3e7b1ac87132e92b6bb02bb8746` |
| `install_context41_v69_1_full.py` | `71f1a1744c66793d8c71c91c6153bc1dc87e138d796a92496941746518bfdcd1` |
| `install_context42_v70.py` | `50c2ea0347d266577574d396a8b4f62ddf3bf6e19040b90c32ac6af1beca1176` |
| `install_context42_v70_3_like41.py` | `decca12c58d3cb1f0f1564e8adeddb71cc2c86df8eada86bcd2302f14f52b51c` |
| `install_dashboard_live_v72.py` | `4e5f2e5984e920f4da9f2d3c51bbae4a32074129729cdbea78a65179319e437c` |
| `install_dashboard_ui_v62c.py` | `2c553d994c6534910aed0056d963df45df5b3d6e1c18caa69d45c1ab628ce34b` |
| `install_mockup_ui_v63a.py` | `e76b6da31136180cd5f56e646d024658571c1cdf95d977a2591f7da2bface61f` |
| `install_organization_smartart_v66.py` | `2c77ba6b281905ee1ba878797416f2f7b31e79a36eea8ee86830a61e019c0bda` |
| `install_processes_v71_full.py` | `e224c689a5091c77c38c2807f2b990c8ec5036807fcecf51f9e485a51ae0b63c` |
| `install_siempresoft_product_v64.py` | `ec886de2f73945cf3791d2d6c5c1b2c71a621bc438b36037ad7f01ca54083f14` |
| `install_siempresoft_v65_focus1.py` | `db812bbc7f4d8e3d3d7682bb6b343cd938ed4ebf95e922a3c57ce1a23ae31efa` |
| `install_unified_dynamic_ui_v63b.py` | `c9776e8fe1dbe7bf65cafe2f4700115441b3e49334867aa5c87384aa83c052d3` |
| `install_user_profile_v67.py` | `214167e859ec47e229907ab4cf152faefbd92c7f9220ed5f6de8e27c93ab6c43` |
| `patch_context41_v69.py` | `25a765be36800e88cc27a9c2588eb8b4ea518cb7e195fb7bf532087b9c8c5ce8` |
| `patch_control_document_linking_v61c.py` | `317a840ea308c2d0742dc936aee573528336649a771160206ed9d36df3c28602` |
| `patch_controls_iso_v61.py` | `dcec96905fbaa2df4445acda53eb36eb8e70da585e4b6013c013a6bf3fd65faa` |
| `patch_dashboard_app_v62b.py` | `1250fda72f9f0206e20112f4247551fcd994aff3fb367dc795ddd7d402fbad0f` |
| `patch_document_protection_admin_v59.py` | `c779a74771ad57846873cc7b5dba0da35dd5fac29a3b251f261131d70dd7fe89` |
| `patch_documents_models_v58.py` | `b85e4f0c7f53fab8024d4ba5eb912a9daf89eee63314d276defac083d07b11bb` |
| `patch_documents_models_v58b.py` | `648a5825c91d221845efa775578af26db7eef839f9c5a6d56668e27841107f8f` |
| `patch_documents_models_v58c.py` | `e5efec2a37c88aaef7e0b552b72bd37ee832b280594871005912193aa4454492` |
| `patch_organization_v66.py` | `1efb8ef5769833fc738c27f62c2baddd9101cc7a5a8c80c4d0b9a250ec6a2122` |
| `patch_section_mapping_v60.py` | `10061a630531f9cf1452e5e966afb7acd2c5f23eb6f633229efbc5f49c550f31` |
| `patch_user_profile_v67.py` | `8fa0651711e962da46ef48c2342e3c728e77be0fed864350a32139a8c8e23f4f` |
| `repair_context42_v70_1.py` | `842bbe9f6d339d7a532387f7307d85359a37be46558813b61c000d3e8ef3704f` |
| `repair_context42_v70_2.py` | `581306d1ee0e33e405092c7faf66444887680217950dc2d5833bbe5d2ea0799c` |
| `repair_dashboard_live_v72_1.py` | `c5f9902dff0a0388fda5e715184e37a377284b1ed1c0f3f8832eb298cb4df2e0` |
| `repair_organization_v66_1.py` | `f71fcefb9aaaf1bbcaf4e5381832c5d349747675baa2af9b6a83c2e5c6d0f7d6` |
| `repair_organization_v66_2.py` | `9b2ba0a8c529435b133c31861da60ef7bcccb8cabf658c441b25286b52074950` |
| `repair_pdf_viewer_v69_2.py` | `7c0daa21bab4ed91d78d381ee64ece91be9e17c3f8974b4d1776db243673a26a` |
| `repair_v65_1.py` | `55717033d630057dd98a95d16c354a2fed1319ace4d9554e52c8ca2f577bb234` |

## Verificación de esta entrega

- Django `check`: sin incidencias.
- `makemigrations --check --dry-run`: sin cambios de esquema.
- Migraciones desde una base SQLite temporal vacía: correctas.
- Análisis sintáctico de Python y carga de todas las plantillas: correctos.
- Pruebas existentes: 9 aprobadas. Tres advertencias por no existir staticfiles
  en el entorno de pruebas; no se ejecutó collectstatic.
- No se probó el despliegue Docker ni PostgreSQL en esta sesión.
- Las pruebas existentes no acreditan todos los flujos funcionales o permisos.
