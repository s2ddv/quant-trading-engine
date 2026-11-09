# Contrato v1 — relatório comparativo F2

**Estado:** contrato documental proposto em 09/11/2026, America/Sao_Paulo. O leitor e este formato de saída ainda não foram implementados. A fonte observada é `examples/f2_cost_sensitivity_v1/` (nove execuções sintéticas e `sensitivity.json`). Este contrato não muda o [protocolo F2](protocolo-pesquisa-f2-v1.md), a [sensibilidade registrada](sensibilidade-custos-f2-v1.md) nem qualquer cálculo financeiro.

## Escopo e evidência

O leitor futuro recebe um diretório de execuções **já persistidas** e produz um JSON consolidado e, opcionalmente, uma tabela humana. Não roda o motor. Deve reconstruir cada execução com `replay_f1`, exigir `audit_f1_run(...)["status"] == "VALID"`, conferir manifesto, hashes, identidades e conciliação antes de publicar números. `sensitivity.json` é uma fonte de confronto, não substitui a leitura independente dos subdiretórios. Um erro em uma execução impede a emissão de um relatório comparativo válido; o erro deve identificar caminho e motivo, sem preencher valores com zero.

Na conferência documental desta versão, `sensitivity.json` tinha SHA-256 `23335a0acb600b3a1bd83a1f91a77df321a2a1b6d7ed375b19920a0ce1961dca`, `report_schema_version: 1` e `synthetic: true`. Os nove `run_id` coincidiam entre `sensitivity.json`, `manifest.json` e `audit.json`; todos os `audit.json` registravam `VALID`, e os hashes dos seis arquivos listados em cada manifesto coincidiam com seus bytes. Isso verifica os arquivos presentes, sem constituir nova execução de replay/auditoria ou validação econômica.

## Esquema JSON mínimo proposto

O objeto completo tem exatamente três estratégias (`momentum`, `equal_weight`, `cash`), cada uma com os cenários `zero`, `base`, `high`, e dois pares adjacentes por estratégia (`zero_to_base`, `base_to_high`). `report_schema_version` **deste leitor** é independente do `report_schema_version` do `sensitivity.json` e das versões do manifesto, auditoria e resumo. Campos obrigatórios:

```text
{
  "report_schema_version": 1,
  "source": {"path": string, "sensitivity_sha256": string, "synthetic": true},
  "runs": {
    "<strategy>": {
      "<scenario>": {
        "source_path": string,
        "run_id": string,
        "manifest_sha256": string,
        "audit_status": "VALID",
        "identity": {
          "snapshot_hash": string, "calendar_id": string,
          "model_id": string, "code_hash": string,
          "decision_ats": [string], "config": object
        },
        "decisions": integer, "sessions": integer,
        "orders": integer, "fills": integer,
        "costs_brl": {"spread_cost": string, "slippage_cost": string,
                      "fees": string, "total": string},
        "costs_bps": {"total": string|null, "status": string},
        "final_cash_brl": string,
        "final_receivable_brl": string,
        "final_positions_value_brl": string|null,
        "final_nav_brl": string|null,
        "incomplete_sessions": [string],
        "cumulative_return": string|null,
        "return_status": string
      }
    }
  },
  "comparisons": {
    "<strategy>": {
      "<pair>": {
        "earlier_run_id": string, "later_run_id": string,
        "fills_identical": boolean,
        "nav_schedule_identical": boolean,
        "monotonicity": string,
        "reason": string|null,
        "nav_points_compared": integer|null
      }
    }
  }
}
```

`source_path` é relativo a `source.path`; não pode escapar do diretório recebido. `sensitivity_sha256` e `manifest_sha256` são SHA-256 hexadecimais dos bytes dos respectivos arquivos. `decision_ats` vem das janelas do manifesto, em ordem, no formato ISO 8601 com offset. `config` preserva todas as chaves e strings decimais do manifesto, inclusive os três custos do cenário; não é uma configuração reconstruída de defaults. O JSON consolidado deve usar ordem estável de chaves e listas, strings decimais exatas e nenhuma data de geração variável, para ter os mesmos bytes diante das mesmas entradas. Valores monetários não devem passar por `float`.

