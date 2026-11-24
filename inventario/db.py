"""Camada de acesso ao banco de dados do inventário (SQLite)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
TIPOS_MOVIMENTACAO = ("ENTRADA", "SAIDA")


class InventarioError(Exception):
    """Erro de regra de negócio do inventário."""


class ProdutoNaoEncontradoError(InventarioError):
    pass


class ProdutoDuplicadoError(InventarioError):
    pass


class EstoqueInsuficienteError(InventarioError):
    pass


def conectar(caminho: str | Path = ":memory:") -> sqlite3.Connection:
    """Abre (e cria, se preciso) o banco, aplicando o esquema."""
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    return conn


def _normalizar_sku(sku: str) -> str:
    return sku.strip().upper()


def _obter_ou_criar_categoria(conn: sqlite3.Connection, nome: str) -> int:
    nome = nome.strip()
    conn.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (?)", (nome,))
    return conn.execute("SELECT id FROM categorias WHERE nome = ?", (nome,)).fetchone()[0]


def _produto_id(conn: sqlite3.Connection, sku: str) -> int:
    linha = conn.execute(
        "SELECT id FROM produtos WHERE sku = ? AND ativo = 1", (_normalizar_sku(sku),)
    ).fetchone()
    if linha is None:
        raise ProdutoNaoEncontradoError(f"Produto não encontrado: {sku}")
    return linha[0]


def cadastrar_produto(
    conn: sqlite3.Connection,
    sku: str,
    nome: str,
    categoria: str | None = None,
    preco_custo: float = 0.0,
    estoque_minimo: int = 0,
) -> int:
    """Cadastra um produto e devolve o seu id."""
    sku = _normalizar_sku(sku)
    if not sku or not nome.strip():
        raise ValueError("SKU e nome são obrigatórios")
    if preco_custo < 0 or estoque_minimo < 0:
        raise ValueError("Preço de custo e estoque mínimo não podem ser negativos")

    try:
        with conn:
            categoria_id = (
                _obter_ou_criar_categoria(conn, categoria) if categoria else None
            )
            cursor = conn.execute(
                "INSERT INTO produtos (sku, nome, categoria_id, preco_custo, estoque_minimo)"
                " VALUES (?, ?, ?, ?, ?)",
                (sku, nome.strip(), categoria_id, preco_custo, estoque_minimo),
            )
    except sqlite3.IntegrityError as erro:
        raise ProdutoDuplicadoError(f"SKU já cadastrado: {sku}") from erro
    return cursor.lastrowid


def saldo(conn: sqlite3.Connection, sku: str) -> int:
    """Saldo atual de um produto."""
    linha = conn.execute(
        "SELECT saldo FROM vw_saldo_estoque WHERE sku = ?", (_normalizar_sku(sku),)
    ).fetchone()
    if linha is None:
        raise ProdutoNaoEncontradoError(f"Produto não encontrado: {sku}")
    return linha[0]


def registrar_movimentacao(
    conn: sqlite3.Connection,
    sku: str,
    tipo: str,
    quantidade: int,
    observacao: str | None = None,
) -> int:
    """Registra uma ENTRADA ou SAIDA e devolve o novo saldo do produto."""
    tipo = tipo.upper()
    if tipo not in TIPOS_MOVIMENTACAO:
        raise ValueError(f"Tipo inválido: {tipo}. Use ENTRADA ou SAIDA")
    if not isinstance(quantidade, int) or quantidade <= 0:
        raise ValueError("A quantidade deve ser um número inteiro maior que zero")

    produto_id = _produto_id(conn, sku)
    try:
        with conn:
            conn.execute(
                "INSERT INTO movimentacoes (produto_id, tipo, quantidade, observacao)"
                " VALUES (?, ?, ?, ?)",
                (produto_id, tipo, quantidade, observacao),
            )
    except sqlite3.IntegrityError as erro:
        # A trigger do banco avisa quando a saída é maior que o saldo.
        if "Estoque insuficiente" in str(erro):
            raise EstoqueInsuficienteError(
                f"Estoque insuficiente para {_normalizar_sku(sku)}: "
                f"saldo atual {saldo(conn, sku)}, saída pedida {quantidade}"
            ) from erro
        raise
    return saldo(conn, sku)


def listar_estoque(
    conn: sqlite3.Connection, apenas_abaixo_minimo: bool = False
) -> list[sqlite3.Row]:
    consulta = "SELECT * FROM vw_saldo_estoque"
    if apenas_abaixo_minimo:
        consulta += " WHERE saldo < estoque_minimo"
    return conn.execute(consulta + " ORDER BY nome").fetchall()


def historico(conn: sqlite3.Connection, sku: str, limite: int = 20) -> list[sqlite3.Row]:
    """Últimas movimentações de um produto (mais recentes primeiro)."""
    produto_id = _produto_id(conn, sku)
    return conn.execute(
        "SELECT data_hora, tipo, quantidade, observacao FROM movimentacoes"
        " WHERE produto_id = ? ORDER BY id DESC LIMIT ?",
        (produto_id, limite),
    ).fetchall()


def valor_total_estoque(conn: sqlite3.Connection) -> float:
    """Valor de todo o estoque a preço de custo."""
    return conn.execute(
        "SELECT COALESCE(SUM(saldo * preco_custo), 0) FROM vw_saldo_estoque"
    ).fetchone()[0]


def popular_exemplo(conn: sqlite3.Connection) -> None:
    """Carrega os dados fictícios de sql/dados_exemplo.sql (só em banco vazio)."""
    if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]:
        raise InventarioError("O banco já possui produtos; use um arquivo novo para o demo")
    conn.executescript((SQL_DIR / "dados_exemplo.sql").read_text(encoding="utf-8"))
