# Pull requests de Moisés (@Moises-JPG). Ejecutar en PowerShell dentro de Documentos\Tarea3.
#   PR 1 (base):  .\publicar_moises.ps1 base
#   PR 6 (final): .\publicar_moises.ps1 final   <- solo cuando los PR 2, 3, 4 y 5 ya estén fusionados
param([string]$paso)
$ErrorActionPreference = "Continue"
$autor = @("-c", "user.name=Moises-JPG", "-c", "user.email=moisesmoran50@gmail.com")
# Volver a main con la carpeta limpia (las etapas s0..s6 vienen del paquete)
git checkout -q -f main
git clean -fdq capturas documentos_prueba
git fetch origin
git fetch ..\tarea3.bundle "refs/heads/*:refs/heads/*" --force 2>$null

if ($paso -eq "base") {
    # El contenido de la etapa base (s0) sobre el main actual, como un solo commit de Moisés
    git checkout -B moises/mysql-documentos s0
    git reset --soft origin/main
    git @autor commit -m "Migrar a MySQL y agregar subida, versiones y descarga de documentos" -m "crear_bd.sql con la tabla documentos (LONGBLOB y FOREIGN KEY ON DELETE CASCADE), formulario multipart con validaciones de tipo, tamaño, archivo vacío y enlace de video, versiones con MAX(version), estados vigente/obsoleta, descarga con send_file y 404, y resumen por documento y video."
    git push -u origin moises/mysql-documentos
    Start-Process "https://github.com/marcoafane10/Fase2/compare/main...moises/mysql-documentos?expand=1"
}
elseif ($paso -eq "final") {
    git checkout -B moises/csv-pruebas origin/main
    # Trae todos los archivos de la etapa final (s6) sobre el main que ya tiene las mejoras de todos
    git checkout s6 -- .
    git status --short
    git @autor commit -m "Agregar exportar a CSV con la version del documento, pruebas y README de la Tarea 3" -m "Ruta /instrucciones/exportar.csv, pruebas.py con 18 casos sobre una base aparte, armar_pdf.py, documentos de prueba inventados, capturas y README actualizado."
    git push -u origin moises/csv-pruebas
    Start-Process "https://github.com/marcoafane10/Fase2/compare/main...moises/csv-pruebas?expand=1"
}
else { "Uso: .\publicar_moises.ps1 base   o   .\publicar_moises.ps1 final" }
