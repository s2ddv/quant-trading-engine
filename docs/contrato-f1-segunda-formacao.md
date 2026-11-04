# F1 sintética: segunda decisão e venda — exemplo manual

Continuação de `synthetic_f1_v1.json`, com sessões sintéticas até 05/03/2025.
O snapshot `synthetic_f1_rebalance_v1.json` tem SHA-256 canônico
`2f6eee2938b1b3899f45d0e1893412fe12f209d78a3fb7e755472bfe6e5005df`.
A primeira decisão é 31/01 às 20:07 UTC e conserva os resultados do contrato
anterior. A segunda é 28/02 às 20:07 UTC, após barras publicadas às 20:05;
suas ordens só podem executar a partir da abertura de 03/03 às 13:00 UTC.
Não há ações corporativas após 05/02 nesta fixture. A liquidação é imediata.

Em 05/02: caixa R$ 50.774,01, recebíveis zero e posições SYN-001=658,
SYN-002=318, SYN-003=308, SYN-004=299, SYN-005=290. As respectivas bases
totais de aquisição são R$ 9.884,81; 9.872,79; 9.870,79; 9.881,81; 9.874,79.
Em 28/02, os fechamentos conhecidos são R$ 20,00; 31,00; 32,00; 33,00;
25,00. Logo o valor das posições é R$ 49.991,00 e o patrimônio é
R$ 100.765,01. Cada um dos cinco nomes elegíveis recebe alvo de 10%:
R$ 10.076,501. Com lote 1, a quantidade desejada é o piso de
`alvo/preço de fechamento`; a diferença contra a posição vira ordem.

| Ativo | Antes | Alvo | Ordem | Abertura 03/03 | Caixa líquido | Base após execução |
|---|---:|---:|---:|---:|---:|---:|
| SYN-001 | 658 | 503 | vender 155 | R$ 20,00 | +R$ 3.095,35 | R$ 7.556,32 |
| SYN-002 | 318 | 325 | comprar 7 | R$ 31,00 | −R$ 217,33 | R$ 10.090,12 |
| SYN-003 | 308 | 314 | comprar 6 | R$ 32,00 | −R$ 192,29 | R$ 10.063,08 |
| SYN-004 | 299 | 305 | comprar 6 | R$ 33,00 | −R$ 198,30 | R$ 10.080,11 |
| SYN-005 | 290 | 403 | comprar 113 | R$ 25,00 | −R$ 2.829,24 | R$ 12.704,03 |

Spread de 5 bps, slippage de 5 bps e taxa de 5 bps: compra a
`abertura × 1,001`, venda a `abertura × 0,999`. Em SYN-001, a venda tem
referência R$ 3.100,00, preço R$ 19,980 por ação, valor executado
R$ 3.096,90, spread R$ 1,55, slippage R$ 1,55 e taxa R$ 1,55; o crédito é
R$ 3.095,35. A base removida é
`round_cent(9.884,81 × 155 / 658) = 2.328,49`; o lucro realizado é
R$ 766,86. Para compra, spread e slippage já estão no preço: a taxa é o único
débito adicional. Todos os valores monetários são arredondados ao centavo por
`ROUND_HALF_UP`, com o resíduo de custo alocado a slippage.

Depois da venda, o caixa é R$ 53.869,36. Após as quatro compras, fica
R$ 50.432,20. As posições a fechamento de 03/03 valem R$ 50.323,00;
o NAV é **R$ 100.755,20**. A diferença de R$ 9,81 contra 28/02 corresponde
somente aos custos de negociação, pois os fechamentos de 03/03 repetem as
aberturas e não há fluxo externo. Vendas são processadas antes de compras na
mesma abertura; uma venda suspensa ou não executada não libera caixa.

O teste de lote usa múltiplos inteiros da configuração e não vende frações.
Capacidade de 5% do menor volume das últimas 50 barras disponíveis, suspensão
datada, execução parcial e falta de caixa são casos separados de regressão.
As ordens são congeladas na decisão: alterar aberturas e barras posteriores
não pode mudar seus alvos, embora possa mudar fills e NAV.
