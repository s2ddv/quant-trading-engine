# Protocolo F2 v1 — registrado antes da análise de resultados

**Estado:** pré-especificação de método, 05/11/2026. Nenhum retorno da F1 foi
usado para escolher os parâmetros abaixo. Os quatro ciclos atuais são
exclusivamente uma fixture sintética para validar causalidade e software.

## Hipótese e configuração congelada

Hipótese de pesquisa futura: uma carteira long-only de ações B3 selecionada
por momentum cross-sectional 12–2 pode superar um benchmark investível de
retorno total **líquida de custos**, fora da amostra. A hipótese nula é que
não há excesso líquido. Nenhuma delas é testável com os quatro ciclos atuais.

Para o ensaio sintético F2, usar o contrato da especificação: score
`C_(m−2)/C_(m−13)−1`, com 13 fechamentos mensais consecutivos e exclusão de
`m−1`; decisão após o último fechamento de `m−1`; execução apenas na próxima
abertura elegível. Ordenar por score decrescente e `instrument_id` ascendente,
selecionar até 10 ativos se houver pelo menos 5 elegíveis, peso-alvo
`min(1/N, 10%)` e excedente em caixa. Sem short, alavancagem ou juros.

Universo: instrumentos historicamente listados e não suspensos no instante da
decisão, com classificação datada, desde `m−13`. Exigir preço de fechamento
≥ R$ 2, 50 pregões válidos entre os últimos 63 e mediana de volume diário
≥ R$ 1 milhão no contrato de pesquisa real. A fixture F1 usa seu universo e
calendário sintéticos versionados; não se interpreta como universo B3.

Configuração sintética fixa: caixa inicial R$ 100.000; lote 1; teto por nome
10%; participação estimada 5%; reserva de abertura 1%; validade de 3 sessões;
marcação 6 minutos após fechamento; spread de meia banda 5 bps, slippage
5 bps e taxas agregadas 5 bps por lado; liquidação imediata simulada. Os
valores são hipóteses, sem alíquotas ou negociabilidade B3 observadas. Ensaios
de sensibilidade **separados** usarão custos 0/0/0 e 15/15/10 bps, sem
selecionar o melhor cenário. Comparar NAV apenas com agenda e quantidades de
fills idênticas quando se testar monotonicidade de custos.

## Controles, métricas e cortes

Controles sintéticos predefinidos: `cash` mantém R$ 100.000 sem juros;
`equal_weight` compra a cesta dos mesmos nomes elegíveis conhecidos em cada
decisão, com pesos iguais sujeitos ao teto, mesma primeira abertura, lotes,
capacidade, custos e regras de caixa da estratégia. Se nenhum nome for
elegível, ambos ficam em caixa. O controle deve registrar sua própria
identidade, ordens e NAV; não usar nomes escolhidos pelo ranking futuro.

Antes de comparar retornos, relatar número de decisões e sessões, cobertura
do universo, fills/ordens e rejeições, exposição e caixa, giro unilateral
`Σ|notional negociado|/(2×NAV médio)`, custos por rubrica em BRL e bps,
retorno acumulado líquido, drawdown máximo e duração. CAGR, volatilidade,
Sharpe, Sortino, tracking error, VaR/CVaR, intervalos de confiança e testes
estatísticos ficam sem estimativa quando a série não for suficiente ou houver
NAV incompleto. Não imputar retorno zero a uma marca ausente.

Os quatro ciclos atuais formam **um único bloco de desenvolvimento sintético**.
Não há corte temporal de validação ou teste final, nem walk-forward. Quando
houver histórico suficiente, fixar datas de desenvolvimento, validação e
teste final antes de ver o último bloco; embargar pelo menos 13 meses de
informação necessária ao score entre escolha de parâmetros e teste, e
registrar todas as tentativas. O teste final fica intocado até o congelamento
de código, dados, universo, custos e benchmark. Datas concretas exigem fonte
histórica auditada e serão uma nova versão deste protocolo.

## Critérios de interpretação

**Inválida:** hash/identidade ou replay divergente; dado de ordem disponível
após a decisão; ordem criada no/apos fill; fonte de barra/abertura/marca
ausente ou incompatível; marcação usa dado futuro; NAV incompleto tratado
como número; ausência de proveniência; mudança de parâmetro após inspecionar
resultado sem registrar nova tentativa. A auditoria F2 deve rejeitar a
fixture com vazamento temporal deliberado.

**Inconclusiva:** qualquer NAV incompleto para métrica dependente dele; série
curta para inferência, controle não comparável, universo histórico ou
benchmark sem disponibilidade verificável, custos/liquidação sem evidência
real, ou tentativa múltipla sem registro. A execução sintética pode ser válida
como teste de software e continuar inconclusiva quanto a desempenho.

Conclusão de desempenho B3 exige fonte, direitos, eventos, deslistados,
disponibilidade point-in-time e benchmark de retorno total auditados, além de
histórico suficiente e avaliação fora da amostra pré-especificada.
