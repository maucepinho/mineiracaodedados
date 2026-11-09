# Atividade Extra 3 - Raspagem de Dados

O arquivo solicitado para entrega é `raspagem_livros.py`. Ele contém comentários em português, percorre as 50 páginas do catálogo e consulta os detalhes dos 1.000 livros para salvar os seis campos exigidos no PostgreSQL.

O enunciado original foi preservado em `Atividade3-Raspagem.pdf`.

## Executar

Abra o PowerShell nesta pasta e instale as dependências:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Com um servidor PostgreSQL em execução, crie um banco vazio uma única vez. Por exemplo, usando `psql` disponível no PATH:

```powershell
psql -U postgres -c "CREATE DATABASE atividade_extra_3;"
```

Configure a conexão para o seu servidor e execute o script:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "atividade_extra_3"
$env:PGUSER = "postgres"
$env:PGPASSWORD = "sua_senha"
.\.venv\Scripts\python.exe raspagem_livros.py
```

Também é possível definir `DATABASE_URL` com uma URL de conexão PostgreSQL. A tabela e o índice são criados automaticamente pelo script; `criar_tabela.sql` fornece a mesma estrutura para consulta manual. A reexecução atualiza os livros identificados pelo link, sem duplicá-los.

## Dados coletados

| Campo | Origem e tratamento |
| --- | --- |
| `titulo` | Título completo da página do livro, sem o truncamento do catálogo. |
| `categoria` | Categoria no caminho de navegação da página do livro. |
| `preco` | Valor em libras esterlinas (GBP), convertido com `Decimal` e armazenado em `NUMERIC(10,2)`. |
| `avaliacao` | Classes `One` a `Five` convertidas em 1 a 5 estrelas. |
| `disponibilidade` | Texto completo de disponibilidade, incluindo a quantidade em estoque. |
| `link` | URL absoluta da página do livro. |

O script valida as 50 páginas e os 1.000 links únicos antes de gravar os livros. A gravação usa uma transação e parâmetros SQL. Os resultados incluem um CSV em UTF-8 com BOM para facilitar a abertura no Excel e um JSON com contagens e tempos, sem credenciais.

## Tempo de execução

O tempo é medido com `time.perf_counter()`. A execução completa inclui a coleta, a conexão ao PostgreSQL, a criação da estrutura, a inserção e a confirmação da transação. O JSON de resultados registra também os tempos de coleta e banco separadamente.

Na execução completa realizada em **09/11/2026**, das **19:17:01 às 19:18:36** (horário de São Paulo), foram coletadas **50 páginas e 1.000 livros**, com os **1.000 registros confirmados no PostgreSQL 18.0**:

| Etapa | Tempo medido |
| --- | ---: |
| Coleta das páginas e detalhes | 94,665345 s |
| Conexão, estrutura, gravação, conferência e commit no banco | 0,190419 s |
| **Execução completa** | **94,868783 s (aproximadamente 1 min 34,87 s)** |

O total inclui também validações, preparação dos resultados e gravação intermediária dos arquivos. Foram utilizados 4 workers e pausa de 0,15 segundo por requisição/worker. O tempo varia conforme a conexão, o computador e o servidor. Esses números foram medidos na execução real, não estimados. A mesma resposta do item 3 está no comentário inicial do arquivo Python.

A conferência independente comparou todos os seis campos entre o CSV e o banco: 1.000 links únicos, 50 categorias, nenhum campo vazio e avaliações entre 1 e 5. Uma segunda importação manteve exatamente 1.000 registros, comprovando a ausência de duplicação. A exportação SQL também foi restaurada em outro banco temporário, com os 1.000 registros e todos os seis campos conferidos.

## Evidências salvas

- `resultados/livros.csv`: os 1.000 livros coletados.
- `resultados/metadados_execucao.json`: tempos e contagens da execução completa original.
- `resultados/validacao_banco.json`: conferência independente dos registros e da reimportação.
- `resultados/livros_postgresql.sql`: exportação real do banco, com estrutura e 1.000 registros.

A execução de validação utilizou um PostgreSQL temporário e isolado, encerrado após a conferência. Para usar os dados em seu próprio servidor, execute o script ou restaure a exportação em um banco vazio, com cliente/servidor PostgreSQL 18:

```powershell
psql -U postgres -c "CREATE DATABASE atividade_extra_3_restaurada;"
psql -U postgres -d atividade_extra_3_restaurada -v ON_ERROR_STOP=1 -f resultados/livros_postgresql.sql
```

## Reproduzir a partir do CSV

O modo de importação usa o CSV já coletado e evita repetir o acesso ao site. Seu tempo mede apenas a leitura, validação e persistência; ele não substitui o tempo da raspagem completa. Consulte os argumentos disponíveis:

```powershell
.\.venv\Scripts\python.exe raspagem_livros.py --importar-csv resultados/livros.csv --saida resultados_importacao
```

Use `--saida` para manter os metadados dessa importação separados dos tempos da execução completa. O modo `--somente-coleta` coleta e salva o CSV sem gravar no banco e, portanto, não satisfaz sozinho o item 2 da atividade. `--workers` permite de 1 a 4 conexões paralelas de detalhe, e `--pausa` controla a espera entre requisições de cada worker (padrão de 0,15 segundo). Para ver todas as opções, execute `raspagem_livros.py --help`.

Fonte dos dados: [Books to Scrape](https://books.toscrape.com/), site de demonstração destinado à prática de raspagem. Os preços e as avaliações são dados fictícios de demonstração.
