# Controle de Inventário com SQL

Sistema de controle de estoque em Python com banco de dados SQLite, usado por linha de comando. O foco do projeto é a modelagem do banco e as consultas SQL: o saldo é sempre calculado a partir das movimentações, e as regras de negócio importantes são garantidas pelo próprio banco.

## O que ele faz

- Cadastra produtos com categoria, preço de custo e estoque mínimo
- Registra entradas e saídas de estoque, com observação
- Calcula o saldo atual de cada produto
- Bloqueia saídas maiores que o saldo
- Aponta os produtos abaixo do estoque mínimo e quanto repor
- Mostra o histórico de movimentações de cada produto
- Traz 7 consultas SQL prontas de análise (`sql/consultas.sql`)

## Modelo de dados

```
categorias (id, nome)
     │ 1
     │
     │ N
produtos (id, sku, nome, categoria_id, preco_custo, estoque_minimo, ativo)
     │ 1
     │
     │ N
movimentacoes (id, produto_id, tipo, quantidade, observacao, data_hora)

vw_saldo_estoque  → view que soma as movimentações de cada produto
```

Pontos de destaque do `sql/schema.sql`:

- **Saldo calculado, nunca gravado:** não existe uma coluna "saldo" para ficar desatualizada. A view `vw_saldo_estoque` soma entradas e subtrai saídas.
- **Restrições `CHECK`:** quantidade sempre maior que zero, tipo só `ENTRADA` ou `SAIDA`, preço e mínimo nunca negativos.
- **Chaves estrangeiras** ativas, e **índice** em `(produto_id, data_hora)` para consultas de histórico.
- **Trigger `trg_bloqueia_saldo_negativo`:** recusa uma saída maior que o saldo direto no banco. Mesmo um `INSERT` feito fora da aplicação não consegue deixar o estoque negativo.

## Instalação

Requer Python 3.10 ou superior. O SQLite já vem com o Python, então não há dependências para rodar (o `pytest` é só para os testes).

```bash
git clone https://github.com/willscognamiglio/controle-inventario-sql.git
cd controle-inventario-sql
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python -m inventario demo                       # carrega dados fictícios
python -m inventario listar                     # estoque atual
python -m inventario listar --baixo             # só o que está abaixo do mínimo
python -m inventario cadastrar SKU "Nome" --categoria Periféricos --custo 49.90 --minimo 10
python -m inventario entrada SKU 50 --obs "Compra"
python -m inventario saida SKU 5 --obs "Venda"
python -m inventario historico SKU --limite 10
python -m inventario resumo
```

Use `--db arquivo.db` antes do comando para escolher o banco (padrão: `inventario.db`).

### Exemplo de execução

```
$ python -m inventario listar
SKU     Produto           Categoria    Saldo  Mínimo  Situação
------  ----------------  -----------  -----  ------  --------
CB-100  Cabo HDMI 2m      Acessórios   25     30      REPOR
MN-024  Monitor 24"       Eletrônicos  12     8       ok
MS-010  Mouse sem fio     Periféricos  25     20      ok
NB-001  Notebook 14"      Eletrônicos  8      5       ok
TC-020  Teclado mecânico  Periféricos  8      10      REPOR
WC-030  Webcam Full HD    Periféricos  40     10      ok

$ python -m inventario saida CB-100 40
Erro: Estoque insuficiente para CB-100: saldo atual 25, saída pedida 40

$ python -m inventario entrada CB-100 60 --obs Reposição
Entrada registrada. Saldo atual de CB-100: 85

$ python -m inventario resumo
Produtos ativos:        6
Unidades em estoque:    118
Valor a preço de custo: R$ 36.845,00
Abaixo do mínimo:       2
```

## Consultas SQL

O arquivo `sql/consultas.sql` reúne consultas de análise que podem ser executadas direto no banco:

1. Saldo atual por produto
2. Produtos abaixo do mínimo e quantidade a repor
3. Valor em estoque por categoria
4. Top 5 produtos com mais saídas nos últimos 30 dias
5. Produtos parados (sem movimentação em 30 dias), com `NOT EXISTS`
6. Entradas x saídas por mês
7. Extrato com saldo acumulado, usando função de janela (`SUM() OVER`)

```bash
sqlite3 inventario.db < sql/consultas.sql
```

## Testes

```bash
python -m pytest
```

Os testes cobrem o cadastro, o cálculo de saldo, o bloqueio de saída acima do saldo (pela aplicação e direto pela trigger), validações de entrada, a interface de linha de comando e a execução de todas as consultas SQL, conferindo os resultados esperados nos dados de exemplo.

## Estrutura

```
controle-inventario-sql/
├── inventario/
│   ├── db.py          # acesso ao banco e regras de negócio
│   ├── cli.py         # interface de linha de comando
│   └── __main__.py
├── sql/
│   ├── schema.sql     # tabelas, índice, trigger e view
│   ├── consultas.sql  # consultas de análise
│   └── dados_exemplo.sql
├── tests/
└── requirements.txt
```

## Migrar para MySQL

O projeto usa SQLite para ser fácil de rodar, mas a modelagem se traduz bem para MySQL. As principais adaptações seriam: `AUTOINCREMENT` → `AUTO_INCREMENT`, `datetime('now', '-30 days')` → `NOW() - INTERVAL 30 DAY`, `strftime` → `DATE_FORMAT`, e a trigger passaria a usar `SIGNAL SQLSTATE '45000'` no lugar de `RAISE(ABORT, ...)`.

## Ideias para evoluir

- Tabela de fornecedores e vínculo com as entradas
- Preço de venda e relatório de margem
- Exportação do estoque para CSV
- Versão em MySQL com a mesma modelagem

## Licença

MIT
