import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile


AQUI = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp()
for nombre in ("app.py", "crear_bd.py", "templates", "static"):
    origen = os.path.join(AQUI, nombre)
    destino = os.path.join(tmp, nombre)
    if os.path.isdir(origen):
        shutil.copytree(origen, destino)
    else:
        shutil.copy(origen, destino)
subprocess.run([sys.executable, "crear_bd.py"], cwd=tmp, check=True, capture_output=True)
os.environ["BIBLIOTECA_DB"] = os.path.join(tmp, "biblioteca.db")
sys.path.insert(0, tmp)
from app import app  # noqa: E402

cliente = app.test_client()
resultados = []


def contar_filas():
    c = sqlite3.connect(os.environ["BIBLIOTECA_DB"])
    n = c.execute("SELECT COUNT(*) FROM instrucciones").fetchone()[0]
    c.close()
    return n


def numeros_resumen(html):
    v = re.search(r"Vigentes<strong>(\d+)", html).group(1)
    d = re.search(r"Desactualizadas<strong>(\d+)", html).group(1)
    return v, d


def registrar(no, que, entrada, esperado, obtenido, url):
    resultados.append({"no": no, "que": que, "entrada": entrada, "esperado": esperado, "obtenido": obtenido, "url": url})


# 1. Registro valido
r = cliente.post("/instrucciones/nueva", data={"titulo": "Limpieza de rodillos", "proceso": "Impresion", "version": "3", "enlace": ""})
lista = cliente.get("/instrucciones").get_data(as_text=True)
ok = r.status_code == 302 and "Limpieza de rodillos" in lista
registrar(1, "Registro valido", "Limpieza de rodillos, Impresion, version 3",
          "Redirige al listado y la instruccion aparece",
          "Redirige y aparece en el listado" if ok else "FALLO", "http://127.0.0.1:5000/instrucciones/nueva")

# 2. Registro invalido (titulo vacio)
antes = contar_filas()
r = cliente.post("/instrucciones/nueva", data={"titulo": "", "proceso": "Corte", "version": "2", "enlace": ""})
msg = "obligatorios" in r.get_data(as_text=True)
ok = msg and contar_filas() == antes
registrar(2, "Registro invalido", "Titulo vacio, Corte, version 2",
          "Mensaje de error y no se guarda",
          "Muestra el error y no se guardo" if ok else "FALLO", "http://127.0.0.1:5000/instrucciones/nueva")

# 3. Registro invalido (version no numerica)
r = cliente.post("/instrucciones/nueva", data={"titulo": "Prueba", "proceso": "Corte", "version": "abc", "enlace": ""})
ok = "entero" in r.get_data(as_text=True) and contar_filas() == antes
registrar(3, "Registro invalido (version incorrecta)", "Prueba, Corte, version abc",
          "Mensaje de error y no se guarda",
          "Muestra el error y no se guardo" if ok else "FALLO", "http://127.0.0.1:5000/instrucciones/nueva")

# 4. Consulta del listado
html = cliente.get("/instrucciones").get_data(as_text=True)
ok = all(t in html for t in ("Empaque de producto terminado", "Troquelado", "Control de calidad"))
registrar(4, "Consulta del listado", "Abrir /instrucciones",
          "Tabla con las instrucciones y su version",
          "Tabla con las %d instrucciones" % contar_filas() if ok else "FALLO", "http://127.0.0.1:5000/instrucciones")

# 5. Modificacion (actualizar version de la instruccion 4, version 1 -> 3)
r = cliente.post("/instrucciones/editar/4", data={"version": "3"})
c = sqlite3.connect(os.environ["BIBLIOTECA_DB"])
v = c.execute("SELECT version FROM instrucciones WHERE id = 4").fetchone()[0]
h = c.execute("SELECT COUNT(*) FROM historial_versiones WHERE instruccion_id = 4").fetchone()[0]
c.close()
ok = r.status_code == 302 and v == 3 and h == 2
registrar(5, "Modificacion", "Instruccion 4: version 1 -> 3",
          "Version actualizada a 3 y historial con 2 registros",
          "Version %d, historial con %d registros" % (v, h) if ok else "FALLO", "http://127.0.0.1:5000/instrucciones/editar/4")

