# F1: sessões entre duas formações

Incremento sintético para o livro mensal contínuo. Partir de
`synthetic_f1_rebalance_v1.json` e alterar somente `SYN-DIV.pay_session` de
05/02 para 10/02. O direito de 318 ações de SYN-002 a R$ 0,50 por ação nasce
em 04/02 e vale R$ 159,00. A primeira janela termina em 05/02; a próxima
decisão ocorre em 28/02, depois do fechamento.

| Fechamento | Caixa | A receber | Posições a mercado | NAV |
|---|---:|---:|---:|---:|
| 05/02 | R$ 50.615,01 | R$ 159,00 | R$ 49.311,00 | R$ 100.085,01 |
| 10/02 | R$ 50.774,01 | R$ 0,00 | R$ 49.311,00 | R$ 100.085,01 |
| 28/02 | R$ 50.774,01 | R$ 0,00 | R$ 49.991,00 | R$ 100.765,01 |

Em 10/02, o pagamento troca recebível por caixa antes da abertura, sem
alterar o NAV. Cada sessão entre 05/02 e 28/02 recebe uma marca de fechamento.
Ações corporativas são aplicadas apenas depois de conhecidas e com sua data
efetiva; uma ação conhecida tarde para reconstruir a titularidade da ex-data
deve falhar explicitamente. Ordens da segunda decisão dependem somente do
livro e das barras disponíveis em 28/02. O replay reconstrói os saldos e
verifica a sequência de sessões sem chamar o motor.
