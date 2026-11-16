# Revisão de tarefas e contraprovas do QTRE — 16/11/2026

Base revisada: `main` em `f99069d495670723152191aea54c6df9d72a7f10`.
Esta revisão cobre os artefatos locais e as tarefas acessíveis no Codex;
não certifica conversas arquivadas nem estados posteriores. O motor continua
uma demonstração sintética, sem conclusão de desempenho B3. Nenhuma correção
de lógica financeira foi aplicada nesta entrega.

## Tarefas examinadas

F0/F1 (snapshot, sinais, execução, livro, ciclos e replay) e F2 (auditoria,
controles, sensibilidade e leitor comparativo) estão implementados no escopo
sintético. Os contratos de ML ainda são preparação, sem treino. A comparação
com motores externos produziu a [coletânea](../../coletanea-projetos-comparacao-qtre-2026-11-13.md)
e o [plano E1–E4](../../plano-integracao-lacunas-qtre-v1.md); os incrementos
continuam propostos, sem implementação.

A Task 2 B3 produziu, na branch local `codex/f3-b3-sample-audit`, os commits
`5c2b8c4` (seletor/testes) e `5c8a5fa` (parecer). O seletor escolhe casos
com metadados fictícios; não havia licença específica, catálogo real ou amostra
autorizada nos materiais examinados. O parecer permanece **não demonstrada**,
sem auditoria empírica C1–C9. A busca local não exclui documentos fora do
workspace. As tarefas de mapa de integração e explicação de progresso são
planejamento/comunicação, não funcionalidades adicionais.

## Achados reproduzidos

| ID | Prioridade | Código | Contraprova e consequência |
|---|---|---|---|
| A1 | Alta | `src/qtre/backtest/__init__.py:115`; `src/qtre/validation/__init__.py:82` | A primeira ordem de SYN-001 registra 50 chaves, mas seu sinal usa 74; faltam o fechamento-base de 31/01/2024 e cadastro histórico. Depois de mover a disponibilidade desse fechamento para após a decisão e refazer os hashes, a auditoria aceita cinco ordens (`VALID`), enquanto o motor recalculado cria zero. A auditoria verifica apenas as chaves declaradas e não detecta essa omissão. Isso não demonstra que a fixture original esteja vazada. |
| A2 | Média | `src/qtre/validation/cost_sensitivity.py:40` | A mesma fonte válida produz custo de 15.00347073017551978316200046 bps com precisão Decimal 28; com precisão externa 6 ou 50 o leitor rejeita o relatório (`final NAV reconciliation failed` ou `sensitivity run mismatch`). A API depende do contexto Decimal do chamador. |
| A3 | Média | `src/qtre/backtest/__init__.py:97-115` | Decisão em 03/02/2025 com formação explícita de 31/01/2025 gera referências de preços de 31/01 e 03/02. O motor aceita a execução, mas a auditoria a rejeita por divergência da formação. Não é dado futuro relativo à decisão; é uma inconsistência interna da formação declarada. |
| A4 | Média | `src/qtre/validation/ml_examples.py:62` | Duas revisões de fator com os mesmos instantes e valores 0,10/0,90 produzem escolhas opostas quando a ordem de entrada é invertida. Sem precedência autoritativa, a consulta deve rejeitar a ambiguidade ou documentar uma regra verificável. Nenhum modelo foi treinado. |

Para reproduzir as quatro condições, execute da raiz do repositório:

```sh
python3 docs/reviews/2026-11-16/reproduce_findings.py
```

No commit revisado, os quatro testes de **invariantes desejados** terminam em
três falhas e um erro. Esse resultado é a evidência dos problemas pendentes;
o script não altera arquivos de origem e usa diretórios temporários.

## Verificações e limites

`make check` em clone local isolado do commit revisado passou com lint,
formatação, validação estrutural e **158 testes**. `make core-test` passou com
**141 testes**; há sobreposição entre as suítes. A primeira tentativa de
`make check` em uma exportação sem `.git` produziu 15 falhas de infraestrutura:
os testes de experimento exigem `git rev-parse HEAD`. A repetição no clone do
mesmo commit passou; não se classificou a falha inicial como defeito do motor.

Um oráculo independente gerou **500 casos contábeis limitados** com seed
`20261116`: compra, venda, custos, centavos, lotes e caixa conferiram. Duas
leituras do relatório F2 tiveram bytes idênticos e preservaram os hashes dos
73 arquivos de origem. A conciliação manual final foi
`50712.22 + 0 + 50536.00 = 101248.22` BRL; custos de `90.78` BRL.
O retorno permanece indisponível pela sessão com `NAV_INCOMPLETO`; os quatro
pares posicionados de custo continuam não comparáveis por fills diferentes.
Entrada JSON inválida retornou código 2 e `INVALID_SOURCE`, sem relatório
parcial; `NaN` foi rejeitado no snapshot. Quatro testes específicos do seletor
B3 e suas verificações estáticas passaram em cópia do commit `5c8a5fa`.
Foram conferidos 79 links locais, sem destinos ausentes.

Os 162 testes completos informados pela Task 2 não foram repetidos nesta
revisão. Não houve execução de CI hospedada, outra versão de Python, download
B3, backtest de mercado, treino ML ou benchmark de velocidade. O relatório
[estado do projeto](../../status-projeto.md) ainda é um retrato de 06/11 e não
substitui estas observações. Fontes acadêmicas/mercado e direitos de dados
requerem verificação própria; os resultados sintéticos não têm inferência
econômica ou estatística.

## Ordem sugerida

Corrigir A1 e manter sua contraprova como regressão antes de ampliar a trilha
E1. Depois tratar A2–A4 em mudanças pequenas, com convenções explícitas e
revisão independente onde houver efeito causal/numérico. Reexecutar os quatro
testes e a suíte completa após correções. F3 depende primeiro de direitos
escritos, catálogo sem preços e amostra autorizada selecionada antes de
examinar valores.
