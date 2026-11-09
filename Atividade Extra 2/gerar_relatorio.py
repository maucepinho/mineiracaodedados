"""Gera o relatório PDF a partir dos cálculos reproduzíveis."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from estatistica_pinguins import calcular, salvar

PASTA = Path(__file__).resolve().parent


def numero(x, casas=2):
    return f"{x:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def main():
    r = calcular()
    salvar(r)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Corpo", fontName="Helvetica", fontSize=10.5,
                              leading=15, spaceAfter=9, textColor=colors.black))
    for name in ("Title", "Heading1", "Heading2"):
        styles[name].textColor = colors.black
    styles["Title"].fontSize = 20
    styles["Title"].leading = 24
    styles["Title"].alignment = 0
    styles["Heading2"].fontSize = 12
    styles["Heading2"].spaceBefore = 13
    styles["Heading2"].spaceAfter = 8
    story = []

    def p(text):
        story.append(Paragraph(text, styles["Corpo"]))

    def heading(text):
        story.append(Paragraph(text, styles["Heading2"]))

    def table(rows, widths):
        data = [[Paragraph(str(cell), ParagraphStyle(
            name="cell", fontName="Helvetica-Bold" if i == 0 else "Helvetica",
            fontSize=9.5, leading=13, alignment=0 if j == 0 else TA_CENTER))
                 for j, cell in enumerate(row)] for i, row in enumerate(rows)]
        t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4EAF0")),
            ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([t, Spacer(1, 10)])

    story.append(Paragraph("Estatística descritiva dos pinguins", styles["Title"]))
    p("<b>Atividade Extra 2 | Mineração de Dados</b><br/>Nome: ______________________________________________")
    p("Base analisada: palmerpenguins_original.csv, com 344 registros. Os cálculos numéricos "
      "desconsideram os valores ausentes em cada variável, sem imputação: são 342 valores válidos "
      "e 2 ausentes em cada uma das três medidas. O desvio padrão é amostral (denominador n - 1).")
    heading("Exercício 1 Frequência das espécies")
    rows = [["Espécie", "Frequência absoluta", "Frequência relativa"]]
    for species, f in r["frequencias"].items():
        rows.append([species, f["absoluta"], numero(f["relativa_percentual"]) + "%"])
    rows.append(["Total", "344", "100,00%"])
    table(rows, [150, 170, 175])
    p("<b>a e b)</b> As frequências estão na tabela. Frequência relativa = (frequência absoluta / 344) × 100.")
    p("<b>c)</b> Adelie é a espécie mais frequente, com 152 registros (44,19%). A menos frequente "
      "é Chinstrap, com 68. A diferença é <b>152 - 68 = 84 registros</b>.")
    heading("Exercício 2 Média moda e mediana")
    labels = {"body_mass_g": "Massa corporal (g)", "bill_length_mm": "Comprimento do bico (mm)",
              "flipper_length_mm": "Comprimento da nadadeira (mm)"}
    rows = [["Variável", "Média", "Mediana", "Moda"]]
    for k, e in r["estatisticas"].items():
        rows.append([labels[k], numero(e["media"]), numero(e["mediana"]),
                     "; ".join(numero(v) for v in e["modas"])])
    table(rows, [225, 90, 90, 90])
    p("<b>a)</b> A moda da massa corporal é 3.800 g, presente em 12 registros válidos.<br/>"
      "<b>b)</b> A moda do comprimento do bico é 41,1 mm, presente em 7 registros.<br/>"
      "<b>c)</b> A moda do comprimento da nadadeira é 190 mm, presente em 22 registros.")
    p("A média é a soma dos valores dividida por 342. A mediana é a média entre o 171º e o 172º "
      "valores em ordem crescente. A moda é o valor com maior frequência; cada variável apresentou uma única moda.")
    story.append(PageBreak())
    heading("Exercício 3 Desvio padrão amostral")
    p("Foi utilizada a expressão s = raiz quadrada de [soma de (xi - média)² / (n - 1)], "
      "com n = 342 e denominador 341. O cálculo é realizado pela função statistics.stdev do Python.")
    rows = [["Item e variável", "n válido", "Desvio padrão amostral"]]
    for letter, (k, e) in zip("abc", r["estatisticas"].items()):
        unit = "g" if k == "body_mass_g" else "mm"
        rows.append([f"{letter}) {labels[k]}", "342", numero(e["desvio_padrao_amostral"], 4) + " " + unit])
    table(rows, [245, 65, 185])
    heading("Exercício 4 Distância em relação à média")
    e = r["estatisticas"]["body_mass_g"]
    p("<b>a)</b> Maior massa corporal: <b>6.300 g</b>. Menor massa corporal: <b>2.700 g</b>.")
    p("Para expressar a distância em desvios padrão, utiliza-se z = (x - média) / s. "
      "Os resultados abaixo foram calculados com os valores completos; o arredondamento é apenas de apresentação.")
    p("<b>b) Pinguim com maior massa</b><br/>"
      f"z = (6.300 - {numero(e['media'], 6)}) / {numero(e['desvio_padrao_amostral'], 6)} "
      f"= {numero(r['z_massa_maxima'], 4)}.<br/>"
      "Portanto, está aproximadamente <b>2,6164 desvios padrão acima da média</b>.")
    p("<b>c) Pinguim com menor massa</b><br/>"
      f"z = (2.700 - {numero(e['media'], 6)}) / {numero(e['desvio_padrao_amostral'], 6)} "
      f"= {numero(r['z_massa_minima'], 4)}.<br/>"
      "O sinal negativo indica posição abaixo da média: aproximadamente <b>1,8726 desvios padrão abaixo</b>.")
    heading("Evidências dos cálculos")
    p("O arquivo <b>estatistica_pinguins.py</b> contém a leitura da base, o tratamento dos valores ausentes "
      "e os cálculos dos quatro exercícios. Sua execução gera <b>resultados_estatistica.json</b> "
      "com os resultados sem arredondamento de apresentação e <b>resumo_estatistico.csv</b> com as medidas numéricas.")
    p("Para reproduzir, abra o terminal nesta pasta e execute:<br/><b>py estatistica_pinguins.py</b><br/>"
      "O script de cálculos usa somente a biblioteca padrão do Python.")

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawRightString(A4[0] - 50, 30, f"Atividade Extra 2 | Página {doc.page}")

    SimpleDocTemplate(str(PASTA / "Relatorio_Atividade_Extra_2.pdf"), pagesize=A4,
                      leftMargin=50, rightMargin=50, topMargin=42, bottomMargin=45,
                      title="Atividade Extra 2 - Estatística Descritiva - Palmer Penguins",
                      author="").build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()
