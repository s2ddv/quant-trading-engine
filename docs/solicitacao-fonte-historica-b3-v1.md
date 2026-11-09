# Solicitação de amostra histórica B3 — minuta para revisão

**Preparada em:** 09/11/2026, America/Sao_Paulo. **Destinatário:** equipe comercial/de dados da B3 **ou** distribuidor autorizado a ser identificado pelo usuário. **Estado:** minuta, não enviada; nenhuma contratação, autorização ou acesso foi obtido. Projeto: QTRE, pesquisa acadêmica/independente em ações brasileiras, inicialmente uma auditoria pequena de dados e direitos, sem negociação. Referências: [contrato C1–C9](contrato-auditoria-fonte-historica-v1.md), [auditoria inicial](auditoria-fonte-historica-b3-2026-11-09.md) e [protocolo congelado da amostra](protocolo-amostra-historica-b3-v1.md).

## Texto proposto para envio após revisão do usuário

**Assunto:** Consulta sobre licença e amostra histórica auditável de ações B3

Prezados(as),

Estou avaliando uma fonte de dados históricos de ações negociadas na B3 para pesquisa reproduzível. Antes de contratar ou receber dados, gostaria de identificar o produto, as condições aplicáveis a uma pessoa física ou, se necessário, a uma pessoa jurídica, e a possibilidade de uma pequena amostra autorizada. Não solicito nesta etapa acesso a dados licenciados fora dos canais e termos permitidos.

Peço resposta por escrito, com nome e versão do produto, titular dos direitos, contrato/anexos aplicáveis e indicação separada para cada ponto abaixo:

1. **Uso:** é permitido usar barras históricas, cadastro, eventos e índices em pesquisa interna, desenvolvimento de software, teste de qualidade e avaliação de estratégia? Existe distinção entre uso acadêmico, pessoal, profissional/comercial e publicação de estudo? Uma pessoa física pode contratar diretamente? Se não, qual canal autorizado atende esse perfil?
2. **Retenção e reprodução:** posso guardar localmente, pelo prazo necessário à auditoria, os arquivos originais e versões corrigidas, snapshots, esquemas, manifestos, contagens e hashes SHA-256? Há limite de prazo, ambiente, número de cópias ou obrigação de exclusão? Posso repetir a mesma consulta para verificar revisões? Se os dados não puderem ser retidos, qual mecanismo contratual permite replay verificável?
3. **Revisão independente:** um revisor externo, orientador ou colaborador pode acessar a mesma amostra e reproduzir os achados? Isso exige licença individual, acesso supervisionado ou anuência prévia? É permitido compartilhar apenas código, consultas, hashes, contagens e relatório de exceções sem linhas de dados?
4. **Publicação:** posso divulgar somente métricas agregadas de desempenho e qualidade, gráficos agregados, método, conclusões negativas, identificadores de produto/versão e hashes, sem redistribuir cotações ou eventos brutos? Há limiar de agregação, atraso, atribuição, revisão prévia ou autorização específica para métricas derivadas, índices, benchmarks ou estudo público? Favor distinguir permissão de uso interno de distribuição/redistribuição.
5. **Conteúdo e proveniência:** quais produtos entregam (a) OHLC e volumes brutos, abertura separada da barra diária final, (b) calendário e sessões especiais, (c) cadastro e histórico de instrumentos incluindo deslistados, símbolos antigos e suspensões, (d) eventos corporativos e retificações, (e) níveis/metodologia histórica de benchmark? Há `instrument_id` persistente e histórico de `valid_from`/`valid_to`? Quais campos têm primeira data/hora de publicação verificável (`available_at`), versão original, correções e fuso? Dados apenas atuais corrigidos devem ser identificados como tal.
6. **Amostra:** é possível fornecer, sob autorização expressa e sem obrigação de compra, o catálogo sem preços necessário para fixar até sete casos antes de examinar retornos e, depois, as janelas pequenas descritas no protocolo anexo? Se algum caso não existir, qual evidência de cobertura/indisponibilidade pode ser fornecida? Podemos confrontar dois eventos com comunicados oficiais datados?
7. **Preço e acesso:** qual preço da amostra, assinatura, taxa de instalação, mínimos, tributos, histórico retroativo, chaves, usuário adicional, suporte e eventual acesso de revisor? Qual formato, canal de entrega, frequência, prazo, SLA, janela disponível, requisitos técnicos e condições de cancelamento? Há tabelas e versões de preços/contratos por vigência? Favor enviar orçamento não vinculante e informar validade.
8. **Cadeia de direitos:** se a resposta vier de distribuidor, quais direitos vêm da B3 e quais são adicionais do distribuidor? Há autorização B3 necessária para minha finalidade, inclusive métricas derivadas e revisão externa? Qual documento prevalece em caso de conflito?

