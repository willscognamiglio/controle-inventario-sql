-- Consultas úteis para análise do inventário.
-- Execute no banco criado pelo sistema, por exemplo:
--   sqlite3 inventario.db < sql/consultas.sql
-- Ou copie e rode cada consulta separadamente.

-- 1) Saldo atual de todos os produtos
SELECT sku, nome, categoria, saldo
FROM vw_saldo_estoque
ORDER BY nome;

-- 2) Produtos abaixo do estoque mínimo e quanto repor
SELECT sku, nome, saldo, estoque_minimo,
       estoque_minimo - saldo AS repor
FROM vw_saldo_estoque
WHERE saldo < estoque_minimo
ORDER BY repor DESC;

-- 3) Valor em estoque (a preço de custo) por categoria
SELECT COALESCE(categoria, 'Sem categoria') AS categoria,
       SUM(saldo)                           AS unidades,
       ROUND(SUM(saldo * preco_custo), 2)   AS valor_em_estoque
FROM vw_saldo_estoque
GROUP BY COALESCE(categoria, 'Sem categoria')
ORDER BY valor_em_estoque DESC;

-- 4) Top 5 produtos com mais saídas nos últimos 30 dias
SELECT p.sku, p.nome, SUM(m.quantidade) AS total_saidas
FROM movimentacoes m
JOIN produtos p ON p.id = m.produto_id
WHERE m.tipo = 'SAIDA'
  AND m.data_hora >= datetime('now', '-30 days')
GROUP BY p.id
ORDER BY total_saidas DESC
LIMIT 5;

-- 5) Produtos parados: sem nenhuma movimentação nos últimos 30 dias
SELECT p.sku, p.nome
FROM produtos p
WHERE p.ativo = 1
  AND NOT EXISTS (
      SELECT 1
      FROM movimentacoes m
      WHERE m.produto_id = p.id
        AND m.data_hora >= datetime('now', '-30 days')
  )
ORDER BY p.nome;

-- 6) Entradas x saídas por mês
SELECT strftime('%Y-%m', data_hora) AS mes,
       SUM(CASE WHEN tipo = 'ENTRADA' THEN quantidade ELSE 0 END) AS entradas,
       SUM(CASE WHEN tipo = 'SAIDA'   THEN quantidade ELSE 0 END) AS saidas
FROM movimentacoes
GROUP BY mes
ORDER BY mes;

-- 7) Extrato com saldo acumulado após cada movimentação (função de janela)
SELECT p.sku, m.data_hora, m.tipo, m.quantidade,
       SUM(CASE m.tipo WHEN 'ENTRADA' THEN m.quantidade
                       ELSE -m.quantidade END)
           OVER (PARTITION BY m.produto_id
                 ORDER BY m.data_hora, m.id) AS saldo_apos
FROM movimentacoes m
JOIN produtos p ON p.id = m.produto_id
ORDER BY p.sku, m.data_hora, m.id;
