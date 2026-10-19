# Biblioteca Digital de Instrucciones de Trabajo - Fase 2
Reto de Socio Formador: **Impresos Múltiples**.

**Integrantes:** Marco Afane, Ever Gómez, Moisés Morán, Luis Mejía, Rodrigo Alvarenga

## Qué hace el sistema
Administra las instrucciones de trabajo de la planta y el historial de versiones de cada una. Permite **registrar, consultar, modificar (actualizar la versión) y eliminar** instrucciones, y muestra un **resumen** que recorre todas las instrucciones y las clasifica como **vigentes** o **desactualizadas** según su versión.

## Cómo ejecutarlo
```
pip install -r requirements.txt
python crear_bd.py
python app.py
```
(En Windows, si `python` no funciona, usa `py`.) Los scripts funcionan desde cualquier carpeta: la base `biblioteca.db` siempre se crea junto a `app.py`.
Abrir en el navegador:
- http://127.0.0.1:5000/instrucciones (listado)
- http://127.0.0.1:5000/instrucciones/nueva (registrar)
- http://127.0.0.1:5000/instrucciones/editar/1 (modificar)
- http://127.0.0.1:5000/resumen (resumen)

> `crear_bd.py` borra y vuelve a crear las tablas, con 5 instrucciones de ejemplo.

## Estructura de archivos
```
app.py             # rutas de Flask y lógica del sistema
crear_bd.py        # crea las tablas y carga 5 registros de ejemplo
requirements.txt   # dependencias (Flask)
capturas/          # capturas del navegador usadas en el PDF de pruebas
pruebas.py         # ejecuta los casos de prueba y guarda resultados_pruebas.json
armar_pdf.py       # arma el PDF de pruebas con las capturas de la carpeta capturas/
templates/         # base.html, instrucciones.html, nueva.html, editar.html, resumen.html
static/style.css   # única hoja de estilos del sitio
```

## Rutas
| Ruta | Método | Qué hace |
|---|---|---|
| `/` | GET | Redirige al listado |
| `/instrucciones` | GET | Consultar: listado con versión |
| `/instrucciones/nueva` | GET / POST | Registrar: formulario con validación |
| `/instrucciones/editar/<id>` | GET / POST | Modificar: actualiza la versión y guarda historial |
| `/instrucciones/eliminar/<id>` | POST | Eliminar (con confirmación en el navegador) |
| `/resumen` | GET | Recorre y clasifica todas las instrucciones |

## Base de datos (SQLite, `biblioteca.db`)
**instrucciones**: `id` (entero, clave), `titulo` (texto), `proceso` (texto), `version` (entero), `fecha_actualizacion` (texto), `enlace` (texto, opcional)

**historial_versiones**: `id` (entero, clave), `instruccion_id` (entero, referencia a instrucciones), `version` (entero), `fecha` (texto)

Todas las sentencias SQL usan parámetros `?`; nunca se concatena texto del usuario.

## Validaciones
- Registrar: título y proceso no vacíos; versión entera >= 1.
- Modificar: la nueva versión debe ser entera y **mayor** que la actual (una edición genera una versión nueva, según el diagrama de la ficha).
- Si hay error se muestra el mensaje y no se guarda. Al guardar, se redirige al listado.

## Cómo funciona el resumen
`/resumen` lee todas las instrucciones y las recorre con un `for`. En cada vuelta usa `if/elif/else`:
- versión >= `VERSION_VIGENTE` -> **vigente**
- versión >= 1 -> **desactualizada**
- cualquier otro caso -> **sin clasificar**

Cada clasificación suma a su propio contador y se muestra con un color distinto (verde, amarillo, gris) definido en `style.css`.

> **Pendiente de confirmar con el Socio Formador:** `VERSION_VIGENTE = 3` es un valor de prueba (la ficha no fija un número).

## Pruebas
`python pruebas.py` ejecuta 10 casos (registro válido e inválido, listado, modificación, eliminación, resumen con dos conjuntos de datos, inyección SQL) sobre una copia temporal, sin tocar `biblioteca.db`.

## Equipo: parte del código desarrollada por cada integrante
- **Marco Afane** (@marcoafane10): `app.py` (rutas, mantenimientos y resumen), `armar_pdf.py` y README
- **Ever Gómez** (@evergom1306-dotcom): `pruebas.py` y `resultados_pruebas.json`
- **Luis Mejía** (@mejialuissv-prog): `crear_bd.py` (tablas y datos de ejemplo) y `static/style.css`
- **Rodrigo Alvarenga** (@RodrigoAlvarenga-prog): plantillas `base.html`, `instrucciones.html` y `nueva.html`
- **Moisés Morán**: plantillas `editar.html` y `resumen.html`, corrección de la estructura del proyecto (carpeta `static/`, nombre de `crear_bd.py`, ruta de la base de datos) y capturas de pruebas
