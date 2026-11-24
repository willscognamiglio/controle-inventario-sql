-- Dados fictícios para experimentar o sistema (comando: demo).

INSERT INTO categorias (nome) VALUES ('Eletrônicos'), ('Periféricos'), ('Acessórios');

INSERT INTO produtos (sku, nome, categoria_id, preco_custo, estoque_minimo) VALUES
    ('NB-001', 'Notebook 14"',      (SELECT id FROM categorias WHERE nome = 'Eletrônicos'), 2800.00,  5),
    ('MN-024', 'Monitor 24"',       (SELECT id FROM categorias WHERE nome = 'Eletrônicos'),  650.00,  8),
    ('MS-010', 'Mouse sem fio',     (SELECT id FROM categorias WHERE nome = 'Periféricos'),   35.00, 20),
    ('TC-020', 'Teclado mecânico',  (SELECT id FROM categorias WHERE nome = 'Periféricos'),  190.00, 10),
    ('WC-030', 'Webcam Full HD',    (SELECT id FROM categorias WHERE nome = 'Periféricos'),   95.00, 10),
    ('CB-100', 'Cabo HDMI 2m',      (SELECT id FROM categorias WHERE nome = 'Acessórios'),    18.00, 30);

INSERT INTO movimentacoes (produto_id, tipo, quantidade, observacao, data_hora)
SELECT p.id, m.tipo, m.quantidade, m.observacao, datetime('now', m.deslocamento)
FROM (
    SELECT 'NB-001' AS sku, 'ENTRADA' AS tipo,  12 AS quantidade, 'Compra inicial' AS observacao, '-40 days' AS deslocamento
    UNION ALL SELECT 'NB-001', 'SAIDA',   4, 'Venda',          '-12 days'
    UNION ALL SELECT 'MN-024', 'ENTRADA', 15, 'Compra inicial', '-30 days'
    UNION ALL SELECT 'MN-024', 'SAIDA',   3, 'Venda',          '-9 days'
    UNION ALL SELECT 'MS-010', 'ENTRADA', 80, 'Compra inicial', '-35 days'
    UNION ALL SELECT 'MS-010', 'SAIDA',  30, 'Venda',          '-20 days'
    UNION ALL SELECT 'MS-010', 'SAIDA',  25, 'Venda',          '-5 days'
    UNION ALL SELECT 'TC-020', 'ENTRADA', 20, 'Compra inicial', '-25 days'
    UNION ALL SELECT 'TC-020', 'SAIDA',  12, 'Venda',          '-8 days'
    UNION ALL SELECT 'WC-030', 'ENTRADA', 40, 'Compra inicial', '-60 days'
    UNION ALL SELECT 'CB-100', 'ENTRADA', 100, 'Compra inicial', '-45 days'
    UNION ALL SELECT 'CB-100', 'SAIDA',  50, 'Venda',          '-15 days'
    UNION ALL SELECT 'CB-100', 'SAIDA',  25, 'Venda',          '-3 days'
) AS m
JOIN produtos p ON p.sku = m.sku
ORDER BY datetime('now', m.deslocamento);
