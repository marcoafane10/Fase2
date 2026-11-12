import csv
import io
import json
import os
import re
import sys

import mysql.connector

# Ejecuta los casos de prueba de la Tarea 3 contra una base de datos aparte
# (biblioteca_pruebas), creada con el mismo crear_bd.sql. No toca la base real.
# Requiere MySQL encendido (XAMPP). Uso: python pruebas.py

AQUI = os.path.dirname(os.path.abspath(__file__))
BD_PRUEBAS = "biblioteca_pruebas"
URL = "http://127.0.0.1:5000"


def crear_base_de_pruebas():
    with open(os.path.join(AQUI, "crear_bd.sql"), encoding="utf-8") as f:
        script = f.read().replace("biblioteca_instrucciones", BD_PRUEBAS)
    conexion = mysql.connector.connect(host=os.environ.get("MYSQL_HOST", "localhost"),
                                       user=os.environ.get("MYSQL_USER", "root"),
                                       password=os.environ.get("MYSQL_PASSWORD", ""))
    cursor = conexion.cursor()
    sin_comentarios = "\n".join(l for l in script.splitlines() if not l.strip().startswith("--"))
    for sentencia in sin_comentarios.split(";"):
        if sentencia.strip():
            cursor.execute(sentencia)
    conexion.commit()
    cursor.close()
    conexion.close()


crear_base_de_pruebas()
os.environ["MYSQL_DATABASE"] = BD_PRUEBAS
sys.path.insert(0, AQUI)
from app import ajustar_max_allowed_packet, app  # noqa: E402

ajustar_max_allowed_packet()
cliente = app.test_client()
resultados = []


def consulta(sql, parametros=()):
    c = mysql.connector.connect(host=os.environ.get("MYSQL_HOST", "localhost"), user=os.environ.get("MYSQL_USER", "root"),
                                password=os.environ.get("MYSQL_PASSWORD", ""), database=BD_PRUEBAS)
    cur = c.cursor()
    cur.execute(sql, parametros)
    filas = cur.fetchall()
    cur.close()
    c.close()
    return filas


def subir(idInstruccion, contenido, nombre, video=""):
    return cliente.post("/instrucciones/%d/documentos" % idInstruccion,
                        data={"documento": (io.BytesIO(contenido), nombre), "enlace_video": video},
                        content_type="multipart/form-data")


def registrar(no, que, entrada, esperado, obtenido, url, paso, captura=None):
    resultados.append({"no": no, "que": que, "entrada": entrada, "esperado": esperado,
                       "obtenido": obtenido if paso else "FALLO: " + obtenido, "url": url,
                       "captura": captura or str(no), "paso": paso})


# Documentos de prueba inventados (los mismos de la carpeta documentos_prueba/)
def leer(nombre):
    with open(os.path.join(AQUI, "documentos_prueba", nombre), "rb") as f:
        return f.read()


PDF = leer("instructivo_empaque_v1.pdf")
PDF2 = leer("instructivo_empaque_v2.pdf")
DOCX = leer("instructivo_troquel.docx")

# 1. Subida valida de un PDF
r = subir(1, PDF, "instructivo_empaque_v1.pdf", "https://www.youtube.com/watch?v=empaque01")
filas = consulta("SELECT version, nombre_original, tamano FROM documentos WHERE instruccion_id = 1")
ok = r.status_code == 302 and filas == [(1, "instructivo_empaque_v1.pdf", len(PDF))]
registrar(1, "Subida válida de un PDF", "Empaque de producto terminado: instructivo_empaque_v1.pdf + enlace de video",
          "Se guarda como versión 1 con su video", "Versión 1 guardada (%d bytes)" % len(PDF),
          URL + "/instrucciones/1/documentos", ok)

# 2. Subida valida de un Word
r = subir(2, DOCX, "instructivo_troquel.docx")
filas = consulta("SELECT version, tipo_mime FROM documentos WHERE instruccion_id = 2")
ok = r.status_code == 302 and len(filas) == 1 and filas[0][0] == 1 and "wordprocessingml" in filas[0][1]
registrar(2, "Subida válida de un Word", "Ajuste de máquina troqueladora: instructivo_troquel.docx",
          "Se guarda como versión 1 (Word)", "Versión 1 guardada como documento Word",
          URL + "/instrucciones/2/documentos", ok)

