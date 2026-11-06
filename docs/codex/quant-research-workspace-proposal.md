# Quantitative Research Workspace — arquitetura e limites

Data: 2026-11-06. Estado: primeira etapa implementada; itens adicionais abaixo são
propostas. O uso e os comandos atuais estão no `README.md` do workspace independente.

## Ambiente verificado

| Componente | Caminho ou evidência | Estado |
| --- | --- | --- |
| QTRE | `/home/samuel-barbosa/Documentos/quant-trading-engine` | HEAD observado inicialmente `e86375f`; alterações locais anteriores preservadas |
| Simulação | `/home/samuel-barbosa/Documentos/quant-simulation-framework` | HEAD `ffbb186`; alteração anterior em `.idea/monte-carlo-gbm.iml` |
| Black–Litterman | `/home/samuel-barbosa/Documentos/black-litterman-optimizer` | HEAD `bf0be8c`; alterações anteriores em `cli.py`, `model.py`, `test_model.py` |
| Instruções globais | `/home/samuel-barbosa/.codex/AGENTS.md` | Seção Quant acrescentada; bytes anteriores preservados |
| Registro da integração | `/home/samuel-barbosa/.codex/quant-obsidian.json` | `vault_path` aponta para AI Quant; estado `connected` |
| Vault | `/home/samuel-barbosa/Documentos/Obsidian/AI Quant` | Renomeado do vault existente; notas anteriores preservadas |
| Workspace | `/home/samuel-barbosa/Documentos/quant-research-workspace` | Instalado e testado localmente |

Os repositórios de simulação e Black–Litterman usam a branch local
`codex/obsidian-quant-integration`; o QTRE avançou por trabalho paralelo para
`codex/quant-research-environment`. Alterações locais anteriores foram preservadas.
Instruções de integração foram acrescentadas aos três `AGENTS.md`.

O vault existente já continha `AGENTS.md`, `Quant/INDEX.md` e `Quant/quant_vault.py`.
Esses arquivos foram preservados; a nova estrutura fica em `Codex Quant/` e o índice
novo aponta para a pesquisa Quant anterior.

Python e as ferramentas `pdftotext`, `pdfinfo`, `pdftoppm` e `tesseract` estão disponíveis.
SQLite 3.51.2 passou em um teste em memória: criar tabela FTS5, inserir texto e recuperar
o registro pela palavra `causal`. Isso verifica disponibilidade, não qualidade de busca.
O Python padrão tem NumPy, mas não tem pypdf, scikit-learn ou sentence-transformers.
O runtime de documentos do Codex foi localizado, sem instalar dependências globais.

A busca limitada em Documentos, Documents e Downloads encontrou 26 PDFs, sem ler seu
conteúdo. Os nomes incluem documentos acadêmicos gerais e pessoais; não foi identificado
um acervo Quant curado. Nenhum PDF pessoal será importado automaticamente. A contagem
não equivale a inventário exaustivo do computador nem a classificação pelo conteúdo.

## Arquitetura proposta

```text
PDF escolhido + metadados de origem
              |
              v
Biblioteca imutável por SHA-256 + catálogo bibliográfico
              |
              v
Extração por página -> controle de qualidade -> trechos com proveniência
              |
              +--> SQLite FTS5/BM25 (baseline lexical)
              +--> embeddings locais versionados (busca semântica candidata)
                                 |
                       resultados com fonte e página
                                 |
               fichamento no Obsidian + proposta de experimento
                                 |
           compatibilidade + autorização de mudanças substanciais
                                 |
               execução no repositório correto e seus testes
                                 |
                 evidências -> registro no mesmo vault
```

A infraestrutura ficará em um workspace independente para evitar acoplar extração,
embeddings e dependências de documentos ao motor financeiro. Os projetos atuais serão
consumidores do contexto, mantendo seus contratos e comandos de validação.

