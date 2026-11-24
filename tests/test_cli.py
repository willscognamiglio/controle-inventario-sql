import re

import pytest

from inventario.cli import main


@pytest.fixture
def banco(tmp_path):
    return str(tmp_path / "teste.db")


def rodar(banco, *args):
    return main(["--db", banco, *args])


def test_fluxo_completo(banco, capsys):
    assert rodar(banco, "cadastrar", "mn-1", "Monitor", "--categoria", "Eletrônicos",
                 "--custo", "650", "--minimo", "5") == 0
    assert rodar(banco, "entrada", "MN-1", "10", "--obs", "compra") == 0
    assert rodar(banco, "saida", "MN-1", "7") == 0
    capsys.readouterr()

    assert rodar(banco, "listar") == 0
    saida = capsys.readouterr().out
    assert "MN-1" in saida and "REPOR" in saida  # saldo 3 < mínimo 5

    assert rodar(banco, "listar", "--baixo") == 0
    assert "MN-1" in capsys.readouterr().out

    assert rodar(banco, "historico", "MN-1") == 0
    assert "compra" in capsys.readouterr().out


def test_saida_maior_que_o_saldo_retorna_erro(banco, capsys):
    rodar(banco, "cadastrar", "A", "Produto A")
    rodar(banco, "entrada", "A", "2")
    capsys.readouterr()

    assert rodar(banco, "saida", "A", "5") == 1
    assert "Estoque insuficiente" in capsys.readouterr().err


def test_produto_inexistente_retorna_erro(banco, capsys):
    assert rodar(banco, "entrada", "NADA", "1") == 1
    assert "não encontrado" in capsys.readouterr().err


def test_demo_e_resumo(banco, capsys):
    assert rodar(banco, "demo") == 0
    assert rodar(banco, "demo") == 1  # banco já populado
    capsys.readouterr()

    assert rodar(banco, "resumo") == 0
    saida = capsys.readouterr().out
    assert re.search(r"Produtos ativos:\s+6", saida)
    assert re.search(r"Abaixo do mínimo:\s+2", saida)
    assert "R$ 36.845,00" in saida
