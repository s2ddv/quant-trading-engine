# F2 — sensibilidade sintética a custos v1

As nove execuções persistidas estão em
[`examples/f2_cost_sensitivity_v1`](../examples/f2_cost_sensitivity_v1).
`sensitivity.json` registra os `run_id`, a configuração por cenário, as
conciliações e as diferenças de cada ordem e fill. Cada subdiretório tem
manifesto, seis arquivos do envelope F1 e `audit.json`; o replay independente
e a auditoria retornam `VALID` nos nove casos. A geração reproduzível usa
`run_cost_sensitivity(snapshot, decision_ats=decisions, directory=destino)`
com a fixture estendida a quatro decisões por `tests/test_f2_controls.py`.

Os parâmetros 0/0/0, 5/5/5 e 15/15/10 bps são os três níveis registrados no
[protocolo](protocolo-pesquisa-f2-v1.md). Os demais parâmetros F1 são iguais.
As decisões usam apenas dados disponíveis até sua data; a primeira execução
elegível ocorre na próxima abertura, e cada marca usa o horário previsto.

| Estratégia | Spread/slippage/taxas (bps) | Ordens/fills | Spread (R$) | Slippage (R$) | Taxas (R$) | Total (R$) | Caixa final (R$) | Posições marcadas (R$) | NAV final (R$) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Momentum e `equal_weight` | 0/0/0 | 15/15 | 0,00 | 0,00 | 0,00 | 0,00 | 50.751,50 | 50.594,00 | 101.345,50 |
| Momentum e `equal_weight` | 5/5/5 | 16/16 | 30,27 | 30,24 | 30,27 | 90,78 | 50.712,22 | 50.536,00 | 101.248,22 |
| Momentum e `equal_weight` | 15/15/10 | 15/15 | 90,57 | 90,57 | 60,54 | 241,68 | 50.608,32 | 50.484,00 | 101.092,32 |
| `cash` | todos | 0/0 | 0,00 | 0,00 | 0,00 | 0,00 | 100.000,00 | 0,00 | 100.000,00 |

Em cada linha, caixa mais recebíveis (zero no fim) mais posições marcadas
iguala o NAV final. As posições e a base de custo por instrumento estão no
relatório. O custo total dividido pelo nocional de referência negociado é
0, aproximadamente 15,0035 e 40,0272 bps nos três cenários com operações;
para `cash`, a razão é indisponível porque não há nocional negociado.

Os quatro pares adjacentes de momentum e `equal_weight` têm diferenças nas
quantidades de ordens e fills. De 0 para 5/5/5, surge uma venda de uma ação
`SYN-001` no quarto ciclo (15 para 16 fills). De 5/5/5 para 15/15/10, essa
venda deixa de existir (16 para 15). Outras quantidades também mudam; a
agenda de sessões de NAV permanece igual. Assim, os NAVs finais acima são
valores observados de execuções distintas, **sem conclusão de monotonicidade**.
O teste adicional com participação de 0,01% mantém 56 fills não nulos com
agenda e quantidades idênticas entre custo zero e alto; nesse caso, custos
totais não diminuem e os 65 NAVs completos comparáveis não aumentam.

Cada estratégia com posições tem uma marca `NAV_INCOMPLETO` em 04/02/2025.
Ela não recebe valor imputado: retorno acumulado e outras métricas que
dependem da série completa permanecem indisponíveis. `cash` mantém 66 marcas
completas de R$ 100.000,00, sem operações e sem juros. Os quatro ciclos são
uma fixture de software, sem corte fora da amostra, inferência ou alegação de
desempenho B3.
