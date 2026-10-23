# Referência da API

A API HTTP é somente leitura, usa JSON e está versionada em `/api/v1`. Em
desenvolvimento, a especificação OpenAPI fica disponível em `/docs`.

O dashboard publica a metodologia em `/metodologia`, sem redirecionar o usuário para
um serviço externo.

## Filtros comuns

| Parâmetro | Formato | Observação |
|---|---|---|
| `start_month` | `AAAA-MM` | mês inicial inclusivo |
| `end_month` | `AAAA-MM` | mês final inclusivo |
| `market` | `all`, `domestic`, `international` | endpoints VRA aceitam somente `domestic` nesta fase |
| `regularity` | `all`, `regular`, `non_regular` | regularidade oficial do serviço na camada SIROS |
| `airline` | código ICAO, 2–4 caracteres | normalizado para maiúsculas |
| `origin` / `destination` | código ICAO, 3–4 caracteres | normalizado para maiúsculas |

O período não pode ser invertido nem ultrapassar `MAX_PERIOD_MONTHS`. Valores
inválidos retornam HTTP 422.

## Oferta programada

| Endpoint | Resultado |
|---|---|
| `GET /health` | saúde básica da aplicação |
| `GET /metadata` | cobertura e metadados da base SIROS |
| `GET /filters` | opções disponíveis para filtros |
| `GET /summary` | indicadores consolidados |
| `GET /timeseries` | série mensal de decolagens e assentos |
| `GET /airports` | ranking de aeroportos |
| `GET /airlines` | ranking de empresas |
| `GET /routes` | ranking de rotas |

Rankings recebem `limit` entre 1 e 100.

## Operação doméstica

| Endpoint | Resultado |
|---|---|
| `GET /delays/summary` | pontualidade, atrasos e cancelamentos |
| `GET /delays/timeseries` | evolução mensal operacional |
| `GET /delays/buckets` | distribuição exclusiva por faixa de atraso |
| `GET /delays/airports` | ranking operacional por origem |
| `GET /delays/airlines` | ranking operacional por empresa |
| `GET /delays/flights` | registros paginados; `limit` 1–1000 e `offset` obrigatório quando usado |
| `GET /cancellations` | cancelamentos oficiais por mês |
| `GET /data-quality` | cobertura e ausências da camada VRA |
| `GET /collection/status` | quantidade e data dos manifestos coletados |
| `GET /passengers/impacted` | estimativa, cobertura e limitações do casamento |
| `GET /weather/correlation` | correlações descritivas aeroporto/mês |
| `GET /ml/delay-analysis` | métricas e variáveis relevantes do experimento de ML |

Exemplos:

```bash
curl "http://127.0.0.1:8000/api/v1/delays/summary?start_month=2025-01&end_month=2025-12&market=domestic"
curl "http://127.0.0.1:8000/api/v1/delays/flights?start_month=2025-01&end_month=2025-01&market=domestic&origin=SBGR&limit=50&offset=0"
```

Cancelamento deriva somente de `flight_status = CANCELADO`. Atrasos de 120 minutos
ou mais continuam sendo atrasos críticos. Correlação meteorológica não comprova
causalidade, e passageiros impactados são sempre identificados como estimativa.

`/ml/delay-analysis` não executa inferência nem treinamento. Ele serve um artefato
JSON previamente validado e retorna `503` quando o experimento ainda não foi gerado.

## Erros esperados

- `422`: filtro, intervalo ou paginação inválidos;
- `429`: limite de requisições excedido;
- `500`: falha controlada durante consulta;
- `503`: camada de dados opcional ainda não processada.
