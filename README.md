# Dashboard da Malha Aérea Brasileira

Dashboard para explorar a oferta programada da malha aérea brasileira a partir de
dados públicos da Agência Nacional de Aviação Civil (ANAC/SIROS).

## Documentação

- [Arquitetura e fluxo de dados](docs/architecture.md)
- [Pipeline de coleta e processamento](docs/pipeline.md)
- [Machine learning aplicado à análise de atrasos](docs/machine-learning.md)
- [Referência da API](docs/api.md)
- [Dicionário de dados e métricas](docs/data-dictionary.md)
- [Deploy e operação](docs/deployment.md)
- [Requisitos de segurança](docs/security.md)
- [Política para reporte de vulnerabilidades](SECURITY.md)

> **Limitação essencial:** a base SIROS representa serviços programados. A camada VRA
> acrescenta horários realizados e cancelamentos oficiais. Assentos previstos não são
> passageiros transportados; a futura métrica de passageiros impactados será estimada
> e identificada como tal.

## Estado atual

- intervalo mensal de março/2018 a dezembro/2025;
- decolagens programadas e assentos previstos;
- filtros por mercado, companhia, origem e destino;
- séries mensais e rankings de aeroportos, companhias e rotas;
- API agregadora, sem envio do Parquet bruto ao navegador;
- interface responsiva e documentação metodológica.
- pontualidade, faixas de atraso e cancelamentos oficiais do VRA;
- associação descritiva entre meteorologia INMET e desempenho operacional;
- recorte operacional inicial: voos domésticos regulares (`Código Tipo Linha = N`).

O pipeline VRA de pontualidade e a integração meteorológica INMET estão disponíveis
para o recorte doméstico. Passageiros estimados permanecem dependentes da importação
manual do arquivo oficial de Dados Estatísticos da ANAC.

## Pipeline VRA

Os arquivos brutos são imutáveis e ignorados pelo Git. Cada download recebe um arquivo
de metadados com URL, data de coleta, tamanho e SHA-256.

```bash
python -m coletores.collect_vra --start-month 2018-01 --end-month 2025-12
python -m coletores.build_vra
```

Nesta primeira fase, o processamento inclui somente o tipo de linha `N` (voos
domésticos regulares de passageiros),
preserva os horários no fuso sem conversão implícita e gera
`data/curated/flight_delay_analysis.parquet`.

### Passageiros e meteorologia

O portal dos Dados Estatísticos pode exigir download interativo. Sem contornar esse
controle, importe o CSV oficial obtido no portal e gere a camada estimada:

```bash
python -m coletores.import_anac_statistics --source-file CAMINHO_DO_CSV_OFICIAL
python -m coletores.build_passenger_impact
```

Os históricos anuais públicos do INMET podem ser coletados com:

```bash
python -m coletores.collect_inmet --start-year 2018 --end-year 2025
python -m coletores.build_weather
```

Passageiros impactados são estimativas mensais por empresa e rota; não representam a
lista efetiva de ocupantes de um voo. Meteorologia deve ser interpretada como associação,
e não como causa comprovada de atraso.

## Arquitetura

O backend FastAPI consulta o Parquet consolidado por meio do DuckDB e entrega somente
agregações ao frontend React/TypeScript. Consulte [a documentação de arquitetura](docs/architecture.md)
e o [dicionário de dados](docs/data-dictionary.md).

## Estrutura

```text
backend/       API, serviços analíticos e testes
frontend/      interface React/TypeScript
coletores/     coletores originais
data/          dados brutos, intermediários e curados (não versionados)
dados_api/     extrações mensais originais
data_voo/      Parquets consolidados
docs/          arquitetura, dados e segurança
```

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- npm, pnpm ou equivalente

## Backend

```bash
python -m venv .venv
.venv/Scripts/activate
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

A API estará em `http://localhost:8000` e a documentação de desenvolvimento em
`http://localhost:8000/docs`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

A interface estará em `http://localhost:5173`; o Vite encaminha `/api` para o backend.

## Configuração

Copie `.env.example` para `.env` apenas no ambiente local. Variáveis:

| Variável | Finalidade |
|---|---|
| `APP_ENV` | `development` ou `production` |
| `ANAC_DATA_FILE` | caminho servidor do Parquet consolidado |
| `ANAC_DELAY_DATA_FILE` | Parquet analítico de atrasos e cancelamentos VRA |
| `ANAC_PASSENGER_IMPACT_FILE` | Parquet opcional de passageiros impactados estimados |
| `INMET_AIRPORT_WEATHER_FILE` | Parquet meteorológico agregado por aeroporto/mês |
| `ANAC_MANIFEST_DIR` | diretório dos metadados de coleta VRA |
| `ALLOWED_ORIGINS` | origens CORS separadas por vírgula |
| `MAX_PERIOD_MONTHS` | maior intervalo permitido |
| `RATE_LIMIT_PER_MINUTE` | limite por endereço cliente |
| `SERVE_FRONTEND` | permite ao FastAPI servir o build do frontend |
| `FRONTEND_DIR` | diretório do build estático |

