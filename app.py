import csv
import os
from datetime import date
from io import BytesIO, StringIO

import mysql.connector
from flask import Flask, Response, abort, flash, redirect, render_template, request, send_file

app = Flask(__name__)
# Necesaria para los mensajes de confirmacion (flash) entre paginas
app.secret_key = "biblioteca-impresos-multiples"

# ---------- Configuracion de MySQL (XAMPP usa root sin contraseña) ----------
DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "biblioteca_instrucciones"),
}

# ---------- Reglas de los archivos ----------
TAMANO_MAXIMO_MB = 10
TAMANO_MAXIMO = TAMANO_MAXIMO_MB * 1024 * 1024
TIPOS_PERMITIDOS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# Flask corta la peticion si es mucho mas grande que el maximo (ver error 413 abajo)
app.config["MAX_CONTENT_LENGTH"] = TAMANO_MAXIMO * 2


def conectar():
    return mysql.connector.connect(**DB_CONFIG)


def ajustar_max_allowed_packet():
    # El MySQL de XAMPP trae max_allowed_packet = 1M: un archivo mas grande corta la conexion.
    # Se sube a 16M al iniciar (root de XAMPP tiene permiso). Si no se puede, ver README.
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SET GLOBAL max_allowed_packet = %s", (16 * 1024 * 1024,))
        cursor.close()
        conexion.close()
    except mysql.connector.Error as error:
        print("Aviso: no se pudo ajustar max_allowed_packet (" + str(error) + "). Ver README.")


def validar_archivo(archivo):
    """Devuelve (error, contenido, nombre, tipo). Si error no esta vacio, no se guarda nada."""
    if archivo is None or archivo.filename == "":
        return "Elige un archivo PDF o Word para subir.", None, None, None
    nombre = os.path.basename(archivo.filename.replace("\\", "/"))[:255]
    extension = os.path.splitext(nombre)[1].lower()
    if extension not in TIPOS_PERMITIDOS:
        return "Tipo de archivo no permitido: solo se aceptan .pdf, .doc y .docx.", None, None, None
    contenido = archivo.read()
    if len(contenido) == 0:
        return "El archivo está vacío.", None, None, None
    if len(contenido) > TAMANO_MAXIMO:
        megas = round(len(contenido) / (1024 * 1024), 1)
        return "El archivo pesa " + str(megas) + " MB; el máximo es " + str(TAMANO_MAXIMO_MB) + " MB.", None, None, None
    # Se revisa que el contenido corresponda a la extension (un .txt renombrado a .pdf no pasa)
    if extension == ".pdf" and not contenido.startswith(b"%PDF"):
        return "El archivo no es un PDF válido.", None, None, None
    if extension == ".docx" and not contenido.startswith(b"PK"):
        return "El archivo no es un documento Word (.docx) válido.", None, None, None
    if extension == ".doc" and not contenido.startswith(b"\xd0\xcf\x11\xe0"):
        return "El archivo no es un documento Word (.doc) válido.", None, None, None
    return "", contenido, nombre, TIPOS_PERMITIDOS[extension]


def validar_video(enlace):
    # El enlace del video es opcional; si se escribe, debe ser una direccion web
    if enlace == "":
        return ""
    if not (enlace.startswith("http://") or enlace.startswith("https://")):
        return "El enlace del video debe empezar con http:// o https://"
    if len(enlace) > 500:
        return "El enlace del video es demasiado largo (máximo 500 caracteres)."
    return ""


def guardar_documento(conexion, idInstruccion, nombre, tipo, contenido, enlace_video):
    # La version siguiente se calcula con MAX(version); la primera es 1. Nunca se reemplaza la anterior.
    cursor = conexion.cursor()
    cursor.execute("SELECT MAX(version) FROM documentos WHERE instruccion_id = %s", (idInstruccion,))
    ultima = cursor.fetchone()[0]
    if ultima is None:
        siguiente = 1
    else:
        siguiente = ultima + 1
    cursor.execute(
        "INSERT INTO documentos (instruccion_id, version, nombre_original, tipo_mime, tamano, contenido, enlace_video) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (idInstruccion, siguiente, nombre, tipo, len(contenido), contenido, enlace_video or None),
    )
    cursor.close()
    return siguiente


