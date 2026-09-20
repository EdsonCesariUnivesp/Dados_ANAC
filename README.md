# Dashboard da Malha Aérea Brasileira

Dashboard para explorar a oferta programada da malha aérea brasileira a partir de
dados públicos da Agência Nacional de Aviação Civil (ANAC/SIROS).

> **Limitação essencial:** os registros representam serviços programados. Assentos
> previstos não são passageiros transportados, e a presença de uma etapa não comprova
> que o voo foi realizado. A base atual não contém cancelamentos nem horários reais.

## Escopo do MVP

- intervalo mensal de março/2018 a dezembro/2025;
- decolagens programadas e assentos previstos;
- filtros por mercado, companhia, origem e destino;
- séries mensais e rankings de aeroportos, companhias e rotas;
- API agregadora, sem envio do Parquet bruto ao navegador;
- interface responsiva e documentação metodológica.

Passageiros efetivos, cancelamentos e atrasos dependem de integrações futuras com os
Dados Estatísticos do Transporte Aéreo e com o Voo Regular Ativo (VRA).

## Arquitetura

O backend FastAPI consulta o Parquet consolidado por meio do DuckDB e entrega somente
agregações ao frontend React/TypeScript. Consulte [a documentação de arquitetura](docs/architecture.md)
e o [dicionário de dados](docs/data-dictionary.md).

## Estrutura

```text
backend/       API, serviços analíticos e testes
frontend/      interface React/TypeScript
coletores/     coletores originais
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

1. Consolidar o MVP de oferta programada.
2. Integrar passageiros realizados por meio dos Dados Estatísticos.
3. Integrar cancelamentos e atrasos por meio do VRA.
4. Adicionar alertas, exportações e indicadores avançados de conectividade.
