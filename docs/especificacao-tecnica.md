# Quant Trading Research Engine (QTRE) — especificação técnica do MVP

**Estado:** proposta para implementação; nenhuma estratégia, fonte B3 ou resultado foi validado pelo QTRE. **Data da inspeção:** 29/10/2026. Convenções numéricas abaixo são escolhas de projeto, sujeitas às decisões pendentes.

## 1. Objetivo, fronteira e evidência consultada

**Pergunta de pesquisa:** uma carteira long-only de ações B3, selecionada por momentum cross-sectional 12–2 e negociada com latência e custos explícitos, supera um benchmark investível fora da amostra? A resposta deve mostrar retorno líquido, risco, giro e sensibilidade a dados e custos; nenhuma vantagem é presumida. Público: pesquisador quantitativo, desenvolvedor Python e revisor que precise refazer cada decisão de carteira.

O MVP entrega ingestão de snapshots imutáveis, calendário, universo datado, sinal 12–2, carteira, execução simulada, livro de caixa e posições, backtest cronológico, controles, métricas, manifesto e relatório. A primeira entrega executável usa **somente dados sintéticos controlados**. Uma fase posterior usa dados B3 apenas quando direitos, histórico de ativos (inclusive saídas) e disponibilidade temporal forem demonstrados. Ficam adiados: ordens reais, corretora, intraday, short, alavancagem, otimização Black–Litterman, múltiplas estratégias e previsão por ML. Pesquisa histórica não representa operação ao vivo; esta exigiria feed, monitoramento, reconciliação, tratamento de falhas e controles operacionais próprios.

### Inspeção somente leitura dos projetos relacionados

| Projeto | Versão local e estado Git observados | Estrutura, interfaces e dependências verificadas |
|---|---|---|
| `quant-simulation-framework` | `main`, HEAD `ffbb186926b6edd33d6f0a2f644d65d1b42f0fca`; alteração local em `.idea/monte-carlo-gbm.iml`, preservada. `origin` aponta para GitHub. | `AGENTS.md`, `README.md`, `pyproject.toml`, `main.py`, `src/{calibration,simulation,risk,validation}`, `tests/`. Python >=3.10; NumPy, pandas, SciPy, Matplotlib, yfinance; pytest opcional. `download_prices` baixa uma série ajustada por ticker; `validate_prices`, `GbmSimulator.generate_paths/generate_terminal`, `evaluate_out_of_sample`, `calibration_sensitivity`, `historical_snapshot`, `read_replay` e CLI são interfaces examinadas. |
| `black-litterman-optimizer` | `main`, HEAD `bf0be8cad97ee7ac22f095c14e39bcba353189a1`; alterações locais em `model.py`, `cli.py` e `tests/test_model.py`, preservadas. A descrição abaixo reflete a árvore de trabalho lida, não apenas o commit. | `AGENTS.md`, `README.md`, `pyproject.toml`, `src/black_litterman`, `examples/small.json`, `tests/test_model.py`. Python >=3.10 e NumPy >=1.24. API exportada: `View`, `InputData`, `Result`, `load_input`, `calculate`; CLI `bl-optimizer`. `calculate` retorna prior, posterior, pesos **sem restrições**, incertezas de opiniões e avisos. |

O acesso à API do GitHub falhou na inspeção; somente os checkouts locais sustentam as afirmações acima. Não foram executados testes nesses projetos nem alterados seus arquivos. O restante deste documento é **proposta para o QTRE**, salvo quando a matriz de integração indicar uma capacidade diretamente observada.

## 2. Arquitetura e fluxo

O motor processa eventos ordenados por instante UTC e sequência estável: publicação de dado, ação corporativa, fechamento observado, geração de sinal, emissão de ordem, abertura/negociação, fill, marcação e relatório. Toda consulta recebe um `as_of` e só devolve informação disponível até esse instante. O construtor converte metas em ordens usando caixa e restrições; o backtester mantém o livro, sem delegar contabilidade à estratégia.