def estado_documento(fila):
    # Clasifica una instruccion segun si ya tiene documento y enlace de video
    if fila["doc_version"] is not None and fila["enlace_video"]:
        return "completa"
    elif fila["doc_version"] is not None:
        return "falta video"
    else:
        return "sin documento"


# Consulta de instrucciones con su documento mas reciente.
# No trae la columna contenido: solo las columnas que se muestran.
SQL_INSTRUCCIONES = """
    SELECT i.id, i.titulo, i.proceso, i.version, i.fecha_actualizacion,
           d.id AS doc_id, d.version AS doc_version, d.nombre_original, d.enlace_video
    FROM instrucciones i
    LEFT JOIN documentos d ON d.instruccion_id = i.id
         AND d.version = (SELECT MAX(d2.version) FROM documentos d2 WHERE d2.instruccion_id = i.id)
"""


@app.route("/")
def inicio():
    return redirect("/instrucciones")


# ---------- CONSULTAR (con buscador y filtros) ----------
@app.route("/instrucciones")
def listar():
    busqueda = request.args.get("q", "").strip()
    proceso = request.args.get("proceso", "").strip()
    filtroDoc = request.args.get("documento", "").strip()
    estado = request.args.get("estado", "activa")
    if estado not in ("activa", "archivada"):
        estado = "activa"

    # El buscador encuentra por titulo de la instruccion o por nombre de cualquiera de sus archivos.
    # Se usan parametros %s: nunca se concatena lo que escribe el usuario.
    condiciones = ["i.estado = %s"]
    parametros = [estado]
    if busqueda != "":
        condiciones.append("(i.titulo LIKE %s OR EXISTS (SELECT 1 FROM documentos b "
                           "WHERE b.instruccion_id = i.id AND b.nombre_original LIKE %s))")
        parametros.append("%" + busqueda + "%")
        parametros.append("%" + busqueda + "%")
    if proceso != "":
        condiciones.append("i.proceso = %s")
        parametros.append(proceso)
    sql = SQL_INSTRUCCIONES + " WHERE " + " AND ".join(condiciones)

    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(sql + " ORDER BY i.titulo", parametros)
    filas = cursor.fetchall()
    cursor.execute("SELECT DISTINCT proceso FROM instrucciones ORDER BY proceso")
    procesos = [f["proceso"] for f in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) AS n FROM instrucciones WHERE estado = 'archivada'")
    archivadas = cursor.fetchone()["n"]
    cursor.close()
    conexion.close()

    # El filtro por estado del documento usa la misma decision del resumen
    instrucciones = []
    for fila in filas:
        fila["estado_doc"] = estado_documento(fila)
        if filtroDoc == "" or fila["estado_doc"] == filtroDoc:
            instrucciones.append(fila)
    return render_template("instrucciones.html", instrucciones=instrucciones, procesos=procesos,
                           busqueda=busqueda, proceso=proceso, filtroDoc=filtroDoc,
                           estado=estado, archivadas=archivadas)


