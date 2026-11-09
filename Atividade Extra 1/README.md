# Atividade Extra 1 — Classificação de pinguins com k-NN

Pesquisa e implementação do algoritmo k-Nearest Neighbors para classificar as espécies Adelie, Chinstrap e Gentoo.

## Arquivos

- `pesquisa_knn_pinguins.docx`: pesquisa sobre o modelo escolhido.
- `classificar_pinguins.py`: implementação em Python.
- `palmerpenguins_original.csv`: base utilizada.
- `requirements.txt`: dependências.
- `resultados_knn/`: previsões e matriz de confusão da execução realizada.

## Execução

No terminal, dentro desta pasta:

```powershell
python -m pip install -r requirements.txt
python classificar_pinguins.py
```

Se a instalação do Windows usar o inicializador `py`, substitua `python` por `py`.

## Metodologia

- Alvo: `species`, correspondente ao atributo Species do enunciado.
- Preditores: comprimento e profundidade do bico, comprimento da nadadeira e massa corporal.
- Treino/teste: `test_size=0.30`, `random_state=42`, `stratify=y`.
- Pipeline: imputação pela mediana, `StandardScaler()` e k-NN com 5 vizinhos e distância euclidiana.
- Imputação e padronização ajustadas somente com o treino.

## Resultado registrado

Os arquivos de resultados contêm 104 exemplos de teste, com 103 acertos (99,04%). Um exemplar Gentoo foi previsto como Adelie. A matriz apresenta classes reais nas linhas e previstas nas colunas.

## Fontes

- [Documentação do k-NN no scikit-learn](https://scikit-learn.org/stable/modules/neighbors.html)
- [Palmer Penguins](https://allisonhorst.github.io/palmerpenguins/)
