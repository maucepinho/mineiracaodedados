"""Resolve os quatro exercícios usando somente a biblioteca padrão.

Execute: py estatistica_pinguins.py
Os valores ausentes são ignorados separadamente em cada variável.
"""
import csv
import json
import math
import statistics as st
from collections import Counter
from pathlib import Path

PASTA = Path(__file__).resolve().parent
VARIAVEIS = ("body_mass_g", "bill_length_mm", "flipper_length_mm")


def calcular():
    with (PASTA / "palmerpenguins_original.csv").open(encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    frequencias = Counter(linha["species"] for linha in linhas)
    resumo = {}
    for coluna in VARIAVEIS:
        valores = []
        for linha in linhas:
            texto = linha[coluna].strip()
            if texto.lower() in ("", "na", "nan", "null"):
                continue
            valor = float(texto)
            if math.isfinite(valor):
                valores.append(valor)
        contagem = Counter(valores)
        resumo[coluna] = {
            "n_validos": len(valores), "ausentes": len(linhas) - len(valores),
            "media": st.mean(valores), "mediana": st.median(valores),
            "modas": sorted(st.multimode(valores)),
            "frequencia_moda": max(contagem.values()),
            "desvio_padrao_amostral": st.stdev(valores),
            "minimo": min(valores), "maximo": max(valores),
        }
    massa = resumo["body_mass_g"]
    return {
        "total_registros": len(linhas),
        "frequencias": {k: {"absoluta": v, "relativa_percentual": v / len(linhas) * 100}
                        for k, v in sorted(frequencias.items())},
        "especie_mais_frequente": max(frequencias, key=frequencias.get),
        "diferenca_maior_menor_frequencia": max(frequencias.values()) - min(frequencias.values()),
        "estatisticas": resumo,
        "z_massa_maxima": (massa["maximo"] - massa["media"]) / massa["desvio_padrao_amostral"],
        "z_massa_minima": (massa["minimo"] - massa["media"]) / massa["desvio_padrao_amostral"],
    }


def salvar(resultados):
    (PASTA / "resultados_estatistica.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    with (PASTA / "resumo_estatistico.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variavel", "n_validos", "ausentes", "media", "mediana", "modas",
                         "frequencia_moda", "desvio_padrao_amostral", "minimo", "maximo"])
        for variavel, e in resultados["estatisticas"].items():
            writer.writerow([variavel, e["n_validos"], e["ausentes"], e["media"], e["mediana"],
                             "; ".join(map(str, e["modas"])), e["frequencia_moda"],
                             e["desvio_padrao_amostral"], e["minimo"], e["maximo"]])


if __name__ == "__main__":
    resultados = calcular()
    salvar(resultados)
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