# ---------- EXPORTAR A CSV (se abre en Excel) ----------
@app.route("/instrucciones/exportar.csv")
def exportar_csv():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    # Misma consulta del listado: no trae el contenido de los archivos
    cursor.execute(SQL_INSTRUCCIONES + " WHERE i.estado = 'activa' ORDER BY i.proceso, i.titulo")
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()

    salida = StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(["ID", "Título", "Proceso", "Versión de la instrucción", "Última actualización",
                       "Documento", "Versión del documento", "Enlace del video", "Estado"])
    for fila in filas:
        escritor.writerow([fila["id"], fila["titulo"], fila["proceso"], fila["version"], fila["fecha_actualizacion"],
                           fila["nombre_original"] or "", fila["doc_version"] or "", fila["enlace_video"] or "",
                           estado_documento(fila)])
    # utf-8-sig: Excel muestra bien los acentos
    nombre = "instrucciones_" + date.today().isoformat() + ".csv"
    return Response(salida.getvalue().encode("utf-8-sig"), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=" + nombre})


# ---------- RESUMEN (repeticion + decision) ----------
@app.route("/resumen")
def resumen():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    # Las instrucciones archivadas no cuentan en el resumen
    cursor.execute(SQL_INSTRUCCIONES + " WHERE i.estado = 'activa' ORDER BY i.titulo")
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()

    contCompletas = 0
    contFaltaVideo = 0
    contSinDocumento = 0
    porProceso = {}
    detalle = []
    for fila in filas:
        if fila["doc_version"] is not None and fila["enlace_video"]:
            clasificacion = "completa"
            contCompletas = contCompletas + 1
        elif fila["doc_version"] is not None:
            clasificacion = "falta video"
            contFaltaVideo = contFaltaVideo + 1
        else:
            clasificacion = "sin documento"
            contSinDocumento = contSinDocumento + 1
        # Contadores por proceso (Empaque, Corte, ...)
        if fila["proceso"] not in porProceso:
            porProceso[fila["proceso"]] = {"completa": 0, "falta video": 0, "sin documento": 0, "total": 0}
        porProceso[fila["proceso"]][clasificacion] = porProceso[fila["proceso"]][clasificacion] + 1
        porProceso[fila["proceso"]]["total"] = porProceso[fila["proceso"]]["total"] + 1

        detalle.append({"id": fila["id"], "titulo": fila["titulo"], "proceso": fila["proceso"],
                        "doc_version": fila["doc_version"], "clasificacion": clasificacion})

    # Porcentajes (si no hay registros quedan en 0 para no dividir entre cero)
    total = len(filas)
    if total > 0:
        porcentajeCompletas = round(contCompletas * 100 / total, 1)
        porcentajeFaltaVideo = round(contFaltaVideo * 100 / total, 1)
        porcentajeSinDocumento = round(contSinDocumento * 100 / total, 1)
    else:
        porcentajeCompletas = 0
        porcentajeFaltaVideo = 0
        porcentajeSinDocumento = 0

    # Primero las que necesitan atencion
    orden = {"sin documento": 0, "falta video": 1, "completa": 2}
    detalle.sort(key=lambda d: (orden[d["clasificacion"]], d["titulo"]))

    return render_template(
        "resumen.html",
        detalle=detalle,
        total=total,
        completas=contCompletas,
        faltaVideo=contFaltaVideo,
        sinDocumento=contSinDocumento,
        porcentaje_completas=porcentajeCompletas,
        porcentaje_falta_video=porcentajeFaltaVideo,
        porcentaje_sin_documento=porcentajeSinDocumento,
        porProceso=sorted(porProceso.items()),
    )


# ---------- REGISTRAR (con documento opcional) ----------
@app.route("/instrucciones/nueva", methods=["GET", "POST"])
def nueva():
    error = ""
    datos = {"titulo": "", "proceso": "", "version": "", "enlace_video": ""}
    if request.method == "POST":
        titulo = request.form["titulo"].strip()
        proceso = request.form["proceso"].strip()
        version = request.form["version"].strip()
        enlace_video = request.form.get("enlace_video", "").strip()
        archivo = request.files.get("documento")
        datos = {"titulo": titulo, "proceso": proceso, "version": version, "enlace_video": enlace_video}

        hayArchivo = archivo is not None and archivo.filename != ""
        contenido = nombre = tipo = None
        if titulo == "" or proceso == "":
            error = "El título y el proceso son obligatorios."
        elif not version.isdigit() or int(version) < 1:
            error = "La versión debe ser un número entero mayor o igual a 1."
        elif enlace_video != "" and not hayArchivo:
            error = "Para guardar el enlace del video, sube también el documento."
        else:
            error = validar_video(enlace_video)
            if error == "" and hayArchivo:
                error, contenido, nombre, tipo = validar_archivo(archivo)

        if error == "":
            conexion = conectar()
            cursor = conexion.cursor()
            hoy = date.today()
            cursor.execute(
                "INSERT INTO instrucciones (titulo, proceso, version, fecha_actualizacion) VALUES (%s, %s, %s, %s)",
                (titulo, proceso, int(version), hoy),
            )
            idInstruccion = cursor.lastrowid
            cursor.execute(
                "INSERT INTO historial_versiones (instruccion_id, version, fecha) VALUES (%s, %s, %s)",
                (idInstruccion, int(version), hoy),
            )
            if hayArchivo:
                guardar_documento(conexion, idInstruccion, nombre, tipo, contenido, enlace_video)
            conexion.commit()
            cursor.close()
            conexion.close()
            flash("Instrucción «" + titulo + "» registrada.")
            return redirect("/instrucciones")

    return render_template("nueva.html", error=error, datos=datos, maximo=TAMANO_MAXIMO_MB)


def buscar_instruccion(conexion, idInstruccion):
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM instrucciones WHERE id = %s", (idInstruccion,))
    fila = cursor.fetchone()
    cursor.close()
    return fila


# ---------- DOCUMENTOS: listado de versiones y subida ----------
@app.route("/instrucciones/<int:idInstruccion>/documentos", methods=["GET", "POST"])
def documentos(idInstruccion):
    conexion = conectar()
    instruccion = buscar_instruccion(conexion, idInstruccion)
    if instruccion is None:
        conexion.close()
        abort(404)

    error = ""
    enlace_video = ""
    if request.method == "POST":
        enlace_video = request.form.get("enlace_video", "").strip()
        error, contenido, nombre, tipo = validar_archivo(request.files.get("documento"))
        if error == "":
            error = validar_video(enlace_video)
        if error == "":
            try:
                version = guardar_documento(conexion, idInstruccion, nombre, tipo, contenido, enlace_video)
                conexion.commit()
                conexion.close()
                flash("Se subió «" + nombre + "» como versión " + str(version) + ".")
                return redirect("/instrucciones/" + str(idInstruccion) + "/documentos")
            except mysql.connector.Error as e:
                # Si MySQL corta la conexion (archivo mayor a max_allowed_packet) se reconecta para seguir
                try:
                    conexion.close()
                except mysql.connector.Error:
                    pass
                conexion = conectar()
                error = ("MySQL no pudo guardar el archivo (" + str(e.msg) + "). "
                         "Revisa max_allowed_packet en el README.")

    # Listado de versiones: SELECT solo con las columnas que se muestran (sin contenido)
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, version, nombre_original, tipo_mime, tamano, enlace_video, fecha_subida "
        "FROM documentos WHERE instruccion_id = %s ORDER BY version DESC",
        (idInstruccion,),
    )
    versiones = cursor.fetchall()
    cursor.close()
    conexion.close()

    ultima = versiones[0]["version"] if versiones else None
    for v in versiones:
        if v["version"] == ultima:
            v["estado"] = "vigente"
        elif v["version"] < ultima:
            v["estado"] = "obsoleta"
        else:
            v["estado"] = "desconocido"
        v["tamano_kb"] = round(v["tamano"] / 1024, 1)

    return render_template("documentos.html", instruccion=instruccion, versiones=versiones,
                           error=error, enlace_video=enlace_video, maximo=TAMANO_MAXIMO_MB)