# 3. Tipo de archivo no permitido
antes = consulta("SELECT COUNT(*) FROM documentos")[0][0]
r = subir(3, b"Notas de la maquina", "notas.txt")
ok = "no permitido" in r.get_data(as_text=True) and consulta("SELECT COUNT(*) FROM documentos")[0][0] == antes
registrar(3, "Tipo de archivo no permitido", "notas.txt",
          "Mensaje de error y no se guarda", "Muestra 'Tipo de archivo no permitido' y no se guardó",
          URL + "/instrucciones/3/documentos", ok)

# 4. Archivo demasiado grande (11 MB; el maximo es 10 MB)
grande = b"%PDF-1.4\n" + b"0" * (11 * 1024 * 1024)
r = subir(3, grande, "manual_completo.pdf")
ok = "máximo" in r.get_data(as_text=True) and consulta("SELECT COUNT(*) FROM documentos")[0][0] == antes
registrar(4, "Archivo demasiado grande", "manual_completo.pdf de 11 MB (máximo 10 MB)",
          "Mensaje de error y no se guarda", "Muestra el tamaño y el máximo; no se guardó",
          URL + "/instrucciones/3/documentos", ok)

# 5. Archivo vacio y sin archivo elegido
r1 = subir(3, b"", "vacio.pdf")
r2 = cliente.post("/instrucciones/3/documentos", data={"enlace_video": ""}, content_type="multipart/form-data")
ok = "vacío" in r1.get_data(as_text=True) and "Elige un archivo" in r2.get_data(as_text=True) \
    and consulta("SELECT COUNT(*) FROM documentos")[0][0] == antes
registrar(5, "Archivo vacío o sin archivo", "vacio.pdf de 0 bytes; luego enviar sin elegir archivo",
          "Mensaje de error en ambos casos y no se guarda", "Muestra 'El archivo está vacío' y 'Elige un archivo'",
          URL + "/instrucciones/3/documentos", ok)

# 6. Segunda subida crea la version 2 y conserva la 1
r = subir(1, PDF2, "instructivo_empaque_v2.pdf", "https://www.youtube.com/watch?v=empaque02")
filas = consulta("SELECT version, nombre_original FROM documentos WHERE instruccion_id = 1 ORDER BY version")
ok = r.status_code == 302 and filas == [(1, "instructivo_empaque_v1.pdf"), (2, "instructivo_empaque_v2.pdf")]
registrar(6, "Segunda subida crea la versión 2", "Empaque: instructivo_empaque_v2.pdf",
          "Versión 2 nueva; la versión 1 se conserva", "Hay 2 versiones: v1 y v2",
          URL + "/instrucciones/1/documentos", ok)

# 7. Estados: la mas reciente vigente, la anterior obsoleta
html = cliente.get("/instrucciones/1/documentos").get_data(as_text=True)
estados = re.findall(r'<span class="chip (vigente|obsoleta)">', html)
ok = estados == ["vigente", "obsoleta"]
registrar(7, "Estados vigente y obsoleta", "Ver las versiones de Empaque",
          "v2 vigente (la más reciente), v1 obsoleta", "v2: " + (estados[0] if estados else "-") + ", v1: "
          + (estados[1] if len(estados) > 1 else "-"), URL + "/instrucciones/1/documentos", ok)

# 8. Descarga devuelve el mismo archivo con su nombre original
idv1 = consulta("SELECT id FROM documentos WHERE instruccion_id = 1 AND version = 1")[0][0]
d = cliente.get("/documentos/%d/descargar" % idv1)
ok = d.status_code == 200 and d.data == PDF and "instructivo_empaque_v1.pdf" in d.headers.get("Content-Disposition", "")
registrar(8, "Descarga del mismo archivo", "Descargar la versión 1 de Empaque",
          "Se descarga instructivo_empaque_v1.pdf idéntico al subido", "Mismo tamaño y mismo contenido byte por byte",
          URL + "/documentos/%d/descargar" % idv1, ok)

