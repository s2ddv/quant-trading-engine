# Auditoria causal F2 — relatório v1

Depois de persistir uma execução F1, executar
PYTHONPATH=src python3 -m qtre.validation DIRETORIO_DA_EXECUCAO. A função
Python equivalente é qtre.validation.audit_f1_run(path). O comando retorna
0 para VALID, 1 para INVALID e 2 quando não consegue ler a entrada.

O arquivo audit.json é criado no mesmo diretório, sem alterar o envelope F1.
Contém audit_schema_version: 1, run_id, SHA-256 do manifesto, hashes
registrados dos seis arquivos F1, status, findings, nomes das verificações
e, se válido, contagens de decisões, ordens, fills, marcas e marcas incompletas.
JSON é canônico, com newline final. Uma nova auditoria só aceita o relatório
existente se seus bytes forem idênticos. O relatório vincula a conclusão à
identidade e aos bytes da execução, mas não é uma assinatura externa.

A auditoria primeiro exige replay F1 completo, que valida hashes, livro,
ações corporativas e NAV. Em seguida, confere que cada ordem pertence a uma
janela de decisão, usa chaves de entrada existentes e disponíveis até sua
criação, referencia o fechamento correto e precede seus fills. Confere a
proveniência e disponibilidade da abertura de cada fill e da barra de cada
marca. NAV_INCOMPLETO deve conservar nav_brl e positions_value_brl como
null; seu número é relatado e não entra em retornos. O relatório VALID
atesta essas condições na fixture sintética, não desempenho de investimento.

As duas fixtures de regressão são construídas em tests/test_f2_audit.py a
partir de examples/synthetic_f1_monthly_v1.json estendido deterministicamente
ao quarto ciclo pelo helper F1. A fixture válida é persistida e auditada
duas vezes para verificar bytes estáveis. Na fixture vazada, uma ordem da
primeira decisão recebe em input_keys uma barra de 30/04/2025;
orders.jsonl e seu hash no manifesto são recalculados. O replay do livro
ainda passa, mas a auditoria registra INVALID porque a barra só ficou
disponível após a decisão da ordem.

O protocolo de interpretação está em protocolo-pesquisa-f2-v1.md.
Quatro ciclos são insuficientes para walk-forward, inferência estatística ou
conclusão de desempenho B3.