A resposta pode apontar cláusulas e anexos em vez de reproduzi-los. Só decidirei sobre aquisição após revisar direitos, custo e uma amostra autorizada. Agradeço também a identificação de um contato adequado caso este pedido pertença a outro canal.

Atenciosamente,

[Nome e vínculo a confirmar pelo usuário]

## Canais e condições publicados consultados

Consulta às páginas oficiais **em 09/11/2026, America/Sao_Paulo**. Isto é documentação comercial/publicada, **não licença concedida** nem confirmação de preço individual. O destinatário e a modalidade serão definidos após a revisão do usuário.

| Ref. | URL oficial | Condição/canal publicado e limite da inferência |
|---|---|---|
| S1 | [B3, Cotações históricas](https://b3.com.br/main.jsp?lumA=1&lumII=2C9E0371634B781701634B7C27111B5F&lumPageId=8A6A8C244DE7C289014DE80C873C130E) | Descreve série desde 1986 em moeda/forma da época, sem ajuste por proventos, com ZIP/layout; não estabelece direitos de pesquisa, versões PIT ou cobertura da amostra. |
| S2 | [B3, UP2DATA: serviço e arquivos](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/central-de-ajuda/servico-e-arquivos.htm) | Descreve canais de referência, eventos e arquivos e orienta contato sobre dados históricos não expostos no site; disponibilidade específica depende de proposta. |
| S3 | [B3, UP2DATA: contratação e acesso](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/contratacao-e-acesso/) | Publica acesso direto por contrato Master/anexos, canais/chaves e contatos; UP2DATA é anunciado para pessoas jurídicas. Não conclui elegibilidade deste pesquisador. |
| S4 | [B3, FAQ contratação e preços](https://b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/central-de-ajuda/contratacao-e-precos.htm) | Distingue uso interno e distribuição pelos anexos; criação de índices/benchmarks para distribuição externa requer consulta/licença específica. Preço e finalidade desta pesquisa seguem pendentes. |
| S5 | [B3, Termos de Uso](https://www.b3.com.br/main.jsp?doui_processActionId=setLocaleProcessAction&locale=pt_BR&lumA=1&lumII=8AE690F77A1A49BA017A5CE182412193&lumPageId=8AE690F77A1A49BA017A5CDEBBCF67BD) | Publica restrições a reprodução/publicação/distribuição comercial sem autorização escrita; não autoriza inferir que agregados ou acesso de terceiros estão liberados. |

## Decisões pendentes e passagem de parecer

| Decisão pendente | Evidência exigida para novo parecer |
|---|---|
| Escolher B3 direta, distribuidor ou nenhum | Resposta escrita identificando produto, titular, canal, elegibilidade pessoa física/jurídica, versão dos termos e custo total; escolher apenas depois de comparar cobertura e direitos. |
| Autorizar aquisição e custódia | Instrumento escrito que cubra C1: pesquisa, snapshots, hashes, prazo, revisor, agregados e restrições; sem permissão, não receber nem reter amostra licenciada. |
| Fixar casos e extrair amostra | Catálogo sem retornos, seleção determinística e manifesto congelado conforme protocolo; depois autorização da amostra e entrega com versão/hash fora do Git. |
| Emitir novo parecer técnico | Relatório por C1–C9 com evidências documentais **e observadas**, amostra de ativo/deslistado/eventos/correção quando disponíveis, falhas e ausências, prova de `available_at` e revisão independente dos casos; registrar versão/limites. |
| Avançar a F3/F4 | Apenas com parecer de fonte compatível com o uso pretendido e protocolo separado de universo integral, dados, benchmark, custos e cortes temporais; F4 exige ainda avaliação causal reservada. Esta minuta não autoriza código ou backtest. |

O parecer atual da [auditoria](auditoria-fonte-historica-b3-2026-11-09.md) continua **não demonstrada**. Um novo parecer pode ser `apta`, `apta com restrições` ou continuar `não demonstrada` conforme o contrato v1. Uma amostra que falhe ou seja indisponível não é corrigida por suposição de `available_at`, por troca retrospectiva de casos ou por uma página de marketing. Preços, condições contratuais e direitos solicitados acima estão pendentes, não foram estimados.