Nunca versione o arquivo `.env` ou chaves privadas.

## Docker e VPS

A imagem final executa somente Python/FastAPI. O Node é usado apenas no estágio de
compilação do frontend e não permanece na imagem de produção.

```bash
docker compose build
docker compose up -d
docker compose ps
```

Por segurança, o Compose publica a aplicação somente em `127.0.0.1:8000`. Em uma
VPS, coloque Nginx, Caddy ou outro proxy reverso com HTTPS na frente do container.
O diretório `data_voo` é montado como volume somente leitura.

Para validar:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### Cloudflare Tunnel

Crie um túnel remotamente gerenciado no painel da Cloudflare e configure o hostname
público para o serviço `http://dashboard:8000`. Grave somente o token específico do
túnel em `.secrets/cloudflare-tunnel-token`:

```bash
bash deploy/configure-cloudflare-tunnel.sh
```

O token nunca deve ser colocado em `.env`, comandos versionados, issues ou logs. O
container usa `--token-file`, não publica portas e alcança o dashboard apenas pela rede
interna do Compose.

## Endpoints

- `GET /api/v1/health`
- `GET /api/v1/metadata`
- `GET /api/v1/filters`
- `GET /api/v1/summary`
- `GET /api/v1/timeseries`
- `GET /api/v1/airports`
- `GET /api/v1/airlines`
- `GET /api/v1/routes`
- `GET /api/v1/delays/summary`
- `GET /api/v1/delays/timeseries`
- `GET /api/v1/delays/buckets`
- `GET /api/v1/delays/airports`
- `GET /api/v1/delays/airlines`
- `GET /api/v1/delays/flights` (paginação obrigatória por `limit` e `offset`)
- `GET /api/v1/cancellations`
- `GET /api/v1/data-quality`
- `GET /api/v1/collection/status`
- `GET /api/v1/passengers/impacted`
- `GET /api/v1/weather/correlation`
- `GET /api/v1/ml/delay-analysis`

Exemplo:

```text
/api/v1/summary?start_month=2025-01&end_month=2025-12&market=domestic
```

## Testes

```bash
pytest
cd frontend
npm run build
```

## Experimento de machine learning

O projeto inclui uma prova de conceito com `HistGradientBoostingClassifier` para
classificar atrasos de partida de 30 minutos ou mais. O treino usa uma amostra
temporal reduzida e ocorre fora da API:

```bash
pip install -r requirements-ml.txt
python -m ml.train_delay_model --train-rows 120000 --test-rows 50000
```

O teste usa anos posteriores aos do treino. Variáveis conhecidas somente após a
operação não entram no modelo, exceto a meteorologia mensal observada, usada apenas
na análise retrospectiva e explicitamente incompatível com previsão em tempo real.
Os artefatos em `data/models/` e o JSON de métricas
em `data/curated/` são locais e não são versionados. O painel identifica o resultado
como experimental; ele não deve orientar decisões operacionais.

Consulte [a documentação completa do processo de machine learning](docs/machine-learning.md)
para conhecer seleção dos dados, variáveis, hiperparâmetros, resultados e limitações.

## Segurança

O projeto adota OWASP Top 10:2025 e controles verificáveis inspirados no ASVS 5.0.
Consulte [SECURITY.md](SECURITY.md) para reporte responsável e
[docs/security.md](docs/security.md) para os requisitos técnicos.

## Metodologia

- Decolagem programada: uma etapa com origem e partida prevista válidas.
- Assentos previstos: soma da capacidade planejada não negativa.
- Rota ativa: par direcional distinto de origem e destino.
- Competência mensal: mês da partida prevista em UTC.

Registros inválidos não devem ser silenciosamente convertidos em zero. Revisões da
fonte podem alterar resultados históricos.

## Fonte e atribuição

Dados provenientes da ANAC. A licença aplicável aos dados e a licença do código devem
ser confirmadas antes da primeira publicação pública do projeto.

## Roadmap

1. Importar e validar os Dados Estatísticos oficiais para estimar passageiros impactados.
2. Ampliar o recorte operacional para voos internacionais após validação metodológica.
3. Adicionar exportações e indicadores avançados de conectividade.
4. Automatizar atualização, observabilidade e testes de qualidade das fontes.
