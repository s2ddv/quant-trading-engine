# Controles sintéticos F2 v1

`run_f2_control(snapshot, decision_ats=decisions, control_id="cash")` e
`control_id="equal_weight"` executam livros independentes na mesma agenda
mensal da F1. O manifesto registra `control_id`, `model_id` próprio e `run_id`
derivado deles. `write_f1_run`, `replay_f1` e `audit_f1_run` aceitam esses
resultados sem alterar os esquemas F1 existentes. Os seis arquivos do envelope
continuam presentes, inclusive arquivos vazios de ordens, estados, fills e
livro para `cash`.

## Regras

- `cash` começa com R$ 100.000, não rende juros e não gera ordens, fills ou
  eventos de livro. Sua marcação conserva caixa e NAV em toda sessão prevista.
- `equal_weight` usa **todos** os nomes elegíveis conhecidos na decisão,
  identificados pelo filtro causal de elegibilidade. O score serve apenas ao
  filtro já existente; não determina a cesta nem a ordem dos nomes. Cada peso
  é `min(1/N, teto_por_nome)`, com o excedente em caixa. Sem elegíveis, o alvo
  é caixa.
- As ordens usam o fechamento conhecido após a formação e só podem executar
  na abertura seguinte. Lote, capacidade, reserva, custos, validade, vendas
  antes de compras, caixa, ações corporativas e marcação seguem o motor F1.
  O replay reconstrói o livro sem chamar o motor; a auditoria verifica
  disponibilidade temporal e pesos do controle.

## Conciliação da fixture de quatro decisões

Na configuração pré-registrada, as 66 sessões de `cash` têm NAV de
R$ 100.000,00; há zero ordens, fills e custos. `equal_weight` tem 16 ordens,
16 fills e 66 marcas, sendo uma `NAV_INCOMPLETO`. Ao fim, caixa de
R$ 50.712,22 mais posições de R$ 50.536,00 resulta em NAV de R$ 101.248,22.
Spread, slippage e taxas somam respectivamente R$ 30,27, R$ 30,24 e R$ 30,27.
Os cinco elegíveis da fixture recebem teto de 10%; por isso as operações
coincidem com as do momentum nesta amostra específica. Um teste separado com
quatro elegíveis confirma que o controle não herda o mínimo de cinco nomes do
ranking momentum.

Esta fixture é sintética. Seus quatro ciclos não sustentam inferência,
comparação fora da amostra ou afirmações de desempenho B3. A marca incompleta
impede calcular retorno acumulado para a série completa. A próxima entrega é
a sensibilidade aos cenários de custo pré-registrados no protocolo, com a
verificação de monotonicidade condicionada a agenda e quantidades de fills
idênticas.
