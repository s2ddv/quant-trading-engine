# Sondagem yfinance — 04/11/2026

Consulta exploratória executada com `yfinance 1.7.0` em 04/11/2026 às 12:42 UTC. Comando:

```bash
PYTHONPATH=src python3 -m qtre.data.yfinance_probe --start 2024-01-01 --end 2025-03-01
```

Parâmetros: intervalo diário, `auto_adjust=False`, `actions=True`, `repair=False`; início inclusivo e fim exclusivo. Nenhum preço bruto foi incluído neste relatório.

| Ticker | Sessões | Primeira | Última | OHLC ausente/inválido | Volume zero | Dividendos | Splits |
|---|---:|---|---|---:|---:|---:|---:|
| PETR4.SA | 293 | 2024-01-02 | 2025-02-28 | 0 | 0 | 6 | 0 |
| VALE3.SA | 293 | 2024-01-02 | 2025-02-28 | 0 | 1 | 3 | 0 |
| ITUB4.SA | 293 | 2024-01-02 | 2025-02-28 | 0 | 0 | 20 | 0 |
| BBDC4.SA | 293 | 2024-01-02 | 2025-02-28 | 0 | 0 | 17 | 0 |
| ABEV3.SA | 293 | 2024-01-02 | 2025-02-28 | 0 | 0 | 1 | 0 |

As cinco consultas retornaram as colunas OHLC, `Adj Close`, `Volume`, `Dividends` e `Stock Splits`; não houve sessões duplicadas por ticker. Esta é uma fotografia da resposta da API naquela coleta. O fornecedor pode revisar o histórico, e este relatório não preserva os preços para replay.

**Classificação:** amostra de qualidade de dados, não snapshot causal nem backtest de ações B3. Faltam histórico de publicação/revisão por registro, universo histórico de ativos incluindo saídas, verificação de direitos de uso e horários de disponibilidade de eventos. Não atribuir `available_at` retroativo presumido a estes dados para executar o motor F1. A integração Monte Carlo permanece em fase posterior.

## Revalidação após revisão

Em 04/11/2026 às 12:57 UTC, a consulta foi repetida com `keepna=True`, preservando linhas ausentes retornadas pelo Yahoo. A [documentação da biblioteca](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) informa que o padrão é descartá-las. A auditoria passou a verificar infinitos, OHLC incoerente, volume negativo/fracionário, ações inválidas, datas fora do intervalo e ordenação.

As cinco séries retornaram novamente 293 linhas. Nenhum desses erros foi encontrado nesta coleta. `VALE3.SA` recebeu `REVIEW` pela linha com volume zero; as outras quatro receberam `OBSERVED`. Não houve confronto com calendário oficial, portanto estes resultados não demonstram ausência de sessões inteiras faltantes. `auto_adjust=False` não é certificado de preço bruto original nem elimina revisões históricas do fornecedor.
