# F1 sintética: terceira decisão mensal

Extensão de `synthetic_f1_rebalance_v1.json` até 03/04/2025. A primeira e a
segunda decisões continuam em 31/01 e 28/02, às 20:07 UTC. A terceira ocorre
em 31/03 às 20:07 UTC, após a barra disponível às 20:05; nenhuma ordem nova
executa antes da abertura de 01/04 às 13:00 UTC. Não há eventos corporativos
adicionais. A liquidação sintética continua imediata.

Depois da segunda execução, em 05/03, o caixa é R$ 50.432,20 e as posições
são SYN-001=503, SYN-002=325, SYN-003=314, SYN-004=305 e SYN-005=403. As
bases de aquisição são, respectivamente, R$ 7.556,32; R$ 10.090,12;
R$ 10.063,08; R$ 10.080,11; R$ 12.704,03. Em 31/03, os fechamentos
conhecidos são R$ 25,00; R$ 31,00; R$ 32,00; R$ 33,00; R$ 20,00. Portanto,
as posições valem R$ 50.823,00 e o NAV é **R$ 101.255,20**. Com cinco nomes
e teto de 10%, cada alvo é R$ 10.125,52.

| Ativo | Antes | Alvo pelo fechamento | Ordem | Abertura 01/04 | Caixa líquido |
|---|---:|---:|---:|---:|---:|
| SYN-001 | 503 | 405 | vender 98 | R$ 25,00 | +R$ 2.446,33 |
| SYN-002 | 325 | 326 | comprar 1 | R$ 31,00 | −R$ 31,05 |
| SYN-003 | 314 | 316 | comprar 2 | R$ 32,00 | −R$ 64,09 |
| SYN-004 | 305 | 306 | comprar 1 | R$ 33,00 | −R$ 33,05 |
| SYN-005 | 403 | 506 | comprar 103 | R$ 20,00 | −R$ 2.063,09 |

Para SYN-001, o preço de venda é R$ 24,975, o notional é R$ 2.447,55, a
taxa é R$ 1,22 e o crédito é R$ 2.446,33. A base removida da venda parcial
é `round_cent(7.556,32 × 98 / 503) = 1.472,21`, deixando R$ 6.084,11 de
base. O lucro realizado é R$ 974,12. As compras debitam R$ 2.191,28 no
total. O caixa final é R$ 50.687,25; as posições valem R$ 50.561,00 e o NAV
em 01/04 é **R$ 101.248,25**. A queda de R$ 6,95 corresponde aos custos de
execução, pois as aberturas e fechamentos de 01/04 coincidem.

Invariantes: cada formação usa apenas dados conhecidos na sua decisão; vendas
precedem compras; ordens pendentes vencem na janela configurada; recebíveis
continuam separados do caixa; os IDs de ordens e fills são únicos por ciclo;
o replay reconstrói todos os saldos sem chamar o motor. Uma deslistagem sem
valor de saída conhecido conserva a posição e torna o NAV incompleto: não há
zeragem ou venda fictícia.