```text
quant-trading-engine/
├── pyproject.toml
├── README.md
├── docs/especificacao-tecnica.md
├── configs/                 # parâmetros versionados, esquemas e perfis de cenário
├── src/qtre/
│   ├── domain/              # tipos imutáveis, unidades, invariantes e identificadores
│   ├── data/                # ingestão, validação, snapshots, proveniência e as_of
│   ├── calendar/            # sessões, fechamento e fuso da bolsa
│   ├── universe/            # associação datada de instrumentos e elegibilidade
│   ├── signals/             # 12–2; sem acesso direto ao futuro nem à execução
│   ├── portfolio/           # pesos-alvo, limites, lotes e dimensionamento
│   ├── execution/           # fila, elegibilidade de sessão, fills e custos
│   ├── accounting/          # caixa, posições, ações corporativas e NAV
│   ├── backtest/            # loop de eventos e checkpoints
│   ├── validation/          # walk-forward, auditoria causal e controles
│   ├── analytics/           # retorno, risco, giro, exposição e custos
│   └── reporting/           # manifesto, tabelas legíveis por máquina e relatório
├── tests/                   # fixtures sintéticas, unitários, integração, propriedades
└── examples/                # entrada sintética e saída esperada mínima
```

Fluxo: `data + calendar → universe → signals → portfolio → execution → accounting/backtest → validation + analytics → reporting`. `domain` fornece contratos comuns. Pacotes não importam `reporting` para calcular decisões; relatórios apenas leem resultados. Adaptadores de fornecedor ficam atrás de `data` e não definem a lógica da estratégia.

## 3. Dados, contratos e causalidade

**Identidade:** `instrument_id` é chave interna persistente do instrumento negociável, distinta de ticker mutável; tabela de símbolos possui `valid_from`, `valid_to`, `observed_at`, `available_at` e identificador da fonte. Um evento que muda ticker preserva a identidade quando for o mesmo instrumento; fusão/cisão que cria instrumento novo exige vínculo explícito e regra de conversão. Nunca inferir identidade apenas do ticker.

**Tempo e unidade:** instantes armazenados em UTC com fuso explícito; sessões e regras de negociação no fuso `America/Sao_Paulo`, usando calendário versionado. Valores monetários em BRL no MVP, preços por ação, quantidade inteira de ações, taxas em fração decimal e pontos base identificados. Frequência da estratégia é mensal; preço, volume, eventos e contabilidade são diários por sessão. Os retornos de carteira são simples totais por sessão, compostos geometricamente; risco anualizado declara número de sessões usado. Não interpolar sessões inexistentes.

| Registro imutável | Campos mínimos (além de `source_id`, `source_version`, `snapshot_id`) | Invariante / tratamento |
|---|---|---|
| `PriceBar` | `instrument_id`, `session`, `open`, `high`, `low`, `close`, `volume_shares`, `volume_brl`, `currency`, `observed_at`, `available_at`, `adjustment_basis` | OHLC bruto positivo e finito; suspensão = ausência/estado, não preço carregado como negociável. Valor ajustado, se fornecido, é série analítica separada com versão da metodologia. |
| `OpenEvent` | `instrument_id`, `session`, `open_price`, `observed_at`, `available_at`, `currency`, `tradable` | Evento separado da barra diária; só o preço de abertura e estado então conhecidos podem alimentar fill na abertura. A barra OHLC completa chega após o fechamento. |
| `CorporateAction` | `action_id`, `instrument_id`, `kind`, `announced_at`, `available_at`, `ex_session`, `record_session?`, `pay_session?`, `ratio?`, `cash_per_share?`, `successor_id?` | Splits alteram quantidade e base de custo; dividendos creditados em `pay_session` se direito adquirido em `ex_session`. Revisões mantêm histórico. |
| `UniverseMembership` | `instrument_id`, `valid_from`, `valid_to?`, `observed_at`, `available_at`, `status`, `reason` | Intervalos sem sobreposição; entrada/saída somente com informação disponível ao corte. Inclui instrumentos deslistados quando historicamente válidos. |
| `Signal` | `instrument_id`, `decision_at`, `feature_end_session`, `input_max_available_at`, `score`, `eligible`, `reason` | `input_max_available_at <= decision_at`; score finito ou inelegível justificado. |
| `Target/Order` | `order_id`, `instrument_id`, `created_at`, `earliest_execution_at`, `side`, `quantity`, `target_weight`, `expiry_session` | Quantidade em lote inteiro; `earliest_execution_at > decision_at`; venda/compra sem short no MVP. |
| `Fill` | `fill_id`, `order_id`, `executed_at`, `session`, `quantity`, `price`, `spread_cost`, `slippage_cost`, `fees`, `model_id` | Quantidade não supera saldo da ordem; preço e custos não negativos; preço não deriva do mesmo fechamento que gerou a ordem. |
| `Position/CashLedger` | `instrument_id`, `session`, `quantity`, `cost_basis`, `cash_brl`, `receivable_brl`, `event_id` | Livro de partidas verificáveis: compras reduzem caixa, vendas aumentam, proventos seguem direito e pagamento. |
| `Result` | `run_id`, `session`, `nav_brl`, `cash_brl`, `positions_value_brl`, `gross_return`, `net_return`, `benchmark_return`, `status` | `NAV = caixa + recebíveis + posições` pela convenção escolhida; cada valor referencia preço ou evento de origem. |

