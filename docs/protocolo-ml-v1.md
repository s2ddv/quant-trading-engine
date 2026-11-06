# Protocolo ML v1 — preparação causal, sem treino

**Estado:** hipótese e contratos sintéticos, 06/11/2026. Complementa o [F2 v1](protocolo-pesquisa-f2-v1.md); não altera sua estratégia, seus custos ou seu embargo. Nenhum resultado da fixture escolheu fatores ou parâmetros.

## Pergunta e unidade

Hipótese incremental: um ranking supervisionado entre os mesmos instrumentos elegíveis produz ganho líquido fora da amostra frente ao momentum cross-sectional 12–2 congelado. Hipótese nula: não há ganho líquido reproduzível. A unidade de observação é `(instrument_id, decision_at)`; várias ações na mesma data são dependentes. `decision_at` é o instante após a formação mensal, antes de qualquer ordem; execução econômica continua na próxima abertura elegível. O contrato desta etapa apenas valida linhas e cortes, sem emitir ordens.

Fatores candidatos, sujeitos a disponibilidade verificável: score momentum 12–2; retorno de janela mais curta excluindo o mês recente; volatilidade histórica; liquidez/volume; indicador de dado faltante. Cada valor exige fonte, versão, `observed_at` e `available_at`. Apenas revisões publicadas até a decisão podem compor a linha; transformações e imputação futuras serão ajustadas somente no treino de cada corte. Elegibilidade, histórico de deslistados, revisões e eventos corporativos terão de ser auditados antes de usar B3. Os fatores além do momentum são hipóteses, não uma seleção otimizada.

Rótulo proposto: retorno total **simples, bruto e adimensional** de um instrumento entre a primeira abertura elegível após a decisão e a marca total ajustada ao fim do horizonte mensal seguinte, `(valor_final / valor_inicial) − 1`. O calendário, tratamento de proventos/deslistagem, disponibilidade da marca e horizonte em sessões serão congelados com os dados auditados. `horizon_end` marca o fim da informação necessária; `label.available_at` marca quando a última fonte foi publicada, nunca antes do fim. Rótulo incompleto fica ausente e não se torna retorno zero. O valor de rótulo sintético nos testes é fornecido pela fixture; o contrato ainda não calcula retornos B3.

## Baseline, cortes e orçamento

O baseline preditivo será o ranking fixo do score momentum 12–2; a comparação econômica principal será a carteira momentum F2 congelada. `cash` e `equal_weight` são controles secundários. Usar universo, capital, elegibilidade, ordens, lotes, execução, capacidade e custos equivalentes. Os cenários F2 0/0/0, 5/5/5 e 15/15/10 bps são análises de sensibilidade predefinidas, não opções a selecionar pelo retorno. NAV incompleto impede métricas correspondentes; monotonicidade de custos só é comparável com fills idênticos.

Planejar cortes cronológicos de treino, validação e teste final antes de qualquer treino. Cada ajuste usa apenas rótulos `available_at <= fit_at`. Purga-se do treino toda linha cujo `horizon_end >= validation_start`. `validation_end` é o corte de seleção deste v1: purga-se da validação todo rótulo cujo horizonte o alcança ou cuja publicação ocorre depois dele. O contrato exige pelo menos **13 meses de calendário** entre esse corte de seleção e `final_start`, preservando o embargo mínimo do F2. Transformações e seleção de fatores serão ajustadas em cada treino e congeladas para a validação. O teste final permanece reservado até congelar dados, código, modelo, custos, benchmark e tentativas.

Antes de treino, registrar datas concretas e tamanho de amostra, dados/versões/hashes, fonte, universo histórico, revisão de preços, calendário, configuração, seed e todos os ensaios, inclusive falhas. Orçamento proposto: no máximo **12 configurações** de modelo/fatores no desenvolvimento, contadas inclusive as rejeitadas; uma abertura do teste final após congelamento. Qualquer alteração posterior é uma nova versão com novo teste futuro. Os quatro ciclos sintéticos atuais não constituem cortes de desempenho.

Métricas preditivas propostas: correlação de postos de Spearman por decisão, cobertura dos rótulos e erro absoluto mediano do retorno, com tratamento determinístico de empates e ausências documentado antes da avaliação. Métricas econômicas: retorno acumulado líquido, drawdown, giro, custos por rubrica, exposição e caixa, com NAV alinhado e completo; incerteza por blocos temporais apenas se houver histórico suficiente. Critério de aceitação econômico a congelar com os dados auditados: ganho líquido consistente frente ao momentum nas janelas de validação e no teste final, após custos comparáveis, com tamanho de amostra e incerteza relatados. Boa previsão isolada não prova ganho econômico.

## Exemplo sintético calculado à mão

Um valor de fator `0,10` observado/publicado em 27/02 às 18:00 UTC está disponível na decisão de 28/02 às 18:00 UTC. Uma revisão de 02/03, mesmo que valha `0,90`, não altera a linha passada. Um preço inicial 100 e final 110 dão rótulo `(110/100)−1 = 0,10`. Se a decisão foi 28/02 e o horizonte termina 15/03, a linha é purgada de um treino cuja validação começa 01/03. Se o horizonte terminou antes de 01/03 mas a fonte só chegou 02/03, também é purgada do ajuste em 01/03. São oráculos de software, sem inferência preditiva.

## Pendências B3

Sem fonte e direitos auditados, universo histórico com deslistados, revisão temporal, ações corporativas, aberturas/marcas negociáveis, benchmark investível, custos/liquidação observados e série suficientemente longa, não há treino autorizado para conclusão econômica nem desempenho B3 demonstrado. Este protocolo não implementa o cálculo do rótulo, transformações, modelo, tuning ou integração ao backtest.
