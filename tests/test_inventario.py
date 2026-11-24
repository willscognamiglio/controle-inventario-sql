import sqlite3

import pytest

from inventario import (
    EstoqueInsuficienteError,
    ProdutoDuplicadoError,
    ProdutoNaoEncontradoError,
    cadastrar_produto,
    conectar,
    historico,
    listar_estoque,
    popular_exemplo,
    registrar_movimentacao,
    saldo,
    valor_total_estoque,
)
from inventario.db import InventarioError, SQL_DIR


@pytest.fixture
def conn():
    conexao = conectar(":memory:")
    yield conexao
    conexao.close()


@pytest.fixture
def conn_demo(conn):
    popular_exemplo(conn)
    return conn


def test_cadastrar_produto_e_listar(conn):
    cadastrar_produto(conn, "mn-1", "Monitor", "Eletrônicos", 650.0, 5)
    estoque = listar_estoque(conn)
    assert len(estoque) == 1
    assert estoque[0]["sku"] == "MN-1"  # SKU é normalizado
    assert estoque[0]["categoria"] == "Eletrônicos"
    assert estoque[0]["saldo"] == 0


def test_categoria_e_reaproveitada(conn):
    cadastrar_produto(conn, "A", "Produto A", "Periféricos")
    cadastrar_produto(conn, "B", "Produto B", "Periféricos")
    total = conn.execute("SELECT COUNT(*) FROM categorias").fetchone()[0]
    assert total == 1


def test_sku_duplicado(conn):
    cadastrar_produto(conn, "A", "Produto A")
    with pytest.raises(ProdutoDuplicadoError):
        cadastrar_produto(conn, " a ", "Outro nome")


@pytest.mark.parametrize(
    "kwargs",
    [{"sku": "", "nome": "X"}, {"sku": "A", "nome": "  "}, {"sku": "A", "nome": "X", "preco_custo": -1}],
)
def test_cadastro_invalido(conn, kwargs):
    with pytest.raises(ValueError):
        cadastrar_produto(conn, **kwargs)


def test_entradas_e_saidas_atualizam_saldo(conn):
    cadastrar_produto(conn, "A", "Produto A")
    assert registrar_movimentacao(conn, "A", "ENTRADA", 10) == 10
    assert registrar_movimentacao(conn, "a", "saida", 3, "venda") == 7
    assert saldo(conn, "A") == 7


def test_saida_maior_que_saldo_e_bloqueada(conn):
    cadastrar_produto(conn, "A", "Produto A")
    registrar_movimentacao(conn, "A", "ENTRADA", 5)
    with pytest.raises(EstoqueInsuficienteError, match="saldo atual 5"):
        registrar_movimentacao(conn, "A", "SAIDA", 6)
    assert saldo(conn, "A") == 5  # nada foi gravado


def test_saida_do_saldo_exato_e_permitida(conn):
    cadastrar_produto(conn, "A", "Produto A")
    registrar_movimentacao(conn, "A", "ENTRADA", 5)
    assert registrar_movimentacao(conn, "A", "SAIDA", 5) == 0


def test_trigger_protege_mesmo_sem_a_aplicacao(conn):
    """Um INSERT direto no banco também não consegue deixar o saldo negativo."""
    cadastrar_produto(conn, "A", "Produto A")
    with pytest.raises(sqlite3.IntegrityError, match="Estoque insuficiente"):
        conn.execute(
            "INSERT INTO movimentacoes (produto_id, tipo, quantidade)"
            " SELECT id, 'SAIDA', 1 FROM produtos WHERE sku = 'A'"
        )


@pytest.mark.parametrize("quantidade", [0, -2, 1.5, "3"])
def test_quantidade_invalida(conn, quantidade):
    cadastrar_produto(conn, "A", "Produto A")
    with pytest.raises(ValueError):
        registrar_movimentacao(conn, "A", "ENTRADA", quantidade)


def test_tipo_invalido(conn):
    cadastrar_produto(conn, "A", "Produto A")
    with pytest.raises(ValueError):
        registrar_movimentacao(conn, "A", "TRANSFERENCIA", 1)


def test_produto_inexistente(conn):
    with pytest.raises(ProdutoNaoEncontradoError):
        registrar_movimentacao(conn, "XYZ", "ENTRADA", 1)
    with pytest.raises(ProdutoNaoEncontradoError):
        saldo(conn, "XYZ")


def test_historico_mais_recente_primeiro(conn):
    cadastrar_produto(conn, "A", "Produto A")
    registrar_movimentacao(conn, "A", "ENTRADA", 10, "compra")
    registrar_movimentacao(conn, "A", "SAIDA", 2, "venda")
    linhas = historico(conn, "A")
    assert [(r["tipo"], r["quantidade"]) for r in linhas] == [("SAIDA", 2), ("ENTRADA", 10)]


def test_abaixo_do_minimo_e_valor_total(conn):
    cadastrar_produto(conn, "A", "Produto A", preco_custo=10.0, estoque_minimo=5)
    cadastrar_produto(conn, "B", "Produto B", preco_custo=2.5, estoque_minimo=1)
    registrar_movimentacao(conn, "A", "ENTRADA", 3)
    registrar_movimentacao(conn, "B", "ENTRADA", 4)
    assert [r["sku"] for r in listar_estoque(conn, apenas_abaixo_minimo=True)] == ["A"]
    assert valor_total_estoque(conn) == pytest.approx(3 * 10.0 + 4 * 2.5)


# ---- dados de exemplo e consultas SQL -------------------------------------


def test_dados_de_exemplo(conn_demo):
    abaixo = {r["sku"] for r in listar_estoque(conn_demo, apenas_abaixo_minimo=True)}
    assert abaixo == {"CB-100", "TC-020"}
    assert saldo(conn_demo, "MS-010") == 25


def test_demo_nao_roda_duas_vezes(conn_demo):
    with pytest.raises(InventarioError):
        popular_exemplo(conn_demo)


def executar_consultas(conn):
    """Executa cada consulta de consultas.sql e devolve os resultados em ordem."""
    resultados, bloco = [], ""
    for linha in (SQL_DIR / "consultas.sql").read_text(encoding="utf-8").splitlines():
        bloco += linha + "\n"
        if sqlite3.complete_statement(bloco):
            resultados.append(conn.execute(bloco).fetchall())
            bloco = ""
    return resultados


def test_consultas_sql_executam_e_retornam_o_esperado(conn_demo):
    r = executar_consultas(conn_demo)
    assert len(r) == 7

    saldo_atual, abaixo, por_categoria, top_saidas, parados, mensal, extrato = r
    assert len(saldo_atual) == 6
    assert [(x["sku"], x["repor"]) for x in abaixo] == [("CB-100", 5), ("TC-020", 2)]
    assert {x["categoria"] for x in por_categoria} == {"Eletrônicos", "Periféricos", "Acessórios"}
    assert [x["sku"] for x in top_saidas][:2] == ["CB-100", "MS-010"]
    assert [x["sku"] for x in parados] == ["WC-030"]
    assert sum(x["entradas"] for x in mensal) == 267
    assert sum(x["saidas"] for x in mensal) == 149

    # o último saldo acumulado de cada produto é o saldo atual
    ultimos = {}
    for x in extrato:
        ultimos[x["sku"]] = x["saldo_apos"]
    assert ultimos["CB-100"] == 25 and ultimos["MS-010"] == 25