Separar `observed_at` (momento a que o fato se refere), `available_at` (primeiro instante verificável em que poderia ser conhecido) e `ingested_at` (captura local). A consulta causal filtra `available_at <= as_of`, usa a versão então disponível e registra as chaves usadas em cada sinal. Revisão posterior não reescreve decisões anteriores. Se o fornecedor só dá dados atuais corrigidos e não tem histórico de publicação, rotular `availability_assumed` e limitar alegações.

Preços brutos e ações corporativas são a base de execução e contabilidade. Um fator ajustado **point-in-time** pode apoiar ranking, desde que sua construção use apenas eventos então conhecidos e não injete distribuições futuras. A convenção de sinal no MVP é retorno total realizado até a data final da janela, derivado de preços brutos e ações corporativas com direito conhecido até a decisão. Evitar somar dividendos outra vez ao NAV. Se não houver eventos confiáveis, a fase sintética testa a regra; dados reais ficam como análise exploratória de preço, claramente rotulada, sem chamar o retorno de total.

Política de ausência: distinguir `não negociou`, `suspenso`, `dado ausente` e `fora do universo`. Não fazer `forward fill` para sinal, volume, fill ou preço de execução. Barra inválida/duplicada bloqueia a execução com erro auditável. Falta de observação em qualquer ponto requerido da janela torna o ativo inelegível; falta de cotação para marcar uma posição gera status `NAV_INCOMPLETO`, interrompe métricas de retorno e exige política de avaliação declarada, sem criar retorno zero silencioso. Eventos corporativos sem termos completos bloqueiam avaliação real daquele instrumento.

**Survivorship bias:** universo deve ser reconstruído por `valid_from/valid_to` e disponibilidade histórica, contendo saídas, suspensões e mudanças de símbolo. Uma lista atual de tickers é somente coorte sobrevivente. **Look-ahead:** além do filtro de disponibilidade, o backtest impede execução no fechamento usado para formar sinal, fixa ordem temporal e guarda o `input_max_available_at`. Sem fonte comprovada de universo histórico e timestamps point-in-time, o primeiro backtest real será rotulado `coorte contemporânea / disponibilidade presumida`, sem alegação de ausência desses vieses; a comparação principal de pesquisa fica condicionada à aquisição e auditoria dos dados.

## 4. Estratégia inicial: momentum cross-sectional 12–2

Defina `m` como o mês de **execução** e `C_j(i)` como o fechamento total econômico do instrumento `i` no último pregão do mês `j`, calculado apenas com informação conhecida até o fechamento de `m−1`. O score é

`M_i,m = [produto de (1 + R_i,j), j = m−12,…,m−2] − 1 = C_(m−2)(i) / C_(m−13)(i) − 1`,

onde `R_i,j` é o retorno total do mês `j` já realizado; **11 retornos mensais** são usados, com o mês `m−1` excluído. A notação `C` inclui reinvestimento teórico de proventos somente para ranking, nunca quantidade fictícia na carteira. Exigir 13 fechamentos mensais consecutivos de `m−13` a `m−1`; o último confirma histórico e elegibilidade, mas não entra no score. Sem preço/evento completo, não há score.

