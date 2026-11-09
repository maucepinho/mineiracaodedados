"""Raspa os 1.000 livros de Books to Scrape e os persiste no PostgreSQL.

Execução: python raspagem_livros.py
Somente CSV: python raspagem_livros.py --somente-coleta
Importação offline: python raspagem_livros.py --importar-csv resultados/livros.csv

Configure DATABASE_URL ou as variáveis PGHOST, PGPORT, PGDATABASE, PGUSER e
PGPASSWORD. A senha e a string de conexão nunca são gravadas nos resultados.

Resposta do item 3:
50 páginas, 1.000 livros coletados e confirmados no PostgreSQL 18.0.
Tempo total de coleta e persistência: 94.868783 segundos (1 min 34,87 s).
Coleta: 94.665345 s; banco, incluindo COMMIT: 0.190419 s.
Medição com 4 workers e pausa de 0,15 s por requisição/worker.
São tempos desta execução; o programa mede novamente em cada execução.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlparse


# Centraliza o endereço, as quantidades exigidas e o significado das estrelas.
PASTA = Path(__file__).resolve().parent
URL_INICIAL = "https://books.toscrape.com/"
TOTAL_PAGINAS = 50
TOTAL_LIVROS = 1000
COLUNAS = ("titulo", "categoria", "preco", "avaliacao", "disponibilidade", "link")
ESTRELAS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# A estrutura segue o enunciado, com restrições que evitam valores inválidos.
SQL_TABELA = """
CREATE TABLE IF NOT EXISTS livros (
    id SERIAL PRIMARY KEY,
    titulo TEXT NOT NULL,
    categoria TEXT NOT NULL,
    preco NUMERIC(10,2) NOT NULL CHECK (preco >= 0),
    avaliacao INTEGER NOT NULL CHECK (avaliacao BETWEEN 1 AND 5),
    disponibilidade TEXT NOT NULL,
    link TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS livros_link_unico ON livros (link);
"""

# Parâmetros %s são enviados pelo driver, sem concatenar os dados ao SQL.
# Se o link já existir, atualiza seus campos em vez de criar outro livro.
SQL_INSERIR = """
INSERT INTO livros (titulo, categoria, preco, avaliacao, disponibilidade, link)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (link) DO UPDATE SET
    titulo = EXCLUDED.titulo,
    categoria = EXCLUDED.categoria,
    preco = EXCLUDED.preco,
    avaliacao = EXCLUDED.avaliacao,
    disponibilidade = EXCLUDED.disponibilidade;
"""


class ErroAtividade(Exception):
    """Erro conhecido cuja mensagem pode ser exibida sem expor credenciais."""


def agora_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def texto(elemento) -> str:
    """Remove somente espaços de apresentação, mantendo o conteúdo textual."""
    if elemento is None:
        raise ErroAtividade("Um campo obrigatório não foi encontrado no HTML.")
    return " ".join(elemento.get_text(" ", strip=True).split())


def validar_url(url: str) -> str:
    partes = urlparse(url)
    if (partes.scheme not in ("http", "https")
            or partes.netloc != "books.toscrape.com"
            or partes.query or partes.fragment):
        raise ErroAtividade("Foi encontrado um link fora do catálogo esperado.")
    return url


def converter_preco(valor: str) -> Decimal:
    limpo = valor.removeprefix("£").strip()
    if not re.fullmatch(r"\d+\.\d{2}", limpo):
        raise ErroAtividade("Preço inválido: esperava-se um valor com duas casas decimais.")
    try:
        preco = Decimal(limpo)
    except InvalidOperation as exc:
        raise ErroAtividade("Preço inválido no catálogo ou CSV.") from exc
    if not Decimal("0.00") <= preco <= Decimal("99999999.99"):
        raise ErroAtividade("Preço fora dos limites do tipo NUMERIC(10,2).")
    return preco


def validar_livros(livros: list[dict]) -> None:
    """Impede que resultados incompletos ou duplicados sejam tratados como sucesso."""
    if len(livros) != TOTAL_LIVROS:
        raise ErroAtividade(f"Esperavam-se {TOTAL_LIVROS} livros; recebidos {len(livros)}.")
    links = set()
    for livro in livros:
        if any(not str(livro.get(c, "")).strip() for c in COLUNAS):
            raise ErroAtividade("Existe um livro com campo obrigatório vazio.")
        validar_url(livro["link"])
        if not livro["link"].endswith("/index.html"):
            raise ErroAtividade("Um link de livro não aponta para uma página de detalhes.")
        if livro["link"] in links:
            raise ErroAtividade("Existem links de livros duplicados.")
        links.add(livro["link"])
        converter_preco(format(livro["preco"], ".2f"))
        if not isinstance(livro["avaliacao"], int) or not 1 <= livro["avaliacao"] <= 5:
            raise ErroAtividade("A avaliação deve ser um inteiro entre 1 e 5.")


def criar_sessao():
    """Reutiliza conexões HTTP e tenta novamente em falhas transitórias."""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    sessao = requests.Session()
    sessao.headers.update({"User-Agent": "AtividadeExtra3-RaspagemEducacional/1.0"})
    tentativas = Retry(
        total=3, connect=3, read=3, status=3, backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}), respect_retry_after_header=True,
    )
    adaptador = HTTPAdapter(max_retries=tentativas, pool_connections=1, pool_maxsize=1)
    sessao.mount("https://", adaptador)
    sessao.mount("http://", adaptador)
    return sessao


class Coletor:
    """Mantém uma Session por thread e limita a coleta a poucas conexões."""

    def __init__(self, pausa: float):
        self.pausa = pausa
        self.local = threading.local()
        self.sessoes = []
        self.trava = threading.Lock()

    def obter_html(self, url: str):
        from bs4 import BeautifulSoup

        validar_url(url)
        if not hasattr(self.local, "sessao"):
            self.local.sessao = criar_sessao()
            with self.trava:
                self.sessoes.append(self.local.sessao)
        # A pausa é aplicada em cada worker; retries também têm backoff.
        time.sleep(self.pausa)
        resposta = self.local.sessao.get(url, timeout=(10, 45))
        resposta.raise_for_status()
        validar_url(resposta.url)
        # O catálogo é UTF-8, mesmo quando o cabeçalho HTTP sugere outro charset.
        resposta.encoding = "utf-8"
        return BeautifulSoup(resposta.text, "html.parser")

    def catalogar_links(self) -> tuple[list[str], int]:
        """Segue o botão next até o fim, conferindo páginas e links únicos."""
        url = URL_INICIAL
        paginas, links, vistos = set(), [], set()
        while url:
            if url in paginas or len(paginas) >= TOTAL_PAGINAS:
                raise ErroAtividade("A paginação apresentou repetição ou páginas excedentes.")
            sopa = self.obter_html(url)
            paginas.add(url)
            artigos = sopa.select("article.product_pod h3 a")
            if not artigos:
                raise ErroAtividade("Uma página do catálogo não apresentou livros.")
            for ancora in artigos:
                link = validar_url(urljoin(url, ancora["href"]))
                if link in vistos:
                    raise ErroAtividade("Um livro apareceu mais de uma vez na paginação.")
                vistos.add(link)
                links.append(link)
            proxima = sopa.select_one("li.next a")
            url = validar_url(urljoin(url, proxima["href"])) if proxima else None
        if len(paginas) != TOTAL_PAGINAS or len(links) != TOTAL_LIVROS:
            raise ErroAtividade(
                f"Catálogo incompleto: {len(paginas)} páginas e {len(links)} links; "
                f"esperados {TOTAL_PAGINAS} e {TOTAL_LIVROS}."
            )
        return links, len(paginas)

    def detalhar_livro(self, link: str) -> dict:
        """Extrai os seis campos solicitados dos seletores HTML do detalhe."""
        sopa = self.obter_html(link)
        principal = sopa.select_one("div.product_main")
        if principal is None:
            raise ErroAtividade("Página de detalhes sem o bloco principal do livro.")
        trilha = sopa.select("ul.breadcrumb li")
        if len(trilha) < 4:
            raise ErroAtividade("Não foi possível identificar a categoria na navegação.")
        classificacao = principal.select_one("p.star-rating")
        classes = classificacao.get("class", []) if classificacao else []
        notas = [ESTRELAS[c] for c in classes if c in ESTRELAS]
        if len(notas) != 1:
            raise ErroAtividade("Avaliação por estrelas ausente ou inválida.")
        return {
            "titulo": texto(principal.select_one("h1")),
            "categoria": texto(trilha[-2].select_one("a")),
            "preco": converter_preco(texto(principal.select_one("p.price_color"))),
            "avaliacao": notas[0],
            "disponibilidade": texto(principal.select_one("p.availability")),
            "link": link,
        }

    def fechar(self) -> None:
        for sessao in self.sessoes:
            sessao.close()


def coletar_livros(workers: int, pausa: float) -> tuple[list[dict], int]:
    """Coleta detalhes com poucas threads e preserva a ordem do catálogo."""
    coletor = Coletor(pausa)
    try:
        links, paginas = coletor.catalogar_links()
        print(f"Catálogo validado: {paginas} páginas e {len(links)} links únicos.", flush=True)
        encontrados = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futuros = {executor.submit(coletor.detalhar_livro, link): link for link in links}
            try:
                for futuro in as_completed(futuros):
                    link = futuros[futuro]
                    encontrados[link] = futuro.result()
                    if len(encontrados) % 100 == 0:
                        print(f"Detalhes coletados: {len(encontrados)}/{TOTAL_LIVROS}.", flush=True)
            except Exception:
                # As tarefas ainda não iniciadas são canceladas em caso de falha.
                for futuro in futuros:
                    futuro.cancel()
                raise
        livros = [encontrados[link] for link in links]
        validar_livros(livros)
        return livros, paginas
    finally:
        coletor.fechar()


def salvar_csv(livros: list[dict], destino: Path) -> None:
    """Grava uma cópia dos dados para conferência e importação sem rede."""
    temporario = destino.with_suffix(".csv.tmp")
    with temporario.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        for livro in livros:
            escritor.writerow({**livro, "preco": format(livro["preco"], ".2f")})
    temporario.replace(destino)


def ler_csv(origem: Path) -> list[dict]:
    """Reconstrói os tipos numéricos e valida os 1.000 livros de um CSV."""
    with origem.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames != list(COLUNAS):
            raise ErroAtividade("O CSV deve conter, nesta ordem: " + ", ".join(COLUNAS))
        livros = []
        for linha in leitor:
            try:
                linha["preco"] = converter_preco(linha["preco"])
                linha["avaliacao"] = int(linha["avaliacao"])
            except (TypeError, ValueError) as exc:
                raise ErroAtividade("O CSV contém um preço ou uma avaliação inválida.") from exc
            livros.append(linha)
    validar_livros(livros)
    return livros


def persistir_livros(livros: list[dict]) -> tuple[int, float]:
    """Cria/atualiza e confere os 1.000 links em uma única transação."""
    inicio = time.perf_counter()
    try:
        import psycopg
    except ImportError as exc:
        raise ErroAtividade("Instale psycopg[binary] para usar o PostgreSQL.") from exc
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn and not os.environ.get("PGDATABASE"):
        raise ErroAtividade("Configure DATABASE_URL ou as variáveis PG*, incluindo PGDATABASE.")
    try:
        # O contexto confirma tudo ao sair normalmente e reverte em qualquer erro.
        with psycopg.connect(dsn, connect_timeout=10) as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(SQL_TABELA)
                cursor.executemany(SQL_INSERIR, [tuple(livro[c] for c in COLUNAS) for livro in livros])
                cursor.execute(
                    "SELECT COUNT(*) FROM livros WHERE link = ANY(%s)",
                    ([livro["link"] for livro in livros],),
                )
                quantidade = cursor.fetchone()[0]
                if quantidade != TOTAL_LIVROS:
                    raise ErroAtividade("A conferência no banco não encontrou todos os 1.000 links.")
        # A medição inclui conexão, DDL, inserção, validação, COMMIT e fechamento.
        return quantidade, time.perf_counter() - inicio
    except psycopg.Error as exc:
        # Não exibir a exceção original: mensagens de conexão podem conter segredos.
        raise ErroAtividade(
            "Falha ao conectar ou persistir no PostgreSQL. Nenhum sucesso foi confirmado; "
            "confira a conexão, as permissões e o esquema da tabela livros."
        ) from exc


def salvar_metadados(metadados: dict, destino: Path) -> None:
    """Registra contagens e tempos, substituindo o JSON de forma atômica."""
    temporario = destino.with_suffix(".json.tmp")
    temporario.write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(destino)


def main() -> int:
    # A linha de comando escolhe a execução completa, só coleta ou importação.
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--somente-coleta", action="store_true", help="Salva CSV sem acessar o banco.")
    modo.add_argument("--importar-csv", type=Path, metavar="ARQUIVO", help="Importa CSV sem acessar o site.")
    parser.add_argument("--saida", type=Path, default=PASTA / "resultados")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--pausa", type=float, default=0.15, help="Pausa por request/worker; mínimo 0,1 s.")
    args = parser.parse_args()
    if not 0.1 <= args.pausa <= 60:
        parser.error("--pausa deve ficar entre 0.1 e 60 segundos.")

    # Relógio monotônico: mede a duração sem depender de ajustes na hora do PC.
    inicio = time.perf_counter()
    importacao = args.importar_csv is not None
    saida = args.saida.resolve()
    saida.mkdir(parents=True, exist_ok=True)
    arquivo_metadados = saida / "metadados_execucao.json"
    # Começa sem sucesso confirmado; a flag do banco só muda após o COMMIT.
    metadados = {
        "status": "iniciado",
        "modo": "importacao_csv" if importacao else ("somente_coleta" if args.somente_coleta else "coleta_e_banco"),
        "inicio_utc": agora_utc(),
        "fim_utc": None,
        "fonte": URL_INICIAL,
        "moeda_preco": "GBP",
        "registros_esperados": TOTAL_LIVROS,
        "paginas_coletadas": None,
        "registros_validados": 0,
        "registros_confirmados_banco": 0,
        "banco_validado": False,
        "tempo_coleta_segundos": None,
        "tempo_leitura_csv_segundos": None,
        "tempo_banco_segundos": None,
        "tempo_total_coleta_e_persistencia_segundos": None,
        "tempo_total_importacao_segundos": None,
        "workers": None if importacao else args.workers,
        "pausa_por_request_segundos": None if importacao else args.pausa,
    }
    salvar_metadados(metadados, arquivo_metadados)
    try:
        # Separa a duração da coleta online da leitura de um CSV já existente.
        inicio_etapa = time.perf_counter()
        if importacao:
            livros = ler_csv(args.importar_csv.resolve())
            metadados["tempo_leitura_csv_segundos"] = round(time.perf_counter() - inicio_etapa, 6)
        else:
            livros, paginas = coletar_livros(args.workers, args.pausa)
            metadados["tempo_coleta_segundos"] = round(time.perf_counter() - inicio_etapa, 6)
            metadados["paginas_coletadas"] = paginas
        metadados["registros_validados"] = len(livros)
        salvar_csv(livros, saida / "livros.csv")
        # O modo padrão só termina com sucesso depois de salvar no PostgreSQL.
        if not args.somente_coleta:
            quantidade, duracao = persistir_livros(livros)
            metadados["registros_confirmados_banco"] = quantidade
            metadados["tempo_banco_segundos"] = round(duracao, 6)
            metadados["banco_validado"] = True
        metadados["status"] = "coleta_concluida_sem_banco" if args.somente_coleta else "concluido"
        codigo = 0
    except Exception as exc:
        metadados["status"] = "falhou"
        mensagem = str(exc) if isinstance(exc, ErroAtividade) else (
            f"Falha do tipo {type(exc).__name__}; a execução não foi concluída."
        )
        metadados["erro"] = mensagem
        print(mensagem, flush=True)
        codigo = 1
    finally:
        # Registra inclusive falhas, sem apresentar uma coleta parcial como sucesso.
        total = round(time.perf_counter() - inicio, 6)
        if importacao:
            metadados["tempo_total_importacao_segundos"] = total
        elif not args.somente_coleta:
            metadados["tempo_total_coleta_e_persistencia_segundos"] = total
        metadados["tempo_total_execucao_segundos"] = total
        metadados["fim_utc"] = agora_utc()
        salvar_metadados(metadados, arquivo_metadados)
    if codigo == 0:
        if args.somente_coleta:
            print("Coleta concluída: 1.000 livros no CSV. O banco não foi acessado.")
        else:
            print("Execução concluída: 1.000 livros validados e confirmados no PostgreSQL.")
        print(f"Tempo desta execução: {total:.3f} segundos. Resultados: {saida}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
