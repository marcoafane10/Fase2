import json
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


RETO = "Biblioteca Digital de Instrucciones de Trabajo - Impresos Múltiples"
INTEGRANTES = ["Marco Afane", "Ever Gómez", "Moisés Morán", "Luis Mejía", "Rodrigo Alvarenga"]
REPOSITORIO = "https://github.com/marcoafane10/Fase2"



AQUI = os.path.dirname(os.path.abspath(__file__))
estilos = getSampleStyleSheet()
pequeno = estilos["BodyText"].clone("pequeno", fontSize=8, leading=10)

with open(os.path.join(AQUI, "resultados_pruebas.json"), encoding="utf8") as f:
    pruebas = json.load(f)

historia = [Paragraph("Documento de pruebas - Fase 2", estilos["Title"]), Spacer(1, 12),
            Paragraph("<b>Reto:</b> " + escape(RETO), estilos["Normal"]), Spacer(1, 8),
            Paragraph("<b>Integrantes:</b> " + escape(", ".join(INTEGRANTES)), estilos["Normal"]), Spacer(1, 8),
            Paragraph("<b>Repositorio:</b> " + escape(REPOSITORIO), estilos["Normal"]), PageBreak()]

filas = [["No.", "Que se prueba", "Datos de entrada", "Resultado esperado", "Resultado obtenido", "Captura"]]
for p in pruebas:
    filas.append([str(p["no"]), Paragraph(escape(p["que"]), pequeno), Paragraph(escape(p["entrada"]), pequeno),
                  Paragraph(escape(p["esperado"]), pequeno), Paragraph(escape(p["obtenido"]), pequeno),
                  "Figura " + str(p["no"])])
tabla = Table(filas, colWidths=[1.2 * cm, 4 * cm, 6 * cm, 5.5 * cm, 5.5 * cm, 2.3 * cm], repeatRows=1)
tabla.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#006dff")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
historia += [Paragraph("Tabla de pruebas", estilos["Heading2"]), tabla, PageBreak()]

for p in pruebas:
    capturas = []
    previa = os.path.join(AQUI, "capturas", str(p["no"]) + "a_formulario.png")
    if os.path.exists(previa):
        capturas.append(("Datos escritos en el formulario, antes de enviar", previa))
    capturas.append(("Resultado en el navegador", os.path.join(AQUI, "capturas", str(p["no"]) + ".png")))
    for parte, (subtitulo, ruta) in enumerate(capturas):
        titulo = "Figura %d - %s" % (p["no"], escape(p["que"]))
        if len(capturas) > 1:
            titulo += " (%s)" % "ab"[parte]
        historia.append(Paragraph(titulo, estilos["Heading3"]))
        historia.append(Paragraph("Ruta probada: " + escape(p["url"]) + " &nbsp;&nbsp;|&nbsp;&nbsp; " + subtitulo, estilos["Normal"]))
        historia.append(Spacer(1, 6))
        if os.path.exists(ruta):
            historia.append(Image(ruta, width=24 * cm, height=15 * cm, kind="proportional"))
        else:
            marco = Table([["[Falta %s - pegar aqui la captura del navegador con la URL visible]" % os.path.basename(ruta)]],
                          colWidths=[24 * cm], rowHeights=[8 * cm])
            marco.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.grey), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                       ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            historia.append(marco)
        historia.append(PageBreak())

SimpleDocTemplate(os.path.join(AQUI, "pruebas_fase2.pdf"), pagesize=landscape(A4),
                  leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm).build(historia)
print("PDF generado: pruebas_fase2.pdf")