No fechamento do último pregão de `m−1`, selecionar apenas ações ordinárias/preferenciais elegíveis por classificação datada, listadas e não suspensas, com histórico completo. Parâmetros iniciais **de pesquisa, não regras da B3**: mediana de `volume_brl` diário nos 63 pregões conhecidos ≥ R$ 1 milhão, pelo menos 50 pregões válidos nesse intervalo, preço de fechamento ≥ R$ 2, e presença no universo desde `m−13`. A decisão real sobre limites depende da cobertura dos dados. Ordenar score decrescente, desempate por `instrument_id` ascendente; selecionar até 10 nomes, desde que pelo menos 5 elegíveis, caso contrário ficar 100% em caixa e registrar motivo. Peso-alvo igual `min(1/N, 10%)` por ativo, excedente em caixa; sem alavancagem e sem short. Rebalancear mensalmente. Liquidez de execução e limite de participação ainda podem reduzir a posição efetiva.

**Linha causal obrigatória:** fechamento de `m−1` observado → após `available_at` de todas as barras/eventos necessários, sinal e ordens registrados → primeira execução permitida na **abertura do primeiro pregão de `m`**, somente se a ordem já existia antes dessa abertura; se dado tardio, passa ao próximo pregão. Não preencher ao preço do fechamento de formação. Os preços da abertura são usados somente pelo modelo de execução, jamais por score ou dimensionamento anterior. Benchmark candidato: Ibovespa de retorno total, com metodologia e série datadas verificadas; até lá, controles sintéticos `cash`, buy-and-hold de cesta fixa e pesos iguais no mesmo universo causal. Benchmark não é carteira atual do usuário.

## 5. Carteira, execução e custos

Caixa inicial em BRL configurado; não há empréstimo nem juros no caso base. Vender antes de comprar na mesma sessão; compras só usam caixa liquidado disponível segundo convenção de liquidação configurada, mantendo recebíveis separados. Para evitar dependência de regra externa ainda não verificada, o protótipo sintético usa liquidação imediata **explicitamente simulada**; a integração real deve selecionar prazo histórico correto e contabilizar recebíveis. Arredondar quantidade para baixo ao múltiplo do lote configurado por instrumento e sessão; frações ficam em caixa. Preço de referência para tamanho é último fechamento disponível, com reserva para custos e desvio de abertura. Se a abertura exceder caixa, reduzir ou rejeitar compra, nunca gerar saldo negativo.

Limites iniciais configuráveis: peso por nome ≤10% no alvo, participação em volume da sessão ≤5%, long-only, posição inteira, sem concentração por setor até haver classificação histórica confiável. Ordens não executadas podem expirar após 3 pregões; fills parciais são registrados. Suspensão impede novas compras e fills; posição permanece com avaliação incompleta se não houver marca confiável. Deslistagem exige evento e preço/valor de saída documentado; não zerar nem liquidar artificialmente. Resultados reais com saída não resolvida ficam incompletos.

Modelo de fill: na primeira abertura elegível, compra a `open × (1 + half_spread + slippage)` e venda a `open × (1 − half_spread − slippage)`, mais taxas monetárias; limitar por capacidade estimada antes da abertura e lote. Somente `OpenEvent` alimenta o fill naquele instante; a barra diária completa, publicada após o fechamento, não pode ser consultada na abertura. O uso do **volume diário completo** para limitar fill é uma hipótese retrospectiva: no caso base sintético, usar limite previamente estimado por volume histórico ou um livro de disponibilidade publicado antes do fill; em sensibilidade, aplicar limite pós-sessão apenas como cenário explicitamente não causal. Spread, slippage, impacto, corretagem, emolumentos, tributos e outras tarifas são campos separados com unidade, vigência e fonte. O MVP não afirma alíquotas atuais; valores de exemplo são hipóteses. Incluir cenário zero, base e adverso (por exemplo, 0/10/30 bps por lado de spread+slippage e 0/5/10 bps por lado de taxas agregadas), além de variar participação e atraso em sessões. Relatar custos realizados em BRL e bps do notional, e sensibilidade do retorno líquido.

## 6. Backtest, validação e métricas

