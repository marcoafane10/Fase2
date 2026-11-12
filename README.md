# Biblioteca Digital de Instrucciones · Impresos Múltiples

Reto de Socio Formador: **Impresos Múltiples**. Tarea 3: subida de archivos y mejoras.

**Integrantes:** Marco Afane, Ever Gómez, Moisés Morán, Luis Mejía, Rodrigo Alvarenga

**Video de pruebas (YouTube):** PENDIENTE: pegar aquí el enlace del video

## Qué hace el sistema
Administra las instrucciones de trabajo de la planta. Cada instrucción tiene un **documento (PDF o Word)** que se guarda dentro de MySQL y un **enlace a su video**. Subir de nuevo el documento crea una **versión nueva** sin borrar las anteriores, y cada versión se puede descargar. El sistema permite registrar, consultar, modificar, archivar y eliminar instrucciones, y muestra un **resumen** de cuántas instrucciones ya tienen documento y video y a cuántas les falta alguno.

## Cómo ejecutarlo desde cero
1. Instalar [XAMPP](https://www.apachefriends.org/) y encender **Apache** y **MySQL** desde el panel de XAMPP.
2. Subir el límite de paquetes de MySQL para aceptar archivos de hasta 10 MB: en XAMPP, botón **Config** de MySQL → `my.ini`, cambiar `max_allowed_packet=1M` por `max_allowed_packet=16M` (sección `[mysqld]`) y reiniciar MySQL. *(Si se olvida este paso, `app.py` intenta ajustarlo solo al iniciar.)*
3. Abrir http://localhost/phpmyadmin:
   1. Pestaña **Bases de datos** → crear la base `biblioteca_instrucciones` con cotejamiento `utf8mb4_unicode_ci`.
   2. Seleccionarla en el panel izquierdo → pestaña **Importar** → elegir `crear_bd.sql` → **Importar**.

   Se crean las tablas con 8 instrucciones de ejemplo. *(Si se importa sin seleccionar la base, el script la crea igual, pero phpMyAdmin muestra avisos "#1046 Base de datos no seleccionada" al listar las consultas; con la base seleccionada no aparece ninguno.)*
4. Instalar las dependencias y ejecutar el sistema:
   ```
   pip install -r requirements.txt
   python app.py
   ```
   (En Windows, si `python` no funciona, usar `py`.)
5. Abrir en el navegador:
   - http://127.0.0.1:5000/instrucciones (listado)
   - http://127.0.0.1:5000/instrucciones/1/documentos (versiones del documento y subida)
   - http://127.0.0.1:5000/resumen (resumen)

Para probar la subida se pueden usar los archivos de `documentos_prueba/` (contenido inventado; nunca se suben documentos reales).

La conexión usa `root` sin contraseña en `localhost:3306`, como trae XAMPP. Si su MySQL es distinto, se cambia con las variables de entorno `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` y `MYSQL_DATABASE`.

## Estructura de archivos
```
app.py               # rutas de Flask, validaciones, versiones, estados y descarga
crear_bd.sql         # crea la base y las tablas en MySQL (se importa en phpMyAdmin)
requirements.txt     # Flask y mysql-connector-python
pruebas.py           # ejecuta los 19 casos de prueba sobre una base aparte (biblioteca_pruebas)
armar_pdf.py         # arma el PDF de pruebas con las capturas de capturas/
documentos_prueba/   # PDF y Word inventados para las pruebas
capturas/            # capturas del navegador y de phpMyAdmin usadas en el PDF
templates/           # base, instrucciones, nueva, documentos, editar, resumen y 404
static/style.css     # única hoja de estilos del sitio
static/modal.js      # ventana modal para errores y confirmaciones
static/logo_im.png   # logo de Impresos Múltiples
```

## Rutas
| Ruta | Método | Qué hace |
|---|---|---|
| `/` | GET | Redirige al listado |
| `/instrucciones` | GET | Listado con documento, video y estado. Acepta `?q=` (título o nombre de archivo), `?proceso=`, `?documento=` y `?estado=archivada` |
| `/instrucciones/nueva` | GET / POST | Registrar una instrucción, con documento y video opcionales |
| `/instrucciones/<id>/documentos` | GET / POST | **Nueva:** lista todas las versiones del documento y sube una versión nueva |
| `/documentos/<id>/descargar` | GET | **Nueva:** descarga esa versión con su nombre original; 404 si no existe |
| `/instrucciones/editar/<id>` | GET / POST | Nueva versión de la instrucción, editar título y proceso, cambiar el enlace del video |
| `/instrucciones/archivar/<id>` | POST | Archivar o restaurar |
| `/instrucciones/eliminar/<id>` | POST | Eliminar la instrucción y, por la llave foránea, todos sus documentos |
| `/instrucciones/exportar.csv` | GET | Descargar el listado en CSV (se abre en Excel) |
| `/resumen` | GET | Recorre las instrucciones y las clasifica por documento y video |

## Base de datos (MySQL: `biblioteca_instrucciones`)
**instrucciones** (tabla padre): `id` INT PK, `titulo` VARCHAR(150), `proceso` VARCHAR(80), `version` INT, `fecha_actualizacion` DATE, `estado` ENUM('activa','archivada')

**historial_versiones**: `id` INT PK, `instruccion_id` INT → `instrucciones.id` (ON DELETE CASCADE), `version` INT, `fecha` DATE

**documentos** (tabla de archivos, nueva):

| Campo | Tipo | Para qué |
|---|---|---|
| `id` | INT, PK | Identifica cada versión subida |
| `instruccion_id` | INT, **FOREIGN KEY → instrucciones.id ON DELETE CASCADE** | Instrucción a la que pertenece |
| `version` | INT | 1, 2, 3… (única por instrucción) |
| `nombre_original` | VARCHAR(255) | Nombre con el que se subió y con el que se descarga |
| `tipo_mime` | VARCHAR(100) | PDF o Word |
| `tamano` | INT | Tamaño en bytes |
| `contenido` | **LONGBLOB** | El archivo |
| `enlace_video` | VARCHAR(500), opcional | Enlace del video de la instrucción (el video no se sube) |
| `fecha_subida` | DATETIME | Cuándo se subió |

Todas las sentencias usan parámetros `%s`; nunca se concatena texto del usuario. Los listados **no traen la columna `contenido`**: solo la consulta de descarga la pide.

## Archivos permitidos y validaciones
- Tipos: **.pdf, .doc y .docx** (sin importar mayúsculas). Además se revisa que el contenido corresponda a la extensión.
- Tamaño máximo: **10 MB** (requiere `max_allowed_packet=16M`, paso 2).
- Antes de guardar se verifica que se eligió un archivo, que no está vacío, su tipo, su tamaño y que el enlace del video (si se escribe) empiece con `http://` o `https://`. Si algo falla, no se guarda nada y el error aparece en una **ventana modal del sistema** (`static/modal.js`), no en una ventana del navegador. Eliminar también pide confirmación en ese modal.

## Cómo funcionan las versiones y los estados
- Al subir, `SELECT MAX(version)` obtiene la última versión de esa instrucción: si no hay ninguna la nueva es la 1; si hay, es la última + 1. Siempre se **inserta** una fila nueva: la anterior se conserva.
- En `/instrucciones/<id>/documentos` las versiones se listan de la más reciente a la más antigua y un `if/elif/else` decide el estado de cada una: la más reciente es **vigente** y las anteriores son **obsoletas**.

## Cómo funciona el resumen
`/resumen` lee las instrucciones activas con su documento más reciente y las recorre con un `for`. En cada vuelta un `if/elif/else` decide:
- tiene documento y enlace de video → **completa**
- tiene documento pero no video → **falta video**
- cualquier otro caso → **sin documento**

Cada clasificación suma a su contador general y al de su proceso; al final se calculan los porcentajes.

## Mejoras individuales
| Integrante | Usuario de GitHub | Mejora |
|---|---|---|
| Marco Afane | [@marcoafane10](https://github.com/marcoafane10) | Buscador por título **o nombre de archivo** y filtros por proceso y por estado del documento |
| Ever Gómez | [@evergom1306-dotcom](https://github.com/evergom1306-dotcom) | Porcentajes, barra de distribución y resumen por proceso |
| Luis Mejía | [@mejialuissv-prog](https://github.com/mejialuissv-prog) | Archivar y restaurar instrucciones conservando sus documentos |
| Rodrigo Alvarenga | [@RodrigoAlvarenga-prog](https://github.com/RodrigoAlvarenga-prog) | Editar título y proceso, y cambiar el enlace del video del documento vigente |
| Moisés Morán | [@Moises-JPG](https://github.com/Moises-JPG) | Migración a MySQL con subida, versiones y descarga de documentos, y exportar el listado a CSV con la versión del documento |

## Pruebas
`python pruebas.py` ejecuta 19 casos sobre una base aparte (`biblioteca_pruebas`), sin tocar los datos reales: subida de PDF y Word, tipo no permitido, archivo demasiado grande, vacío o sin archivo, versión 2, estados, descarga, 404, enlace inválido, resumen, eliminación en cascada, errores en ventana modal y una prueba por cada mejora individual. El documento PDF con capturas se arma con `python armar_pdf.py`.
