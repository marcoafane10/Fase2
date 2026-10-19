import sqlite3

conexion = sqlite3.connect("biblioteca.db")

conexion.execute("DROP TABLE IF EXISTS historial_versiones")
conexion.execute("DROP TABLE IF EXISTS instrucciones")

conexion.execute("""
    CREATE TABLE instrucciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        proceso TEXT NOT NULL,
        version INTEGER NOT NULL,
        fecha_actualizacion TEXT NOT NULL,
        enlace TEXT
    )
""")

conexion.execute("""
    CREATE TABLE historial_versiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        instruccion_id INTEGER NOT NULL,
        version INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        FOREIGN KEY (instruccion_id) REFERENCES instrucciones (id)
    )
""")

instrucciones = [
    ("Empaque de producto terminado", "Empaque", 3, "2026-09-01", "https://ejemplo.com/empaque.pdf"),
    ("Ajuste de maquina troqueladora", "Troquelado", 2, "2026-06-15", "https://ejemplo.com/troquel.pdf"),
    ("Cambio de tinta en impresora offset", "Impresion", 4, "2026-09-20", ""),
    ("Control de calidad de etiquetas", "Calidad", 1, "2026-03-10", "https://ejemplo.com/calidad.mp4"),
    ("Corte de papel en guillotina", "Corte", 3, "2026-08-05", ""),
]

for instruccion in instrucciones:
    cursor = conexion.execute(
        "INSERT INTO instrucciones (titulo, proceso, version, fecha_actualizacion, enlace) VALUES (?, ?, ?, ?, ?)",
        instruccion,
    )
   
    conexion.execute(
        "INSERT INTO historial_versiones (instruccion_id, version, fecha) VALUES (?, ?, ?)",
        (cursor.lastrowid, instruccion[2], instruccion[3]),
    )

conexion.commit()
conexion.close()
print("Base de datos creada con", len(instrucciones), "instrucciones de ejemplo.")
