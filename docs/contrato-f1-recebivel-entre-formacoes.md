# F1: recebível atravessando duas formações

Primeiro incremento do livro contínuo previsto no roadmap. Usar somente o
snapshot sintético `synthetic_f1_rebalance_v1.json`, mudando o pagamento de
`SYN-DIV` de 05/02 para 03/03. Ex-data e valor por ação não mudam. A posição
de 318 ações de SYN-002 em 04/02 gera R$ 159,00 a receber (`318 × 0,50`).

| Momento | Caixa | A receber | Tratamento |
|---|---:|---:|---|
| Fechamento de 05/02 | R$ 50.615,01 | R$ 159,00 | Dividendo ainda indisponível para compras |
| Formação de 28/02 | R$ 50.615,01 | R$ 159,00 | NAV de R$ 100.765,01 inclui o recebível |
| Abertura de 03/03 | +R$ 159,00 | −R$ 159,00 | Pagamento registrado antes das ordens |
| Fechamento de 03/03 | R$ 50.432,20 | R$ 0,00 | NAV de R$ 100.755,20 |

O pagamento altera caixa e recebível em igual magnitude, sem criar retorno.
Antes de 03/03, o valor a receber compõe o NAV, mas não financia ordens. O
replay deve reconstruir cada saldo a partir do dividendo e do pagamento
persistidos, sem executar novamente o motor. Uma ação corporativa cuja ex-data
ocorra entre as janelas de execução continua fora deste incremento: exige
processamento e marcação contínuos das sessões intermediárias.