| Campo | Unidade e interpretação |
|---|---|
| `decisions`, `sessions`, `orders`, `fills`, `nav_points_compared` | Contagens inteiras; `sessions` conta linhas de NAV, inclusive as incompletas. |
| `costs_brl.*`, `final_cash_brl`, `final_receivable_brl`, `final_positions_value_brl`, `final_nav_brl` | BRL, `Decimal` serializado como string; `total` é soma exata das três rubricas. |
| `costs_bps.total` | bps do nocional de referência negociado: `10000 × costs_brl.total / Σ reference_notional` dos fills. Não é a soma dos parâmetros de custo. Preservar a precisão Decimal do cálculo, sem arredondamento adicional. |
| `cumulative_return` | Fração adimensional líquida, `NAV_último / NAV_primeiro − 1`, somente com série completa e denominador válido; `"0"` é retorno zero observado, diferente de `null`. |
| `incomplete_sessions` | Datas de sessão `YYYY-MM-DD` em que o NAV tem estado `NAV_INCOMPLETO`. |

## Estados e regras de ausência

`costs_bps.status` é `AVAILABLE` com string numérica se o nocional for positivo, ou `UNAVAILABLE_NO_NOTIONAL` com `total: null` se não houver nocional, como em `cash`. Custo monetário zero continua `"0"` e não é ausente. `return_status` usa `AVAILABLE_SYNTHETIC` com retorno numérico para série completa, `UNAVAILABLE_INCOMPLETE_NAV` com `cumulative_return: null` se qualquer marca for incompleta, ou `UNAVAILABLE_NO_NAV` com `null` se faltar série/denominador válido em uma fonte aceitável. Uma fonte sem NAV exigido pelo contrato de artefatos deve ser rejeitada como inválida, em vez de ser silenciosamente tratada como série vazia. Se a **última** marca for incompleta, `final_nav_brl` e `final_positions_value_brl` ficam `null`; caixa e recebíveis continuam observáveis. Não imputar marcas e não calcular métricas que dependem da série completa.

Falha de arquivo/hash, replay, auditoria, identidade, configuração, conciliação ou par faltante é erro de entrada (`INVALID_SOURCE` com caminho e motivo fora do relatório válido), não um terceiro tipo de retorno. O leitor não publica comparação parcial como se fosse o conjunto de nove. Uma execução sintética válida ainda é inconclusiva quanto a desempenho B3.

## Identidade e comparabilidade

Cada célula `(strategy, scenario)` aponta para um subdiretório e `run_id` distintos. O `run_id` deve ser igual nos três registros observados; `audit.json` deve referir o hash do manifesto e os hashes de artefatos correspondentes. O manifesto é a autoridade para `snapshot_hash`, calendário, modelo, código, janelas de decisão e configuração. Entre cenários da mesma estratégia, exigir a mesma identidade de snapshot, calendário, modelo, código, janelas de decisão e todos os parâmetros exceto `half_spread_bps`, `slippage_bps` e `fees_bps`, que devem coincidir com `zero=(0,0,0)`, `base=(5,5,5)` e `high=(15,15,10)`. Entre estratégias, exigir o mesmo snapshot, calendário, instantes de decisão, sessões de formação/execução e hipóteses de execução/custos; o `model_id`, `run_id` e motivos de formação próprios de cada controle devem ser preservados. As janelas completas observadas diferem entre `cash` e as estratégias com posições por causa do motivo de formação, portanto não se exige igualdade byte a byte dessas janelas. Divergência nos campos comuns bloqueia comparação e deve ser explicada.

Para cada par adjacente da **mesma estratégia**, reutilizar a semântica de `compare_pair`: comparar a assinatura ordenada dos fills (`order_id`, sessão, instante e quantidade) e a agenda ordenada do NAV (`session`, `status`). `orders_identical` pode ser exibido como detalhe adicional, mas não é condição suficiente nem necessária para o teste vigente. Se fills ou agenda diferirem, `monotonicity` é `NOT_COMPARABLE_EXECUTION_CHANGED`, `reason` identifica qual mudou e `nav_points_compared` é `null`. Mesmo que os dois NAVs finais existam, não declarar monotonicidade. Se ambos coincidirem, confrontar custos totais não decrescentes e NAVs não crescentes apenas nas marcas completas alinhadas; usar `PASS` ou `FAIL` conforme `compare_pair` e registrar o número de pontos completos. Uma falha de propriedade deve ser exposta como falha, nunca corrigida por omissão. `PASS` para `cash` sem negócios é uma propriedade vacuamente satisfeita do controle, sem evidência de custo de negociação. A comparação entre estratégias é descritiva: NAVs iguais na fixture não provam equivalência geral.

