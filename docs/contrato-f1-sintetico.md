# F1: primeiro corte sintético

Entrada: snapshot v1 imutável, instante de decisão posterior à publicação do último fechamento de janeiro de 2025 e anterior à abertura de fevereiro. A fixture cobre janeiro de 2024 a fevereiro de 2025, cinco instrumentos fictícios, 63 sessões recentes, split, dividendo, suspensão e barra ausente.

Universo: usar somente associações `listed` cujo intervalo inclua a sessão e cujo `available_at` não ultrapasse a decisão. Histórico exigido desde o último pregão de janeiro de 2024. Suspensos e registros tardios ficam fora. O identificador persistente, não o ticker, é a chave.

Sinal: para execução em fevereiro de 2025, exigir fechamentos de janeiro de 2024 a janeiro de 2025 sem lacunas mensais. O score 12–2 usa os 11 retornos de fevereiro a dezembro de 2024: valor econômico em dezembro de 2024 dividido pelo de janeiro de 2024 menos um. Janeiro de 2025 é excluído do score. Preços brutos são corrigidos causalmente por splits e dividendos conhecidos até a decisão. Exigir preço final de janeiro ≥ R$ 2 e, nas 63 sessões anteriores, 50 barras e mediana de volume financeiro ≥ R$ 1 milhão. Falha de qualquer requisito produz inelegibilidade explícita. Nenhuma consulta pode usar `available_at` posterior à decisão.

Exemplo esperado sem proventos: SYN-001 fecha janeiro de 2024 a R$ 10, dezembro de 2024 a R$ 12 e janeiro de 2025 a R$ 30. Score = 12/10 − 1 = 0,20; mudar o fechamento de janeiro para R$ 300 não altera o score. A abertura de fevereiro só pode entrar na execução posterior, nunca no score.

Saída da primeira etapa: membros datados e sinais com `decision_at`, `feature_end_session`, `input_max_available_at`, `score`, `eligible` e `reason`. Testes comparam o valor manual e verificam que alterar dados publicados depois da decisão preserva os sinais.
