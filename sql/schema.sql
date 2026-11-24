-- Esquema do banco de dados do controle de inventário (SQLite).
-- Pode ser executado várias vezes: tudo usa IF NOT EXISTS.

PRAGMA foreign_keys = ON;

-- Categorias dos produtos (Periféricos, Eletrônicos, ...)
CREATE TABLE IF NOT EXISTS categorias (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

-- Cadastro de produtos
CREATE TABLE IF NOT EXISTS produtos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    sku            TEXT    NOT NULL UNIQUE,
    nome           TEXT    NOT NULL,
    categoria_id   INTEGER REFERENCES categorias (id),
    preco_custo    REAL    NOT NULL DEFAULT 0 CHECK (preco_custo >= 0),
    estoque_minimo INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    ativo          INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

-- Cada entrada ou saída de estoque. O saldo NÃO é gravado em lugar nenhum:
-- é sempre calculado a partir das movimentações (veja a view abaixo), o que
-- evita saldo desatualizado ou divergente.
CREATE TABLE IF NOT EXISTS movimentacoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos (id),
    tipo       TEXT    NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA')),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    observacao TEXT,
    data_hora  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP  -- UTC
);

CREATE INDEX IF NOT EXISTS idx_mov_produto_data
    ON movimentacoes (produto_id, data_hora);

-- Impede saldo negativo diretamente no banco, mesmo que alguém insira
-- dados por fora da aplicação.
CREATE TRIGGER IF NOT EXISTS trg_bloqueia_saldo_negativo
BEFORE INSERT ON movimentacoes
WHEN NEW.tipo = 'SAIDA'
BEGIN
    SELECT RAISE(ABORT, 'Estoque insuficiente')
    WHERE (
        SELECT COALESCE(SUM(CASE tipo WHEN 'ENTRADA' THEN quantidade
                                      ELSE -quantidade END), 0)
        FROM movimentacoes
        WHERE produto_id = NEW.produto_id
    ) < NEW.quantidade;
END;

-- Saldo atual de cada produto ativo.
CREATE VIEW IF NOT EXISTS vw_saldo_estoque AS
SELECT
    p.id             AS produto_id,
    p.sku            AS sku,
    p.nome           AS nome,
    c.nome           AS categoria,
    p.preco_custo    AS preco_custo,
    p.estoque_minimo AS estoque_minimo,
    COALESCE(SUM(CASE m.tipo WHEN 'ENTRADA' THEN  m.quantidade
                             WHEN 'SAIDA'   THEN -m.quantidade END), 0) AS saldo
FROM produtos p
LEFT JOIN categorias    c ON c.id = p.categoria_id
LEFT JOIN movimentacoes m ON m.produto_id = p.id
WHERE p.ativo = 1
GROUP BY p.id;
