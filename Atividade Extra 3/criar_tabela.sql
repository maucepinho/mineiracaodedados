-- Estrutura solicitada no enunciado.
CREATE TABLE IF NOT EXISTS livros (
    id SERIAL PRIMARY KEY,
    titulo TEXT NOT NULL,
    categoria TEXT NOT NULL,
    preco NUMERIC(10, 2) NOT NULL CHECK (preco >= 0),
    avaliacao INTEGER NOT NULL CHECK (avaliacao BETWEEN 1 AND 5),
    disponibilidade TEXT NOT NULL,
    link TEXT NOT NULL
);

-- O link identifica cada livro e impede duplicação em novas execuções.
CREATE UNIQUE INDEX IF NOT EXISTS livros_link_unico ON livros (link);
