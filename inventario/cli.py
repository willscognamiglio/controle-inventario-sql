"""Interface de linha de comando do inventário."""

from __future__ import annotations

import argparse
import sys

from . import db


def _brl(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _imprimir_tabela(cabecalho: list[str], linhas: list[list]) -> None:
    if not linhas:
        print("(nenhum registro)")
        return
    larguras = [max(len(str(c)) for c in coluna) for coluna in zip(cabecalho, *linhas)]

    def formatar(linha):
        return "  ".join(str(c).ljust(w) for c, w in zip(linha, larguras)).rstrip()

    print(formatar(cabecalho))
    print("  ".join("-" * w for w in larguras))
    for linha in linhas:
        print(formatar(linha))


def _cmd_cadastrar(conn, args) -> None:
    db.cadastrar_produto(
        conn, args.sku, args.nome, args.categoria, args.custo, args.minimo
    )
    print(f"Produto {args.sku.strip().upper()} cadastrado.")


def _movimentar(tipo: str):
    def comando(conn, args) -> None:
        novo_saldo = db.registrar_movimentacao(conn, args.sku, tipo, args.quantidade, args.obs)
        print(f"{tipo.capitalize()} registrada. Saldo atual de {args.sku.upper()}: {novo_saldo}")

    return comando


def _cmd_listar(conn, args) -> None:
    linhas = [
        [
            r["sku"],
            r["nome"],
            r["categoria"] or "-",
            r["saldo"],
            r["estoque_minimo"],
            "REPOR" if r["saldo"] < r["estoque_minimo"] else "ok",
        ]
        for r in db.listar_estoque(conn, apenas_abaixo_minimo=args.baixo)
    ]
    _imprimir_tabela(["SKU", "Produto", "Categoria", "Saldo", "Mínimo", "Situação"], linhas)


def _cmd_historico(conn, args) -> None:
    linhas = [
        [r["data_hora"], r["tipo"], r["quantidade"], r["observacao"] or ""]
        for r in db.historico(conn, args.sku, args.limite)
    ]
    _imprimir_tabela(["Data/hora (UTC)", "Tipo", "Qtd", "Observação"], linhas)


def _cmd_resumo(conn, args) -> None:
    estoque = db.listar_estoque(conn)
    abaixo = [r for r in estoque if r["saldo"] < r["estoque_minimo"]]
    linhas = [
        ("Produtos ativos", len(estoque)),
        ("Unidades em estoque", sum(r["saldo"] for r in estoque)),
        ("Valor a preço de custo", _brl(db.valor_total_estoque(conn))),
        ("Abaixo do mínimo", len(abaixo)),
    ]
    for rotulo, valor in linhas:
        print(f"{rotulo + ':':<24}{valor}")


def _cmd_demo(conn, args) -> None:
    db.popular_exemplo(conn)
    print("Dados de exemplo carregados. Experimente: listar, listar --baixo, resumo.")


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventario", description="Controle de inventário com SQLite."
    )
    parser.add_argument(
        "--db", default="inventario.db", help="arquivo do banco (padrão: %(default)s)"
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("cadastrar", help="cadastra um produto")
    p.add_argument("sku")
    p.add_argument("nome")
    p.add_argument("--categoria")
    p.add_argument("--custo", type=float, default=0.0, help="preço de custo")
    p.add_argument("--minimo", type=int, default=0, help="estoque mínimo")
    p.set_defaults(func=_cmd_cadastrar)

    for nome, tipo in (("entrada", "ENTRADA"), ("saida", "SAIDA")):
        p = sub.add_parser(nome, help=f"registra uma {nome}")
        p.add_argument("sku")
        p.add_argument("quantidade", type=int)
        p.add_argument("--obs", help="observação")
        p.set_defaults(func=_movimentar(tipo))

    p = sub.add_parser("listar", help="lista o estoque atual")
    p.add_argument("--baixo", action="store_true", help="só produtos abaixo do mínimo")
    p.set_defaults(func=_cmd_listar)

    p = sub.add_parser("historico", help="movimentações de um produto")
    p.add_argument("sku")
    p.add_argument("--limite", type=int, default=20)
    p.set_defaults(func=_cmd_historico)

    p = sub.add_parser("resumo", help="visão geral do estoque")
    p.set_defaults(func=_cmd_resumo)

    p = sub.add_parser("demo", help="carrega dados fictícios em um banco vazio")
    p.set_defaults(func=_cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)
    conn = db.conectar(args.db)
    try:
        args.func(conn, args)
    except (db.InventarioError, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