# 6. Resumen con datos A (estado actual)
html = cliente.get("/resumen").get_data(as_text=True)
vA, dA = numeros_resumen(html)
registrar(6, "Resumen con datos A", "Datos de ejemplo + registro de prueba 1 + modificacion de prueba 5",
          "Vigentes: 5, Desactualizadas: 1 (de 6 instrucciones)",
          "Vigentes: %s, Desactualizadas: %s" % (vA, dA), "http://127.0.0.1:5000/resumen")

# 7. Eliminacion
antes = contar_filas()
r = cliente.post("/instrucciones/eliminar/2")
c = sqlite3.connect(os.environ["BIBLIOTECA_DB"])
sigue = c.execute("SELECT COUNT(*) FROM instrucciones WHERE id = 2").fetchone()[0]
c.close()
ok = r.status_code == 302 and sigue == 0 and contar_filas() == antes - 1
registrar(7, "Eliminacion", "Eliminar instruccion 2 (Ajuste de maquina troqueladora)",
          "La instruccion desaparece del listado",
          "Eliminada, quedan %d" % contar_filas() if ok else "FALLO", "http://127.0.0.1:5000/instrucciones")

# 8. Resumen con datos B (despues de eliminar y de registrar dos instrucciones desactualizadas)
cliente.post("/instrucciones/nueva", data={"titulo": "Embalaje de cajas", "proceso": "Empaque", "version": "1", "enlace": ""})
cliente.post("/instrucciones/nueva", data={"titulo": "Rotulado de tarimas", "proceso": "Empaque", "version": "2", "enlace": ""})
html = cliente.get("/resumen").get_data(as_text=True)
vB, dB = numeros_resumen(html)
registrar(8, "Resumen con datos B", "Tras eliminar la instruccion 2 y registrar 'Embalaje de cajas' (v1) y 'Rotulado de tarimas' (v2)",
          "Vigentes: 5, Desactualizadas: 2 (de 7 instrucciones)",
          "Vigentes: %s, Desactualizadas: %s" % (vB, dB), "http://127.0.0.1:5000/resumen")

# 9. Modificacion invalida (version menor o igual)
r = cliente.post("/instrucciones/editar/5", data={"version": "2"})
ok = "mayor" in r.get_data(as_text=True)
registrar(9, "Modificacion invalida", "Instruccion 5: version 3 -> 2",
          "Mensaje de error y no se guarda",
          "Muestra el error" if ok else "FALLO", "http://127.0.0.1:5000/instrucciones/editar/5")

# 10. Intento de inyeccion SQL en el titulo
r = cliente.post("/instrucciones/nueva", data={"titulo": "x'); DROP TABLE instrucciones;--", "proceso": "Corte", "version": "1", "enlace": ""})
ok = contar_filas() >= 1
registrar(10, "Consulta parametrizada (inyeccion SQL)", "Titulo: x'); DROP TABLE instrucciones;--",
          "Se guarda como texto; la tabla sigue existiendo",
          "Tabla intacta, titulo guardado como texto" if ok else "FALLO", "http://127.0.0.1:5000/instrucciones/nueva")

with open(os.path.join(AQUI, "resultados_pruebas.json"), "w", encoding="utf8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

for x in resultados:
    if x["esperado"].startswith("Vigentes"):
        paso = x["esperado"].startswith(x["obtenido"])
    else:
        paso = x["obtenido"] != "FALLO"
    print("PASA " if paso else "FALLA", x["no"], x["que"], "->", x["obtenido"])
shutil.rmtree(tmp)