```text
quant-research-workspace/
  AGENTS.md
  README.md
  pyproject.toml
  requirements.lock
  src/quant_workspace/       # biblioteca, extração, busca, notas e protocolos
  tests/                    # fixtures pequenas e regressões adversas
  schemas/                  # contratos versionados de documento, trecho e experimento
  config/                   # caminhos locais; sem credenciais
  library/
    inbox/                  # PDFs selecionados explicitamente
    objects/<sha256>.pdf    # originais preservados e deduplicados
    catalog/                # metadados e registros de procedência
  derived/<sha256>/<extractor-version>/
    pages.jsonl
    chunks.jsonl
    quality.json
  indexes/                  # derivados reconstruíveis, fora do Git
  research/protocols/       # hipóteses e planos antes de executar
  runs/<run-id>/            # manifestos, comandos, logs, artefatos e falhas
  evaluation/               # consultas rotuladas e comparação de recuperação
```

Os caminhos locais, PDFs, índices, caches e resultados volumosos não serão publicados
por padrão. Catálogo distingue livro, paper, preprint e documentação técnica; temas e
projetos são metadados, evitando múltiplas cópias do mesmo PDF. Mudança nos bytes produz
outro objeto e relação de revisão, nunca substituição silenciosa.

## Contratos de extração e proveniência

- Documento: `document_id`, SHA-256, título, autores, ano, edição/versão, tipo,
  DOI/arXiv/ISBN quando verificado, URL/origem local, data de aquisição, idioma,
  direitos de uso, projeto/temas, total de páginas e estado de revisão dos metadados.
- Campos desconhecidos ficam nulos com motivo. Título embutido no PDF é um candidato;
  título confirmado pela página inicial ou fonte bibliográfica tem origem própria.
  Não derivar autores, ano ou DOI de uma suposição sobre o nome do arquivo.
- Página: número físico de 1 a N, rótulo impresso se disponível e confirmado, texto,
  método de extração/OCR, versão da ferramenta e diagnósticos. Página física 1 não
  será confundida com página impressa 1 de um livro com prefácio numerado em romano.
- Trecho: ID estável derivado do documento, versão do pipeline, página e offsets;
  texto e hash. No MVP, trechos não atravessam páginas. Overlap é explícito e não
  duplica páginas ao avaliar recuperação.
- Extração mantém citações e bibliografia como texto com página. Referências citadas
  dentro do paper não serão marcadas como obras consultadas; resolução de DOI é uma
  etapa separada, com resultado verificável e estado de ambiguidade.
- PDFs sem texto suficiente recebem `needs_ocr` ou `needs_review`, não sucesso vazio.
  OCR será opcional e identificado. Equações, tabelas, múltiplas colunas e caracteres
  gregos exigem conferência visual antes de orientar uma implementação matemática.
- Registrar limites de tamanho/páginas, timeout e falhas; não executar scripts,
  anexos ou instruções presentes em documentos. Conteúdo é dado de pesquisa.

## Busca semântica e decisão sobre RAG

O baseline será FTS5/BM25 com títulos, texto e filtros de projeto, autor, tipo e data.
Busca lexical não será chamada de semântica. A segunda implementação será um retriever
de embeddings local, com modelo/revisão, tokenizer, dimensão, normalização, parâmetros
de segmentação e hash do corpus registrados. Modelo e dependências serão fixados após
checagem de memória, licença e compatibilidade. A execução será serial e em lotes.

Antes de comparar, congelar consultas representativas dos três projetos, em português
e inglês, com páginas relevantes revisadas por uma pessoa. Separar consultas de ajuste
das de avaliação e incluir perguntas sem resposta no acervo. Comparar os mesmos filtros,
corpus e top-k: BM25, semântica e, se necessário, combinação dos dois.

