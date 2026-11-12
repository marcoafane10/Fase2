import json
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Arma el PDF de pruebas de la Tarea 3 a partir de resultados_pruebas.json (lo genera pruebas.py)
# y de las capturas de la carpeta capturas/. Requiere: pip install reportlab
# Uso: python armar_pdf.py

AQUI = os.path.dirname(os.path.abspath(__file__))
RETO = "Biblioteca Digital de Instrucciones - Impresos Múltiples"
INTEGRANTES = ["Marco Afane (@marcoafane10)", "Ever Gómez (@evergom1306-dotcom)", "Moisés Morán (@Moises-JPG)",
               "Luis Mejía (@mejialuissv-prog)", "Rodrigo Alvarenga (@RodrigoAlvarenga-prog)"]
REPOSITORIO = "https://github.com/marcoafane10/Fase2"
VIDEO = "PENDIENTE: enlace del video de YouTube"
# Capturas de phpMyAdmin que van al final del documento
CAPTURAS_PHPMYADMIN = [
    ("phpmyadmin_tablas.png", "Estructura de la tabla documentos en phpMyAdmin (LONGBLOB y llave foránea)"),
    ("phpmyadmin_documentos.png", "Tabla documentos con sus versiones en phpMyAdmin"),
]

MARINO = colors.HexColor("#2b3857")
estilos = getSampleStyleSheet()
celda = ParagraphStyle("celda", parent=estilos["Normal"], fontSize=8, leading=10)
celdaTitulo = ParagraphStyle("celdaTitulo", parent=celda, textColor=colors.white, fontName="Helvetica-Bold")
titulo = ParagraphStyle("titulo", parent=estilos["Title"], textColor=MARINO)

with open(os.path.join(AQUI, "resultados_pruebas.json"), encoding="utf-8") as f:
    pruebas = json.load(f)

historia = []

# ---------- Portada ----------
historia.append(Spacer(1, 2.5 * cm))
logo = os.path.join(AQUI, "static", "logo_im.png")
if os.path.exists(logo):
    historia.append(Image(logo, width=3 * cm, height=2.2 * cm, kind="proportional"))
historia.append(Spacer(1, 0.6 * cm))
historia.append(Paragraph("Tarea 3: Documento de pruebas", titulo))
historia.append(Paragraph(escape(RETO), estilos["Heading2"]))
historia.append(Spacer(1, 0.6 * cm))
historia.append(Paragraph("<b>Integrantes:</b> " + escape(", ".join(INTEGRANTES)), estilos["Normal"]))
historia.append(Spacer(1, 0.3 * cm))
historia.append(Paragraph("<b>Repositorio:</b> " + REPOSITORIO, estilos["Normal"]))
historia.append(Paragraph("<b>Video de pruebas:</b> " + escape(VIDEO), estilos["Normal"]))
historia.append(PageBreak())

# ---------- Tabla de pruebas ----------
historia.append(Paragraph("Tabla de pruebas", estilos["Heading1"]))
encabezado = ["No.", "Qué se prueba", "Datos de entrada", "Resultado esperado", "Resultado obtenido", "Captura"]
filas = [[Paragraph(t, celdaTitulo) for t in encabezado]]
for p in pruebas:
    filas.append([Paragraph(str(p["no"]), celda), Paragraph(escape(p["que"]), celda), Paragraph(escape(p["entrada"]), celda),
                  Paragraph(escape(p["esperado"]), celda), Paragraph(escape(p["obtenido"]), celda),
                  Paragraph("Figura " + str(p["no"]), celda)])
n = len(pruebas)
for i, (_, desc) in enumerate(CAPTURAS_PHPMYADMIN, start=1):
    filas.append([Paragraph("-", celda), Paragraph(escape(desc), celda), Paragraph("phpMyAdmin", celda),
                  Paragraph("Se ven la tabla y sus versiones", celda), Paragraph("Ver captura", celda),
                  Paragraph("Figura " + str(n + i), celda)])
tabla = Table(filas, colWidths=[1 * cm, 4.2 * cm, 5.6 * cm, 5 * cm, 5 * cm, 2 * cm], repeatRows=1)
tabla.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), MARINO),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5cbd8")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6f9")]),
]))
historia.append(tabla)
historia.append(PageBreak())


def figura(numero, texto, ruta, url=None):
    historia.append(Paragraph("Figura " + str(numero) + ". " + escape(texto), estilos["Heading3"]))
    if url:
        historia.append(Paragraph("URL: " + escape(url), estilos["Normal"]))
    historia.append(Spacer(1, 6))
    if os.path.exists(ruta):
        historia.append(Image(ruta, width=24 * cm, height=15 * cm, kind="proportional"))
    else:
        historia.append(Paragraph("[Falta la captura " + escape(os.path.basename(ruta)) + "]", estilos["Normal"]))
    historia.append(PageBreak())


for p in pruebas:
    figura(p["no"], p["que"], os.path.join(AQUI, "capturas", p.get("captura", str(p["no"])) + ".png"), p["url"])
for i, (archivo, desc) in enumerate(CAPTURAS_PHPMYADMIN, start=1):
    figura(n + i, desc, os.path.join(AQUI, "capturas", archivo))

salida = os.path.join(AQUI, "pruebas_tarea3.pdf")
SimpleDocTemplate(salida, pagesize=landscape(letter), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                  topMargin=1.5 * cm, bottomMargin=1.5 * cm, title="Pruebas Tarea 3").build(historia)
print("PDF creado:", salida)
