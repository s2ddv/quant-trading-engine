# F1 sintética: deslistagem com e sem valor de saída

Partir da fixture da [terceira formação](contrato-f1-terceira-formacao.md).
Uma ação de deslistagem de SYN-001 é conhecida em 01/04 às 18:01 UTC, tem
ex-data em 02/04 e pagamento em 03/04. O valor **sintético e previamente
declarado** é R$ 26,00 por ação; a posição após 01/04 é de 405 ações e tem
base total de R$ 6.084,11. Um snapshot de esquema 2 distingue esse caso com
`exit_cash_per_share: 26` e `pay_session: "2025-04-03"`.

| Fechamento | Caixa | A receber | Outras posições | NAV |
|---|---:|---:|---:|---:|
| 01/04 | R$ 50.687,25 | R$ 0,00 | R$ 50.561,00, incluindo SYN-001 | R$ 101.248,25 |
| 02/04 | R$ 50.687,25 | R$ 10.530,00 | R$ 40.436,00, sem SYN-001 | R$ 101.653,25 |
| 03/04 | R$ 61.217,25 | R$ 0,00 | R$ 40.436,00 | R$ 101.653,25 |

Em 02/04, `405 × 26 = R$ 10.530,00` substitui a posição por um recebível.
A base de R$ 6.084,11 é removida integralmente e o resultado realizado é
R$ 4.445,89. O aumento de R$ 405,00 no NAV contra 01/04 representa a
diferença entre o último preço de R$ 25,00 e a saída conhecida de R$ 26,00;
o pagamento em 03/04 não cria retorno. Não se presume venda em bolsa nem
liquidação B3 real.

Sem `exit_cash_per_share`, a deslistagem não tem valor atribuível: a posição
e a base permanecem, o NAV fica `NAV_INCOMPLETO` e decisões futuras param
enquanto o valor não for resolvido. O replay deve rejeitar omissão ou
adulteração de ambos os tipos de evento.

Revisão de 05/11: um recebível de saída pode atravessar várias formações.
O livro conserva o valor reconhecido na ex-data até o pagamento, inclusive
quando a quantidade da posição já é zero. O teste com saída após o split
em 04/02 reconhece `658 × 26 = R$ 17.108,00`, mantém esse valor a receber
em fevereiro e março e paga uma única vez em 02/04. Posições zeradas não
aparecem nas marcas de preço. Uma cotação temporariamente ausente mantém o
NAV daquele dia incompleto, mas permite continuar se a formação seguinte
tiver avaliação completa. Uma saída ainda sem valor continua bloqueando a
nova decisão. Publicações tardias não são ignoradas na troca de janela.