# 9. Descarga de un id que no existe
d = cliente.get("/documentos/9999/descargar")
registrar(9, "Descarga inexistente", "/documentos/9999/descargar", "Responde 404",
          "Responde %d" % d.status_code, URL + "/documentos/9999/descargar", d.status_code == 404)

# 10. Enlace de video invalido
r = subir(3, PDF, "tinta.pdf", "www.video-sin-protocolo.com")
ok = "http://" in r.get_data(as_text=True) and consulta("SELECT COUNT(*) FROM documentos WHERE instruccion_id = 3")[0][0] == 0
registrar(10, "Enlace de video inválido", "tinta.pdf con enlace www.video-sin-protocolo.com",
          "Mensaje de error y no se guarda", "Pide que empiece con http:// o https://; no se guardó",
          URL + "/instrucciones/3/documentos", ok)

# 11. Resumen cuenta documento y video
html = cliente.get("/resumen").get_data(as_text=True)
obtenido = "Completas: %s, Falta video: %s, Sin documento: %s" % (
    re.search(r'data-completas="(\d+)"', html).group(1), re.search(r'data-falta-video="(\d+)"', html).group(1),
    re.search(r'data-sin-documento="(\d+)"', html).group(1))
esperado = "Completas: 1, Falta video: 1, Sin documento: 6"
registrar(11, "Resumen con documento y video", "Empaque con documento y video; Troquel solo documento; 6 sin documento",
          esperado, obtenido, URL + "/resumen", obtenido == esperado)

# 12. Eliminar la instruccion borra tambien sus archivos (ON DELETE CASCADE)
r = cliente.post("/instrucciones/eliminar/2")
quedan = consulta("SELECT COUNT(*) FROM documentos WHERE instruccion_id = 2")[0][0]
ok = r.status_code == 302 and quedan == 0 and consulta("SELECT COUNT(*) FROM instrucciones WHERE id = 2")[0][0] == 0
registrar(12, "Eliminar borra sus archivos", "Eliminar Ajuste de máquina troqueladora (tenía 1 documento)",
          "Se borran la instrucción y sus documentos", "Quedan %d documentos de esa instrucción" % quedan,
          URL + "/instrucciones", ok)

# ---------- Mejoras individuales ----------
# 13. Marco: buscador por nombre de archivo y filtros
h1 = cliente.get("/instrucciones", query_string={"q": "instructivo_empaque"}).get_data(as_text=True)
h2 = cliente.get("/instrucciones", query_string={"proceso": "Impresión"}).get_data(as_text=True)
h3 = cliente.get("/instrucciones", query_string={"q": "' OR 1=1 --"}).get_data(as_text=True)
n1, n2, n3 = (h.count('class="fila-animada"') for h in (h1, h2, h3))
ok = n1 == 1 and "Empaque de producto terminado" in h1 and n2 == 2 and n3 == 0
registrar(13, "Mejora de Marco: buscador y filtros", "Buscar 'instructivo_empaque'; filtrar Impresión; buscar ' OR 1=1 --",
          "1 resultado (por nombre de archivo); 2 de Impresión; 0 (sin inyección SQL)",
          "%d; %d; %d" % (n1, n2, n3), URL + "/instrucciones?q=instructivo_empaque", ok)

# 14. Ever: porcentajes y resumen por proceso
html = cliente.get("/resumen").get_data(as_text=True)
porcentajes = re.findall(r"<small>([\d.]+)%</small>", html)
ok = porcentajes == ["14.3", "0.0", "85.7"] and html.count("barra-mini") >= 5
registrar(14, "Mejora de Ever: porcentajes por proceso", "Resumen con 7 instrucciones (1 completa)",
          "14.3% completas, 0.0% falta video, 85.7% sin documento y tabla por proceso",
          ", ".join(p + "%" for p in porcentajes), URL + "/resumen", ok)

# 15. Luis: archivar conserva los documentos
r = cliente.post("/instrucciones/archivar/1")
cliente.get("/instrucciones")  # consume el mensaje de confirmacion
activas = cliente.get("/instrucciones").get_data(as_text=True)
archivadas = cliente.get("/instrucciones?estado=archivada").get_data(as_text=True)
docs = consulta("SELECT COUNT(*) FROM documentos WHERE instruccion_id = 1")[0][0]
ok = r.status_code == 302 and "Empaque de producto terminado" not in activas \
    and "Empaque de producto terminado" in archivadas and docs == 2