# ---------- DESCARGA ----------
@app.route("/documentos/<int:idDocumento>/descargar")
def descargar(idDocumento):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT nombre_original, tipo_mime, contenido FROM documentos WHERE id = %s", (idDocumento,))
    documento = cursor.fetchone()
    cursor.close()
    conexion.close()
    if documento is None:
        abort(404)
    return send_file(
        BytesIO(documento["contenido"]),
        mimetype=documento["tipo_mime"],
        as_attachment=True,
        download_name=documento["nombre_original"],
    )


# ---------- MODIFICAR: nueva version de la instruccion ----------
@app.route("/instrucciones/editar/<int:idInstruccion>", methods=["GET", "POST"])
def editar(idInstruccion):
    conexion = conectar()
    instruccion = buscar_instruccion(conexion, idInstruccion)
    if instruccion is None:
        conexion.close()
        abort(404)

    # Documento vigente (la version mas reciente), sin traer el contenido del archivo
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT id, version, nombre_original, enlace_video FROM documentos "
                   "WHERE instruccion_id = %s ORDER BY version DESC LIMIT 1", (idInstruccion,))
    vigente = cursor.fetchone()
    cursor.close()

    error = ""
    errorDatos = ""
    errorVideo = ""
    accion = request.form.get("accion", "version")
    if request.method == "POST" and accion == "datos":
        # Corregir titulo y proceso sin perder documentos ni historial
        titulo = request.form["titulo"].strip()
        proceso = request.form["proceso"].strip()
        if titulo == "" or proceso == "":
            errorDatos = "El título y el proceso son obligatorios."
        else:
            cursor = conexion.cursor()
            cursor.execute("UPDATE instrucciones SET titulo = %s, proceso = %s WHERE id = %s",
                           (titulo, proceso, idInstruccion))
            conexion.commit()
            cursor.close()
            conexion.close()
            flash("Datos de «" + titulo + "» actualizados.")
            return redirect("/instrucciones/editar/" + str(idInstruccion))
    elif request.method == "POST" and accion == "video":
        # Cambiar el enlace del video de la version vigente (el video no se sube, solo su enlace)
        enlace = request.form["enlace_video"].strip()
        if vigente is None:
            errorVideo = "Primero sube un documento: el enlace del video acompaña al documento."
        else:
            errorVideo = validar_video(enlace)
        if errorVideo == "":
            cursor = conexion.cursor()
            cursor.execute("UPDATE documentos SET enlace_video = %s WHERE id = %s", (enlace or None, vigente["id"]))
            conexion.commit()
            cursor.close()
            conexion.close()
            flash("Enlace del video actualizado en la versión " + str(vigente["version"]) + " del documento.")
            return redirect("/instrucciones/editar/" + str(idInstruccion))
    elif request.method == "POST":
        version = request.form["version"].strip()
        if not version.isdigit():
            error = "La versión debe ser un número entero."
        elif int(version) <= instruccion["version"]:
            error = "La nueva versión debe ser mayor que la actual (" + str(instruccion["version"]) + ")."
        else:
            hoy = date.today()
            cursor = conexion.cursor()
            cursor.execute("UPDATE instrucciones SET version = %s, fecha_actualizacion = %s WHERE id = %s",
                           (int(version), hoy, idInstruccion))
            cursor.execute("INSERT INTO historial_versiones (instruccion_id, version, fecha) VALUES (%s, %s, %s)",
                           (idInstruccion, int(version), hoy))
            conexion.commit()
            cursor.close()
            conexion.close()
            flash("«" + instruccion["titulo"] + "» actualizada a la versión " + version + ".")
            return redirect("/instrucciones")

    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT version, fecha FROM historial_versiones WHERE instruccion_id = %s ORDER BY version DESC",
                   (idInstruccion,))
    historial = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("editar.html", instruccion=instruccion, historial=historial, error=error,
                           errorDatos=errorDatos, errorVideo=errorVideo, vigente=vigente)


