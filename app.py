import os
import sqlite3
from datetime import date

from flask import Flask, redirect, render_template, request

app = Flask(__name__)


RUTA_BD = os.environ.get("BIBLIOTECA_DB", os.path.join(os.path.dirname(__file__), "biblioteca.db"))


VERSION_VIGENTE = 3


def conectar():
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    return conexion


def clasificar(version):
    
    if version >= VERSION_VIGENTE:
        return "vigente"
    elif version >= 1:
        return "desactualizada"
    else:
        return "sin clasificar"


@app.route("/")
def inicio():
    return redirect("/instrucciones")



@app.route("/instrucciones")
def listar():
    conexion = conectar()
    filas = conexion.execute("SELECT * FROM instrucciones ORDER BY id").fetchall()
    conexion.close()
    return render_template("instrucciones.html", instrucciones=filas, version_vigente=VERSION_VIGENTE)



@app.route("/resumen")
def resumen():
    conexion = conectar()
    filas = conexion.execute("SELECT * FROM instrucciones ORDER BY id").fetchall()
    conexion.close()

    contVigentes = 0
    contDesactualizadas = 0
    contSinClasificar = 0
    detalle = []

    for fila in filas:
        if fila["version"] >= VERSION_VIGENTE:
            clasificacion = "vigente"
            contVigentes = contVigentes + 1
        elif fila["version"] >= 1:
            clasificacion = "desactualizada"
            contDesactualizadas = contDesactualizadas + 1
        else:
            clasificacion = "sin clasificar"
            contSinClasificar = contSinClasificar + 1
        detalle.append({"titulo": fila["titulo"], "version": fila["version"], "clasificacion": clasificacion})

    return render_template(
        "resumen.html",
        detalle=detalle,
        total=len(filas),
        vigentes=contVigentes,
        desactualizadas=contDesactualizadas,
        sinClasificar=contSinClasificar,
        version_vigente=VERSION_VIGENTE,
    )



@app.route("/instrucciones/nueva", methods=["GET", "POST"])
def nueva():
    error = ""
    datos = {"titulo": "", "proceso": "", "version": "", "enlace": ""}
    if request.method == "POST":
        titulo = request.form["titulo"].strip()
        proceso = request.form["proceso"].strip()
        version = request.form["version"].strip()
        enlace = request.form["enlace"].strip()
        datos = {"titulo": titulo, "proceso": proceso, "version": version, "enlace": enlace}
        if titulo == "" or proceso == "":
            error = "El titulo y el proceso son obligatorios."
        elif not version.isdigit() or int(version) < 1:
            error = "La version debe ser un numero entero mayor o igual a 1."
        else:
            hoy = date.today().isoformat()
            conexion = conectar()
            cursor = conexion.execute(
                "INSERT INTO instrucciones (titulo, proceso, version, fecha_actualizacion, enlace) VALUES (?, ?, ?, ?, ?)",
                (titulo, proceso, int(version), hoy, enlace),
            )
            conexion.execute(
                "INSERT INTO historial_versiones (instruccion_id, version, fecha) VALUES (?, ?, ?)",
                (cursor.lastrowid, int(version), hoy),
            )
            conexion.commit()
            conexion.close()
            return redirect("/instrucciones")
    return render_template("nueva.html", error=error, datos=datos)



@app.route("/instrucciones/editar/<int:idInstruccion>", methods=["GET", "POST"])
def editar(idInstruccion):
    conexion = conectar()
    fila = conexion.execute("SELECT * FROM instrucciones WHERE id = ?", (idInstruccion,)).fetchone()
    if fila is None:
        conexion.close()
        return "Instruccion no encontrada", 404

    error = ""
    if request.method == "POST":
        version = request.form["version"].strip()
        if not version.isdigit():
            error = "La version debe ser un numero entero."
        elif int(version) <= fila["version"]:
            error = "La nueva version debe ser mayor que la actual (" + str(fila["version"]) + ")."
        else:
            hoy = date.today().isoformat()
            conexion.execute(
                "UPDATE instrucciones SET version = ?, fecha_actualizacion = ? WHERE id = ?",
                (int(version), hoy, idInstruccion),
            )
            conexion.execute(
                "INSERT INTO historial_versiones (instruccion_id, version, fecha) VALUES (?, ?, ?)",
                (idInstruccion, int(version), hoy),
            )
            conexion.commit()
            conexion.close()
            return redirect("/instrucciones")

    historial = conexion.execute(
        "SELECT version, fecha FROM historial_versiones WHERE instruccion_id = ? ORDER BY version DESC",
        (idInstruccion,),
    ).fetchall()
    conexion.close()
    return render_template("editar.html", instruccion=fila, historial=historial, error=error)



@app.route("/instrucciones/eliminar/<int:idInstruccion>", methods=["POST"])
def eliminar(idInstruccion):
    conexion = conectar()
    conexion.execute("DELETE FROM historial_versiones WHERE instruccion_id = ?", (idInstruccion,))
    conexion.execute("DELETE FROM instrucciones WHERE id = ?", (idInstruccion,))
    conexion.commit()
    conexion.close()
    return redirect("/instrucciones")


if __name__ == "__main__":
    app.run(debug=True)
