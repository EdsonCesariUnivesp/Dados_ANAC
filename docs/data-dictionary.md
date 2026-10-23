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
- **Regularidade do serviço:** `regular` seleciona valores iniciados por `REGULAR` e
  `non_regular` seleciona valores iniciados por `NÃO REGULAR`. Sobrevoos, traslados e
  registros não classificados aparecem apenas em `all`.

## Camada VRA — `flight_delay_analysis`

| Campo | Tipo lógico | Descrição |
|---|---|---|
| `airline_icao` | texto | Designador ICAO da empresa |
| `flight_number` | texto | Número do voo preservado como texto |
| `digit_identifier` | texto | Dígito identificador da etapa |
| `line_type` | texto | `N`; a fase inicial contém apenas voos domésticos regulares |
| `origin_icao` / `destination_icao` | texto | Aeródromos da etapa |
| `scheduled_departure_local` | data/hora | Partida prevista em horário de Brasília conforme a fonte |
| `actual_departure_local` | data/hora | Partida realizada conforme a fonte |
| `flight_status` | texto | Situação oficial do VRA |
| `departure_delay_minutes` | inteiro | Diferença real menos prevista, somente para realizados válidos |
| `delay_bucket` | texto | Bucket exclusivo de antecipação, pontualidade, atraso ou cancelamento |
| `planned_seats` | inteiro | Assentos planejados; não representa passageiros transportados |

Cancelamento deriva exclusivamente de `flight_status`. Atrasos iguais ou superiores a
120 minutos são classificados como `atraso_critico_120_mais`, nunca como cancelamento.

## Passageiros impactados — estimativa

`passenger_impact_analysis` associa aos voos atrasados em pelo menos dez minutos ou
cancelados a média de passageiros por decolagem do mesmo mês, empresa, origem, destino
e natureza. Os campos `estimated_paid_passengers_impacted` e
`estimated_total_passengers_impacted` são estimativas, não contagens por voo.
`estimate_matched` permite calcular e publicar a cobertura do casamento.

## Meteorologia por aeroporto/mês

`airport_station_mapping.csv` registra a estação INMET mais próxima, sua distância e
se está no limite padrão de 50 km. `airport_weather.parquet` contém observações horárias
agregadas por aeroporto e mês: precipitação, horas com chuva, temperatura, vento,
rajada, umidade e pressão. Correlações são descritivas e não comprovam causalidade.