Usar motor orientado a eventos diário: a ordem temporal, ações corporativas, execuções parciais e caixa são centrais para esta estratégia. Vetorização pode acelerar analytics, mas não substituir o livro de eventos. `event_id` e sequência tornam replay determinístico. Em cada sessão: aplicar direitos/proventos devidos, receber `OpenEvent`, executar ordens já elegíveis, atualizar livro, receber a barra completa após o fechamento, marcar NAV e, quando for a data de formação, gerar sinal e ordens para sessão futura. Conservar identidade `NAV = cash + receivables + Σ(quantity × mark_price)`; retorno líquido por sessão `NAV_t/NAV_(t−1)−1` após fluxos externos ajustados. Retorno bruto é recomputação sem custos, sob as mesmas quantidades e agenda de fills, com a convenção registrada. Capital externo tem evento próprio e neutralização em retorno por unidade de cota.

Walk-forward: divisões cronológicas predefinidas, por exemplo desenvolvimento/seleção de parâmetros, validação e teste final intocado; cortes e período de embargo suficientes para janelas de 13 meses definidos antes de avaliar. Dentro da seleção, recalcular universo, liquidez, ranking e parâmetros apenas com dados disponíveis até cada decisão. Variar poucos parâmetros declarados (top N, liquidez, custos) na etapa de seleção; congelar configuração e hash antes do teste final. Não interpretar múltiplas tentativas como uma única hipótese. Comparar estratégia líquida a benchmark documentado e controles de caixa, buy-and-hold e pesos iguais no mesmo universo elegível. Quando houver série real, alinhar calendário, proventos e período comum.

Métricas: retorno acumulado e CAGR, excesso e tracking error frente ao benchmark, volatilidade anualizada, drawdown máximo e duração, Sharpe/Sortino com taxa livre de risco e convenção explícitas, VaR/CVaR históricos como descrição (não previsão), retorno por subperíodo e dispersão entre janelas; giro unilateral `Σ|compras+vendas|/(2×NAV médio)` ou definição alternativa fixada no manifesto; exposição bruta/líquida, pesos e caixa, concentração, cobertura de universo, fill rate, ordens rejeitadas, custos por categoria e participação do custo no retorno. Mostrar número de observações e `NAV_INCOMPLETO`; não calcular métricas que exigem preços faltantes. Sem estimar significância estatística sem procedimento pré-especificado para dependência temporal e múltiplas buscas.

## 7. Reprodutibilidade e saídas

Cada execução recebe `run_id` derivado de configuração canônica, código/commit, hashes dos snapshots e versão do esquema. Guardar configuração integral, versão Python e dependências, calendário, regras de lotes, definições de custo/retorno, timezone, universo, eventos, barras, mapping de símbolos, cortes walk-forward e flags de qualidade. `seed` somente para componentes estocásticos; modelo base de fill é determinístico. Saídas: `manifest.json`, `events.jsonl`, `signals.parquet` ou JSONL, `orders.jsonl`, `fills.jsonl`, `ledger.jsonl`, `nav.csv`, `metrics.json` e relatório Markdown/HTML com limites e proveniência. O formato exato terá esquema versionado; todo registro carrega `run_id` e chaves de origem. Replay offline deve reconstruir NAV e hashes e comparar resultados byte a byte quando ambiente e serialização forem fixos, ou numericamente com tolerância declarada.

Um ID de consulta ou URL de fornecedor não congela dados. Se a licença impedir armazenar o snapshot, registrar hash, intervalo, versão, método e data de extração, mas declarar que terceiros **não conseguem reproduzir exatamente** sem acesso ao mesmo conteúdo. Revisões do fornecedor, ajustes retroativos e mudança de calendário podem alterar resultados; um novo snapshot vira outro `run_id`.

## 8. Integração sem duplicação

| Capacidade existente verificada | Uso possível no QTRE | Adaptação necessária | Decisão |
|---|---|---|---|
| `quant-simulation-framework`: `GbmSimulator`, terminal em lotes | Cenários auxiliares de preço/risco sob hipóteses GBM | Adaptador isolado; frequência/unidades e proveniência; jamais gerar fills históricos | Adiar até depois do corte vertical |
| `validate_prices` e estimação em uma série | Ideias para invariantes de preço e diagnósticos | QTRE precisa de barras multiativo, timestamps de disponibilidade, eventos e universo | Reimplementar contrato próprio, sem dependência |
| `evaluate_out_of_sample` fixed/rolling/expanding | Referência de separação cronológica de calibração GBM | Sua saída são previsões de **um ativo**, não decisões de carteira ou custos | Consultar conceito; não usar como backtester |
| `historical_snapshot`/`read_replay` e hash | Padrão de snapshot e detecção de divergência | Capturar universo, calendário, eventos, ordens, fills e fonte/licença | Inspirar manifesto próprio |
| `calibration_sensitivity` e risco VaR/CVaR | Estresse de parâmetros GBM condicional | Manter distinto da incerteza de custos ou robustez da estratégia | Opcional, sem dependência no MVP |
| Black–Litterman `InputData`/`calculate` | Futuro construtor de carteira baseado em opiniões | Converter ativos, retornos simples totais na mesma frequência, covariância, benchmark e limites; pesos atuais são irrestritos, podem ser negativos ou não somar 1 | Adiar; não altera ranking 12–2 |

