# F1: primeiro corte sintético

Entrada: snapshot v1 imutável, instante de decisão posterior à publicação do último fechamento de janeiro de 2025 e anterior à abertura de fevereiro. A fixture cobre janeiro de 2024 a fevereiro de 2025, cinco instrumentos fictícios, 63 sessões recentes, split, dividendo, suspensão e barra ausente.

Universo: usar somente associações `listed` cujo intervalo inclua a sessão e cujo `available_at` não ultrapasse a decisão. Histórico exigido desde o último pregão de janeiro de 2024. Suspensos e registros tardios ficam fora. O identificador persistente, não o ticker, é a chave.

Sinal: para execução em fevereiro de 2025, exigir fechamentos de janeiro de 2024 a janeiro de 2025 sem lacunas mensais. O score 12–2 usa os 11 retornos de fevereiro a dezembro de 2024: valor econômico em dezembro de 2024 dividido pelo de janeiro de 2024 menos um. Janeiro de 2025 é excluído do score. Preços brutos são corrigidos causalmente por splits e dividendos conhecidos até a decisão. Exigir preço final de janeiro ≥ R$ 2 e, nas 63 sessões anteriores, 50 barras e mediana de volume financeiro ≥ R$ 1 milhão. Falha de qualquer requisito produz inelegibilidade explícita. Nenhuma consulta pode usar `available_at` posterior à decisão.

Exemplo esperado sem proventos: SYN-001 fecha janeiro de 2024 a R$ 10, dezembro de 2024 a R$ 12 e janeiro de 2025 a R$ 30. Score = 12/10 − 1 = 0,20; mudar o fechamento de janeiro para R$ 300 não altera o score. A abertura de fevereiro só pode entrar na execução posterior, nunca no score.

Saída da primeira etapa: membros datados e sinais com `decision_at`, `feature_end_session`, `input_max_available_at`, `score`, `eligible` e `reason`. Testes comparam o valor manual e verificam que alterar dados publicados depois da decisão preserva os sinais.

## Carteira, execução e livro da fixture

Entrada: cinco sinais elegíveis em 31/01/2025 às 20:07 UTC, caixa inicial R$ 100.000, peso-alvo máximo de 10% por nome, lote 1, reserva de 1% para desvio da abertura mais 15 bps de custo, spread de 5 bps, slippage de 5 bps e taxa de 5 bps. Dimensionar com o fechamento de 31/01 já publicado. Capacidade por abertura = 5% do menor volume de ações das últimas 50 barras publicadas antes da decisão. Ordens vencem após três sessões sintéticas. Nenhuma abertura ou barra futura participa do dimensionamento.

Saída: ordens criadas na decisão, fills somente em aberturas posteriores, livro de caixa/posições/recebíveis, NAV por sessão e manifesto com hash do snapshot e configuração. Liquidação imediata é hipótese sintética. Spread e slippage estão no preço do fill e não são debitados novamente; a taxa sai do caixa. O snapshot inclui abertura suspensa de SYN-004 em 03/02, split 2:1 de SYN-001 e dividendo de R$ 0,50 por ação de SYN-002 em 04/02, pagamento em 05/02 e falta da barra de SYN-005 em 04/02.

Valores esperados antes da implementação: SYN-001 recebe ordem de 329 ações; fill em 03/02 a R$ 30,03, taxa R$ 4,94 e débito de R$ 9.884,81. Ao fim de 03/02, caixa R$ 60.498,92 e NAV R$ 99.942,92. Em 04/02, a quantidade de SYN-001 dobra para 658 e o dividendo gera R$ 159,00 de recebível. A barra ausente de SYN-005 produz `NAV_INCOMPLETO`, sem retorno imputado. Em 05/02, o recebível vira caixa e o NAV volta a ser completo em R$ 100.088,01.

Limites desta etapa: uma única formação, três sessões de execução, liquidação imediata fictícia, taxa agregada, sem classificação histórica de tipo de ação, sem venda/deslistagem, sem série diária completa no período de formação e sem replay independente. O manifesto em memória identifica snapshot, parâmetros e instante; uma versão de código/commit e artefatos persistidos serão necessários para o replay da F2. Os números são testes de mecânica, não retornos de mercado brasileiro.
