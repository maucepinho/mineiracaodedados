# Atividade Extra 2 — Estatística descritiva

## Entrega

- `Relatorio_Atividade_Extra_2.pdf`: respostas dos quatro exercícios.
- `estatistica_pinguins.py`: evidência reproduzível dos cálculos solicitada no enunciado.

Preencha seu nome no relatório antes de enviar pelo Teams.

## Arquivos complementares

- `resultados_estatistica.json`: resultados completos dos cálculos.
- `resumo_estatistico.csv`: tabela com as medidas das três variáveis.
- `gerar_relatorio.py`: gera novamente o PDF usando os cálculos do script principal.
- `MineracaoDados_Atividade2.docx`: orientações originais, preservadas.
- `palmerpenguins_original.csv`: base original, preservada.

## Reproduzir os cálculos

Abra o terminal nesta pasta e execute:

```powershell
py estatistica_pinguins.py
```

Não requer pacotes externos. Os valores ausentes são ignorados por variável, sem substituir por zero ou pela média. O desvio padrão é amostral.

## Gerar novamente o PDF

```powershell
py -m pip install -r requirements.txt
py gerar_relatorio.py
```

Se seu sistema usa `python`, substitua `py` por `python` nos comandos.