Nenhuma dessas bibliotecas oferece universo histórico B3, ordens, fills ou livro de caixa. Não incluí-las nas dependências do MVP.

## 9. Interfaces propostas e exemplos

Assinaturas de contrato (pseudocódigo Python tipado; implementação futura):

```python
from datetime import datetime, date
from typing import Protocol, Sequence, Mapping

class DataProvider(Protocol):
    def snapshot(self, start: date, end: date, *, as_of: datetime) -> "DataSnapshot": ...
    def bars(self, ids: Sequence[str], start: date, end: date, *, as_of: datetime) -> Sequence["PriceBar"]: ...
    def actions(self, ids: Sequence[str], start: date, end: date, *, as_of: datetime) -> Sequence["CorporateAction"]: ...

class UniverseProvider(Protocol):
    def members(self, session: date, *, as_of: datetime) -> Sequence["UniverseMembership"]: ...

class Strategy(Protocol):
    def signals(self, context: "ReadOnlyContext", *, decision_at: datetime) -> Sequence["Signal"]: ...

class PortfolioBuilder(Protocol):
    def targets(self, signals: Sequence["Signal"], state: "PortfolioState", limits: "Limits") -> Mapping[str, float]: ...
    def orders(self, targets: Mapping[str, float], state: "PortfolioState", *, created_at: datetime) -> Sequence["Order"]: ...

class ExecutionModel(Protocol):
    def execute(self, orders: Sequence["Order"], market: "AvailableMarketEvent", state: "PortfolioState") -> Sequence["Fill"]: ...

class Backtester(Protocol):
    def run(self, config: "RunConfig", snapshot: "DataSnapshot") -> "BacktestResult": ...

class Validator(Protocol):
    def audit(self, result: "BacktestResult", snapshot: "DataSnapshot") -> "ValidationReport": ...

class ReportGenerator(Protocol):
    def render(self, result: "BacktestResult", audit: "ValidationReport", output_dir: str) -> "ReportArtifacts": ...
```

Exemplo pequeno, **sintético**; valores não são tarifas B3 observadas:

```yaml
schema_version: 1
data_snapshot: synthetic-v1
calendar: synthetic-b3-v1
currency: BRL
initial_cash_brl: 100000
strategy: {name: momentum_12_2, top_n: 10, min_names: 5}
limits: {max_name_weight: 0.10, lot_default: 1, max_participation: 0.05}
execution: {first_fill: next_open, half_spread_bps: 5, slippage_bps: 5, fees_bps: 5}
seed: null
```

```json
{"type":"price_bar","instrument_id":"SYN-001","session":"2025-01-31","open":10.00,"high":10.30,"low":9.90,"close":10.20,"volume_shares":10000,"volume_brl":102000,"currency":"BRL","observed_at":"2025-01-31T20:00:00Z","available_at":"2025-01-31T20:05:00Z","adjustment_basis":"raw","source_id":"fixture","source_version":"1","snapshot_id":"synthetic-v1"}
{"type":"signal","instrument_id":"SYN-001","decision_at":"2025-01-31T20:06:00Z","feature_end_session":"2024-12-30","input_max_available_at":"2025-01-31T20:05:00Z","score":0.12,"eligible":true,"reason":"rank_1"}
{"type":"order","order_id":"O1","instrument_id":"SYN-001","created_at":"2025-01-31T20:06:00Z","earliest_execution_at":"2025-02-03T13:00:00Z","side":"buy","quantity":100,"target_weight":0.10,"expiry_session":"2025-02-05"}
{"type":"fill","fill_id":"F1","order_id":"O1","executed_at":"2025-02-03T13:00:00Z","session":"2025-02-03","quantity":100,"price":10.01,"spread_cost":0.50,"slippage_cost":0.50,"fees":0.50,"model_id":"next_open-v1"}
{"type":"result","run_id":"example-hash","session":"2025-02-03","nav_brl":100018.50,"cash_brl":98998.50,"positions_value_brl":1020.00,"receivable_brl":0.00,"gross_return":0.00020,"net_return":0.000185,"benchmark_return":0.0,"status":"COMPLETE"}
```