registrar(15, "Mejora de Luis: archivar", "Archivar Empaque de producto terminado (2 versiones)",
          "Sale de activas, aparece en Archivadas y conserva sus 2 documentos",
          "Solo en Archivadas, con %d documentos" % docs, URL + "/instrucciones?estado=archivada", ok)
cliente.post("/instrucciones/archivar/1")  # se restaura para las siguientes pruebas

# 16. Rodrigo: editar datos y enlace del video
r1 = cliente.post("/instrucciones/editar/1", data={"accion": "datos", "titulo": "Empaque de producto terminado (cajas)",
                                                   "proceso": "Empaque"})
r2 = cliente.post("/instrucciones/editar/1", data={"accion": "video", "enlace_video": "https://www.youtube.com/watch?v=empaque03"})
fila = consulta("SELECT i.titulo, d.enlace_video FROM instrucciones i JOIN documentos d ON d.instruccion_id = i.id "
                "WHERE i.id = 1 AND d.version = 2")
ok = r1.status_code == 302 and r2.status_code == 302 and fila == [("Empaque de producto terminado (cajas)",
                                                                     "https://www.youtube.com/watch?v=empaque03")]
registrar(16, "Mejora de Rodrigo: editar datos y video", "Nuevo título y nuevo enlace de video en Empaque",
          "Se guardan sin perder documentos", "Título y enlace de la versión 2 actualizados",
          URL + "/instrucciones/editar/1", ok)

# 17. Moises: exportar CSV con la version del documento
r = cliente.get("/instrucciones/exportar.csv")
filas = list(csv.reader(io.StringIO(r.data.decode("utf-8-sig"))))
empaque = [f for f in filas if f and f[0] == "1"]
ok = r.status_code == 200 and filas[0][6] == "Versión del documento" and empaque and empaque[0][6] == "2"
registrar(17, "Mejora de Moisés: exportar a CSV", "Exportar a Excel (CSV)",
          "Archivo CSV con una fila por instrucción y la versión del documento",
          "%d filas; Empaque con documento versión %s" % (len(filas) - 1, empaque[0][6] if empaque else "-"),
          URL + "/instrucciones/exportar.csv", ok)

# 18. Registro con documento desde el formulario de registro
r = cliente.post("/instrucciones/nueva", data={"titulo": "Laminado de portadas", "proceso": "Acabados", "version": "1",
                                              "enlace_video": "", "documento": (io.BytesIO(DOCX), "laminado.docx")},
                 content_type="multipart/form-data")
fila = consulta("SELECT d.version FROM instrucciones i JOIN documentos d ON d.instruccion_id = i.id "
                "WHERE i.titulo = 'Laminado de portadas'")
ok = r.status_code == 302 and fila == [(1,)]
registrar(18, "Registro con documento", "Laminado de portadas, Acabados, v1 + laminado.docx",
          "Se registra la instrucción con su documento versión 1", "Registrada con documento v1",
          URL + "/instrucciones/nueva", ok)

# 19. Los errores y la confirmacion se muestran en una ventana modal del sistema, no del navegador
error = subir(3, b"Notas", "notas.txt").get_data(as_text=True)
listado = cliente.get("/instrucciones").get_data(as_text=True)
ok = '<dialog id="modal"' in error and "modal.js" in error and 'class="error"' in error \
    and "data-confirmar=" in listado and "confirm(" not in listado and "alert(" not in listado
registrar(19, "Errores y confirmación en ventana modal", "Subir notas.txt; luego tocar Eliminar en el listado",
          "El error y la confirmación aparecen en un modal dentro del sistema, no en una ventana del navegador",
          "Modal del sistema con el error; Eliminar pide confirmación en el modal", URL + "/instrucciones", ok)

with open(os.path.join(AQUI, "resultados_pruebas.json"), "w", encoding="utf-8") as f:
    json.dump([{k: v for k, v in x.items() if k != "paso"} for x in resultados], f, ensure_ascii=False, indent=2)

for x in resultados:
    print("PASA " if x["paso"] else "FALLA", x["no"], x["que"], "->", x["obtenido"])
