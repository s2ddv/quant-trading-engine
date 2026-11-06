# Resumo descritivo F2 v1

`qtre.validation.summary.summarize_f1_run(diretorio)` lê uma execução F1
persistida e exige que o replay independente passe antes de calcular qualquer
número. A saída identifica a execução, conta decisões, ordens, fills e sessões,
lista sessões com NAV incompleto e soma spread, slippage e taxas em BRL.

O retorno acumulado, quando disponível, compara a primeira e a última marca
persistidas; não representa retorno desde o caixa inicial. Ele só é calculado
quando todas as marcas têm NAV completo.
Caso contrário, `cumulative_return` é `None` e `return_status` explica o motivo.
O resumo é apenas descritivo: quatro decisões fictícias não permitem inferência
estatística, validação fora da amostra ou conclusão sobre ações da B3. A
implementação não altera os artefatos da execução nem o protocolo registrado.

Na fixture de quatro decisões, a verificação local observou 16 ordens, 16 fills,
66 sessões, caixa final de R$ 50.712,22 e custos totais de R$ 90,78. A sessão
2025-02-04 tem NAV incompleto; por isso não há retorno acumulado. Esses valores
são um oráculo de regressão sintético, não uma estimativa de desempenho.