Esses trechos ilustram um calendário e preços **sintéticos**: abertura seguinte R$ 10,00, execução R$ 10,01, fechamento R$ 10,20, taxa R$ 0,50, caixa inicial R$ 100.000,00 e nenhuma outra posição ou fluxo. Spread e slippage (R$ 0,50 cada) já estão embutidos nos R$ 10,01 e não são debitados de novo; `cash = 100000 − 100×10,01 − 0,50 = 98998,50`, `NAV = cash + 100×10,20 = 100018,50`. O retorno bruto hipotético usa a mesma quantidade na abertura sem custo: `(100000 − 100×10,00 + 100×10,20)/100000 − 1 = 0,00020`. `benchmark_return` é apenas placeholder sintético. Para teste de aceite, completar os demais campos de proveniência exigidos pelo esquema e a série anterior de NAV.

## 10. Roadmap e critérios de aceite

Cada fase depende da anterior; as entradas e saídas indicadas tornam os critérios executáveis. Nenhuma fase requer dados externos antes da F3.

| Fase | Entrada definida → saída demonstrável | Aceite verificável |
|---|---|---|
| F0 Contratos | Esquemas, calendário e duas fixtures sintéticas (normal e adversa) → snapshots com hashes | Parser rejeita duplicatas, timestamps ingênuos, preço inválido, universo sobreposto e dado futuro; mesma entrada gera mesmo hash. |
| F1 Corte vertical | Snapshot sintético com 13+ meses, 5+ ativos, split, dividendo, suspensão e preço ausente → sinais, ordens, fills, livro, NAV e manifesto | Score 12–2 coincide com cálculo manual; nenhuma ordem executa no fechamento gerador; caixa/NAV conciliam centavo a centavo com a convenção monetária; status incompleto é explícito. |
| F2 Validação | Saídas F1 e duas configurações de custo → auditoria, controles, métricas e replay | Auditoria causal sem violações na fixture válida e falha na fixture vazada; replay repete hashes/NAV; custos maiores não elevam NAV quando fills fixos; relatório mostra limites. |
| F3 Dados reais limitados | Contrato/licença e amostra datada de barras/eventos → adaptador e relatório rotulado | Cobertura, gaps, timestamps, corporate actions e universo são auditados por tabela; quando faltar PIT/universo histórico, relatório exibe rótulo de viés e não publica comparação causal conclusiva. |
| F4 Pesquisa histórica auditável | Fonte com universo histórico e versões de disponibilidade, benchmark aprovado → avaliação final congelada | Reconstrução de membros em datas amostradas contra fonte, revisão manual de saídas, zero violações causais, período de teste não usado para escolha e métricas líquidas comparáveis no mesmo calendário. |

## 11. Matriz de testes proposta

