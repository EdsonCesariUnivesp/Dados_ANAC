# Dicionário de dados

| Campo | Tipo lógico | Descrição |
|---|---|---|
| `dt_referencia` | data | Data de referência do registro |
| `sg_empresa_icao` | texto | Designador ICAO da empresa aérea |
| `nr_etapa` | inteiro | Número da etapa do voo |
| `nr_voo` | texto | Número do voo |
| `sg_equipamento_icao` | texto | Código ICAO do modelo da aeronave |
| `qt_assentos_previstos` | inteiro | Capacidade programada; não representa passageiros |
| `sg_icao_origem` | texto | Código ICAO do aeroporto de origem |
| `dt_partida_prevista_utc` | data/hora | Partida programada em UTC |
| `sg_icao_destino` | texto | Código ICAO do aeroporto de destino |
| `dt_chegada_prevista_utc` | data/hora | Chegada programada em UTC |
| `ds_tipo_servico` | texto | Classificação do serviço aéreo |
| `tx_codeshare` | texto | Informação declarada de codeshare |

## Métricas do MVP

- **Decolagens programadas:** contagem de etapas com origem e partida prevista válidas.
- **Assentos previstos:** soma não negativa de `qt_assentos_previstos`.
- **Rotas ativas:** pares direcionais distintos origem → destino.
- **Aeroportos de origem:** origens distintas no período filtrado.
- **Companhias ativas:** empresas distintas no período filtrado.