## Exemplo parcial com valores observados

O bloco abaixo mostra **duas** das nove células e **um** dos seis pares, para caber na página; uma saída válida conterá todas as células e pares. As chaves do envelope, `source_path`, `identity`, `costs_bps.status`, `reason` e a organização dos objetos são **propostas** por este contrato. IDs, hashes, contagens, custos, NAV, estados e resultados do par são **observados** nos artefatos persistidos; `manifest_sha256` é o valor registrado em `audit.json`. `identity` e `config` foram omitidos somente neste recorte didático.

```json
{
  "report_schema_version": 1,
  "source": {
    "path": "examples/f2_cost_sensitivity_v1",
    "sensitivity_sha256": "23335a0acb600b3a1bd83a1f91a77df321a2a1b6d7ed375b19920a0ce1961dca",
    "synthetic": true
  },
  "runs": {
    "momentum": {
      "base": {
        "source_path": "momentum-base",
        "run_id": "4391688841ea80030da871c44bec722836741ef364e0a9f1710c75c57ccd6b71",
        "manifest_sha256": "37a189b041516b6d9205cd51d0396ba247c1ee7e790a23236d7e1a571eede289",
        "audit_status": "VALID",
        "decisions": 4, "sessions": 66, "orders": 16, "fills": 16,
        "costs_brl": {"spread_cost": "30.27", "slippage_cost": "30.24", "fees": "30.27", "total": "90.78"},
        "costs_bps": {"total": "15.00347073017551978316200046", "status": "AVAILABLE"},
        "final_cash_brl": "50712.22", "final_receivable_brl": "0",
        "final_positions_value_brl": "50536.00", "final_nav_brl": "101248.22",
        "incomplete_sessions": ["2025-02-04"],
        "cumulative_return": null, "return_status": "UNAVAILABLE_INCOMPLETE_NAV"
      }
    },
    "cash": {
      "base": {
        "source_path": "cash-base",
        "run_id": "e74aab4f519c103fbf8f058e84d6d82866b3469f0ff7480b81fbb31f1af0fefd",
        "audit_status": "VALID",
        "decisions": 4, "sessions": 66, "orders": 0, "fills": 0,
        "costs_brl": {"spread_cost": "0", "slippage_cost": "0", "fees": "0", "total": "0"},
        "costs_bps": {"total": null, "status": "UNAVAILABLE_NO_NOTIONAL"},
        "final_cash_brl": "100000", "final_receivable_brl": "0",
        "final_positions_value_brl": "0.00", "final_nav_brl": "100000.00",
        "incomplete_sessions": [],
        "cumulative_return": "0", "return_status": "AVAILABLE_SYNTHETIC"
      }
    }
  },
  "comparisons": {
    "momentum": {
      "zero_to_base": {
        "earlier_run_id": "9a77cb8b07190054be2ba029abb0c7033a6898e129042f557e296d85f74a7c01",
        "later_run_id": "4391688841ea80030da871c44bec722836741ef364e0a9f1710c75c57ccd6b71",
        "fills_identical": false, "nav_schedule_identical": true,
        "monotonicity": "NOT_COMPARABLE_EXECUTION_CHANGED",
        "reason": "fills_differ", "nav_points_compared": null
      }
    }
  }
}
```

No caso `momentum-base`, `50712.22 + 0 + 50536.00 = 101248.22` BRL na última marca, mas a marca incompleta de 04/02/2025 impede o retorno da série. Nos três cenários com posições há 15, 16 e 15 fills; os quatro pares adjacentes de `momentum`/`equal_weight` têm `NOT_COMPARABLE_EXECUTION_CHANGED`. `cash` tem 66 marcas completas, nenhum fill e retorno sintético zero. A fixture cobre quatro decisões e não oferece janela fora da amostra, estimativa de incerteza ou evidência de desempenho B3.

## Verificação desta entrega

Foram lidos os contratos, proposta e artefatos persistidos; comparados os nove IDs e estados de auditoria; recalculados SHA-256 dos arquivos referidos pelos nove manifestos; conferidos campos do exemplo com `sensitivity.json` e `audit.json`. Não foram executados motor, backtest, replay, auditoria ou suíte de testes nesta entrega documental. O próximo passo é implementar e testar o leitor contra este contrato, inclusive fonte adulterada, identidade divergente, `NAV_INCOMPLETO`, nocional zero, fills diferentes e determinismo.