Medir Recall@5, MRR@10, precisão da referência de página, cobertura, latência e memória.
O resultado é condicionado à quantidade/qualidade das consultas e não prova melhoria
geral em pesquisa. Critério inicial proposto: ganho absoluto de pelo menos 0,05 em
Recall@5, sem queda de MRR@10, páginas corretas em todos os resultados auditados e
execução dentro do orçamento local. Esse limiar é uma decisão de engenharia a congelar
antes da avaliação, não uma conclusão acadêmica. Com corpus/consultas insuficientes,
relatar comparação inconclusiva e manter o baseline.

RAG acrescentaria síntese apoiada nos trechos recuperados. Ele só será promovido após
uma comparação separada entre leitura assistida pela busca e respostas geradas:
afirmações sustentadas, citações corretas, abstenção quando faltar evidência, tempo
e custo. Não confundir melhor recuperação com melhor resposta. Todas as respostas
devem permitir abrir o documento na página citada. Serviços remotos e envio do acervo
não fazem parte do desenho inicial.

## Organização do Obsidian e fluxo bidirecional

```text
Codex Quant/
  INDEX.md
  Literatura/<document-id>.md
  Metodos/<method-id>.md
  Projetos/<project-slug>/
    Projeto.md
    Modelos/
    Experimentos/
    Decisoes/
    Registros/
  Templates/
```

Cada fichamento separa: referência bibliográfica; problema; método/equações; hipóteses;
pressupostos; evidência apresentada pelos autores; limitações; interpretação local;
e experimentos propostos. Afirmações apontam para documento e página, e métodos ligam
literatura a modelos e experimentos. Um resultado próprio inclui link ao manifesto,
comando e artefatos. Uma hipótese inspirada em paper permanece hipótese até o teste.

O Codex lê notas relevantes e alterações feitas pelo usuário na próxima tarefa, verifica
o repositório e escreve registros ao concluir trabalho relevante. Não há sincronização
de duas cópias, daemon ou execução de código disparada por uma edição de nota.

Notas são criadas de forma exclusiva, em área dedicada. ID estável por entrega e busca
prévia evitam duplicatas. Uma mudança de resultado gera complemento ligado ao anterior;
nenhuma nota pessoal é sobrescrita ou removida. Um índice estável e backlinks permitem
navegação sem reescrever índices pessoais. Escrita só será confirmada após releitura.

O teste ponta a ponta deverá criar uma nota claramente marcada como exemplo, consultá-la
novamente pelo caminho no vault e verificar metadados e links. Confirmação por filesystem
e confirmação visual no aplicativo serão relatadas separadamente.

## Workflow de pesquisa e controles

1. Localizar literatura e ler páginas relevantes; distinguir citação de leitura efetiva.
2. Identificar método, equações, unidades, pressupostos, limitações e validade temporal.
3. Formular hipótese falsificável e baseline; avaliar compatibilidade com contratos
   existentes. Registrar proposta antes de olhar resultados.
4. Obter autorização para mudanças substanciais de lógica financeira; a autorização
   da infraestrutura documental não autoriza trocar estratégias ou parâmetros.
5. Congelar protocolo: dados/hash, universo, calendário, fontes, custos, janela de
   desenvolvimento/validação/teste final, métricas, incerteza e orçamento de tentativas.
6. Implementar somente o escopo autorizado, com oráculos manuais e testes adversos.
7. Executar testes/backtests compatíveis com os dados disponíveis; registrar inclusive
   falhas e tentativas desfavoráveis. Ausência de dados impede conclusão empírica.
8. Revisar evidências e registrar conclusão no Obsidian, explicitando limites e próximos
   passos. Não extrapolar resultados publicados ou sintéticos para lucratividade local.