# ---------- ARCHIVAR / RESTAURAR ----------
@app.route("/instrucciones/archivar/<int:idInstruccion>", methods=["POST"])
def archivar(idInstruccion):
    conexion = conectar()
    instruccion = buscar_instruccion(conexion, idInstruccion)
    if instruccion is None:
        conexion.close()
        abort(404)
    # Archivar no borra nada: solo cambia el estado. Los documentos y su historial se conservan.
    if instruccion["estado"] == "activa":
        nuevo = "archivada"
        mensaje = "«" + instruccion["titulo"] + "» se archivó. Sus documentos se conservan."
    else:
        nuevo = "activa"
        mensaje = "«" + instruccion["titulo"] + "» se restauró."
    cursor = conexion.cursor()
    cursor.execute("UPDATE instrucciones SET estado = %s WHERE id = %s", (nuevo, idInstruccion))
    conexion.commit()
    cursor.close()
    conexion.close()
    flash(mensaje)
    if nuevo == "activa":
        return redirect("/instrucciones?estado=archivada")
    return redirect("/instrucciones")


# ---------- ELIMINAR (ON DELETE CASCADE borra tambien sus documentos) ----------
@app.route("/instrucciones/eliminar/<int:idInstruccion>", methods=["POST"])
def eliminar(idInstruccion):
    conexion = conectar()
    instruccion = buscar_instruccion(conexion, idInstruccion)
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM instrucciones WHERE id = %s", (idInstruccion,))
    conexion.commit()
    cursor.close()
    conexion.close()
    if instruccion is not None:
        flash("«" + instruccion["titulo"] + "» y todos sus documentos se eliminaron.")
    return redirect("/instrucciones")


@app.errorhandler(404)
def no_encontrada(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def archivo_muy_grande(e):
    flash("El archivo supera el máximo de " + str(TAMANO_MAXIMO_MB) + " MB y no se guardó.")
    return redirect(request.path)


if __name__ == "__main__":
    ajustar_max_allowed_packet()
    app.run(debug=True)
