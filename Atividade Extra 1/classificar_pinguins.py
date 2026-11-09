"""Classificação de pinguins com k-NN.

Instalação: python -m pip install -r requirements.txt
Execução: python classificar_pinguins.py
Opcional: python classificar_pinguins.py caminho/para/base.csv
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", type=Path,
                        default=Path(__file__).with_name("palmerpenguins_original.csv"))
    args = parser.parse_args()
    dados = pd.read_csv(args.csv)
    # A base fornecida usa species; aceitar Species sem alterar o significado.
    dados.columns = dados.columns.str.strip().str.lower()
    atributos = ["bill_length_mm", "bill_depth_mm",
                 "flipper_length_mm", "body_mass_g"]
    faltantes = set(atributos + ["species"]) - set(dados.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes: {sorted(faltantes)}")
    # Não é possível treinar/avaliar registros sem classe conhecida.
    dados = dados.dropna(subset=["species"]).copy()
    X = dados[atributos].apply(pd.to_numeric, errors="raise")
    y = dados["species"]
    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    # fit calcula medianas, médias e desvios SOMENTE com o treino.
    # predict reutiliza essas estatísticas ao transformar o teste.
    modelo = Pipeline([
        ("imputacao", SimpleImputer(strategy="median")),
        ("normalizacao", StandardScaler()),
        ("classificador", KNeighborsClassifier(
            n_neighbors=5, weights="uniform", metric="euclidean"
        )),
    ])
    modelo.fit(X_treino, y_treino)
    previsoes = modelo.predict(X_teste)
    classes = modelo.named_steps["classificador"].classes_
    matriz = pd.DataFrame(confusion_matrix(y_teste, previsoes, labels=classes),
                          index=classes, columns=classes)
    matriz.index.name = "Real / prevista"
    print(f"Treino: {len(X_treino)} | Teste: {len(X_teste)}")
    print("\nDistribuição por espécie:")
    print(pd.DataFrame({"treino": y_treino.value_counts(),
                        "teste": y_teste.value_counts()}).sort_index())
    print(f"\nAcurácia: {accuracy_score(y_teste, previsoes):.2%}")
    print("\nRelatório de classificação:")
    print(classification_report(y_teste, previsoes, digits=4, zero_division=0))
    print("Matriz de confusão (linhas reais, colunas previstas):")
    print(matriz)
    destino = Path(__file__).parent / "resultados_knn"
    destino.mkdir(exist_ok=True)
    matriz.to_csv(destino / "matriz_confusao.csv", encoding="utf-8-sig")
    pd.DataFrame({"linha_csv": X_teste.index + 2,
                  "especie_real": y_teste,
                  "especie_prevista": previsoes}).to_csv(
                      destino / "previsoes.csv", index=False, encoding="utf-8-sig")
    print(f"\nResultados salvos em: {destino}")


if __name__ == "__main__":
    main()