| Risco | Controle e evidência exigida | Caso adverso de aceitação |
| --- | --- | --- |
| Look-ahead | Timestamps de observação/disponibilidade/decisão, ordem antes do fill, next-open | Dado disponível depois da decisão deve ser rejeitado |
| Survivorship | Universo histórico datado, ativos removidos/deslistados e ausência explícita | Universo composto apenas por sobreviventes deve bloquear alegação representativa |
| Leakage | Transformações ajustadas apenas no treino; rótulos purgados nos limites; dados revisados datados | Estatística ajustada no conjunto completo ou rótulo cruzando split deve falhar |
| Overfitting | Registro de todas as tentativas, orçamento de seleção, baseline e teste final reservado | Reutilização do holdout para escolher parâmetros deve invalidar seu status de teste final |
| Contabilidade | Custos, caixa, quantidades, lotes, NAV e regras de arredondamento conciliados | NAV incompleto nunca vira retorno zero |
| Citação falsa | Documento/hash, página e revisão visual de equações | Página inexistente ou referência não resolvida impede afirmação sustentada |

Os controles documentais verificarão completude e rastreabilidade; não certificam que
um dataset realmente inclui todos os deslistados. Essa conclusão exige evidência da
fonte e auditoria do conteúdo. Os controles executáveis existentes no QTRE continuam
autoritativos para sua implementação; adaptar outro projeto requer revisão própria.

## Etapas e critérios de aceite

1. Confirmar caminhos do workspace e vault, reconciliar qualquer integração anterior,
   testar leitura/escrita e configurar somente os acessos necessários.
2. Implementar biblioteca, catálogo, extração por página e busca lexical. Validar com
   PDF selecionado, duplicata, PDF sem texto, erro de extração e citação de página.
3. Implementar publicação segura de notas, templates e consulta bidirecional. Validar
   idempotência, colisões, preservação de notas e indisponibilidade do vault.
4. Implementar busca semântica e avaliação congelada. Decidir sobre RAG pela evidência.
5. Implementar validação de protocolos e registros de execução; integrar comandos dos
   projetos sem mudar seus modelos. Contraprovas devem detectar os riscos da tabela.
6. Executar testes da infraestrutura e verificações exigidas por qualquer repositório
   substancialmente alterado. Testar um fluxo literatura -> hipótese -> registro; um
   backtest real exige dados, autorização e contrato próprios.

A primeira etapa operacional foi instalada: acervo com hash e metadados declarados,
extração `pdftotext` por página, SQLite FTS5/BM25, busca LSA limitada e checagem
estrutural de protocolos. Três testes unitários passaram. Um smoke test em diretório
temporário extraiu três páginas e recuperou páginas nas duas buscas. Uma nota de exemplo
foi criada e relida no vault; repetição retornou `already-present`. `make check` no QTRE
passou com 140 testes, mas incluiu alterações locais paralelas do projeto.

Ainda faltam: acervo Quant curado, OCR automático, verificação bibliográfica automática,
avaliação de busca com consultas/páginas rotuladas, eventual RAG e validação de dados
históricos. Não foram executados backtests nesta etapa nem demonstrada lucratividade.

## Referências para o desenho

- Bailey, Borwein, López de Prado e Zhu. *The Probability of Backtest Overfitting*,
  versão revisada de fevereiro de 2015. [Manuscrito dos autores](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).
  Motiva controlar seleção entre tentativas; não comprova resultado de um projeto local.
- Lewis et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*.
  [arXiv:2005.11401](https://arxiv.org/abs/2005.11401). Evidência em tarefas de NLP;
  benefício neste workspace ainda precisa ser medido.
- [SQLite FTS5](https://www.sqlite.org/fts5.html): busca textual e ranking BM25.
- [Sentence Transformers — avaliação](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html):
  métricas de recuperação, incluindo Recall, MRR e NDCG.
- [scikit-learn — pitfalls/data leakage](https://scikit-learn.org/stable/common_pitfalls.html):
  separação treino/teste e ajuste de transformações no treino.

Essas fontes foram localizadas para orientar a arquitetura. Não foram importadas no
acervo nem fichadas integralmente; a implementação de um método requer leitura técnica
das páginas relevantes e referências adicionais específicas do modelo.
