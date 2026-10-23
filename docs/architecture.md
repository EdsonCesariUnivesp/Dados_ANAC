# Arquitetura

```text
ANAC/SIROS ─┐
ANAC/VRA ───┼── raw + manifesto SHA-256
ANAC/Dados  ┤              │
INMET ──────┘              ▼
                    staging / curated
                           │
                           ▼
                DuckDB (somente leitura)
                           │
                           ▼
              FastAPI ─ JSON agregado ─ React
```

O navegador nunca recebe a base bruta. A API aceita somente filtros tipados e gera
consultas parametrizadas. Dimensões usadas em SQL são selecionadas exclusivamente
por uma allowlist interna.

## Limites de confiança

- Internet → frontend: entrada não confiável.
- Frontend → API: entrada não confiável e sempre revalidada.
- Parquet → pipeline/API: dado externo que exige validação de schema e conteúdo.
- Configuração de ambiente → aplicação: acesso restrito à operação.

## Decisões

- O Parquet histórico permanece como fonte da primeira etapa.
- DuckDB executa agregações sem carregar 6,7 milhões de registros no navegador.
- A API é versionada em `/api/v1`.
- O dashboard é somente leitura; proteção de acesso pode ser aplicada na borda com Cloudflare Access.
- O VRA é a fonte de situação oficial e horários realizados.
- A coleta é um processo offline; a API pública não dispara downloads.
- Passageiros por voo são estimados a partir de agregados mensais e sempre rotulados.
- Meteorologia é apresentada como associação, não como causalidade.