| Nível | Entrada controlada | Saída/asserção |
|---|---|---|
| Unitário: 12–2 | 13 fechamentos e retornos mensais conhecidos, com salto só em `m−1` | Score usa `m−12…m−2`; mudar `m−1` não muda ranking, salvo elegibilidade. |
| Unitário: causalidade (teste de vazamento) | Duas bases iguais até `decision_at`, uma altera preços/eventos **após** `decision_at` | Hash de sinais, alvos e ordens até o corte deve ser idêntico; implementação que usar fechamento futuro falha. |
| Unitário: eventos | Split 2:1 e dividendo com ex/pagamento separados | Quantidade dobra, valor econômico é conservado no split; recebível nasce só com direito e caixa aumenta no pagamento. |
| Unitário: custos/execução | Ordem, abertura, spread/slippage/tarifa fixos, caixa justo | Fill e custo por rubrica exatos; compra insuficiente é reduzida/rejeitada; sem execução no mesmo fechamento. |
| Unitário: limites | Ranking com empate, lote 100, teto 10%, suspensão | Desempate estável; pesos e quantidades respeitam tetos/lote; suspenso não recebe fill. |
| Unitário: ausências | Barra faltante na janela, preço faltante em posição, universo tardio | Ativo inelegível; NAV_INCOMPLETO; membro tardio invisível até disponibilidade. |
| Integração: livro | Fixture de compra, venda parcial, taxa, provento e deslistagem resolvida | Livro, posições, recebíveis e NAV batem com planilha manual de valores esperados. |
| Integração: replay | Snapshot + manifesto + eventos preservados | Reexecução offline gera mesmo run hash e série NAV; alteração de um byte invalida hash ou muda run_id. |
| Propriedade: conservação | Sequências geradas de ordens e splits válidos | Caixa nunca negativo, quantidade nunca negativa, fills ≤ ordens, `NAV` concilia em toda sessão completa. |
| Propriedade: monotonicidade de custo | Mesmos fills e preços, custos crescentes | NAV líquido final não cresce; explicitar que fills variáveis invalidam esta propriedade. |

## 12. Decisões pendentes e riscos

| Decisão | Alternativas | Recomendação provisória | Evidência exigida antes de escolher |
|---|---|---|---|
| Fonte de preços/eventos | fornecedor licenciado, dados públicos, dataset próprio | Contratar/selecionar apenas após amostra auditada; protótipo sintético primeiro | Cobertura de deslistados, correções históricas, timestamps, eventos, volume, SLA e confronto com registros oficiais. |
| Licença e redistribuição | snapshot interno, artefatos derivados, dados publicáveis | Manter adaptador e dados reais fora do repositório até revisão de termos | Contrato escrito para armazenamento, replay, publicação de séries e compartilhamento de fixtures. |
| Universo histórico/PIT | constituintes históricos, cadastro de listagens, coorte atual | Exigir cadastro datado para avaliação causal; coorte atual apenas exploratória | Amostras de entradas/saídas, tickers antigos, fusões, data de anúncio e disponibilidade verificadas. |
| Benchmark | índice de retorno total, ETF investível, cesta causal | Avaliar índice total como referência e caixa/cesta como controles | Série licenciada, metodologia, rebalanceamento, data de publicação, dividendos e alinhamento de sessões. |
| Retorno e ajustes | total por eventos brutos, série ajustada do fornecedor, preço apenas | Eventos brutos + livro para NAV; ranking total PIT | Auditoria de splits/dividendos, cálculo em datas ex e pagas, arredondamento e dupla contagem. |
| Custos, lotes e liquidação | tabela por vigência, hipótese fixa | Parametrizar e divulgar sensibilidade até obter histórico | Tarifas/tributos e regras de negociação por período e tipo de instrumento, mais evidência de spread/impacto. |

**Riscos residuais:** seleção retrospectiva de parâmetros, mudanças de regime, benchmark inadequado, eventos incompletos, liquidez fictícia na abertura, custos não observados, viés de sobrevivência, revisão ex-post e diferença entre hipótese de fill e negociabilidade real. Relatório deve listar qual evidência os mitigou e manter os demais como limites, sem transformá-los em fatos.

## Conferência dos critérios de aceite

F0–F4 têm entradas e artefatos de saída explicitados na tabela; cada asserção remete a campo definido no contrato (`available_at`, `score`, `order`, `fill`, `cash`, `NAV`, `run_id`, `status`) ou a evidência externa requerida em F3/F4. O teste de vazamento compara duas entradas com prefixo temporal idêntico e saídas anteriores ao corte. Onde o valor exato depende de convenção pendente (benchmark, liquidação real, tarifa), o aceite exige primeiro uma configuração versionada e a fonte correspondente; nenhum teste pressupõe que esses dados já existam. O exemplo numérico confere a identidade do NAV, mas não substitui a fixture completa de F1.

**Primeiras tarefas de implementação:** (1) definir esquemas e fixtures sintéticas, inclusive relógio e calendário; (2) implementar consulta `as_of`, universo datado e score 12–2; (3) conectar ordem de próxima abertura, livro e replay; (4) escrever auditoria causal e os testes da F1 antes de qualquer adaptador B3.
