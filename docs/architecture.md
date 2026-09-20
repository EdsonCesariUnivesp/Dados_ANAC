# Arquitetura

```text
Parquets ANAC/SIROS
        │
        ▼
Validação e normalização
        │
        ▼
DuckDB (consulta somente leitura)
        │
        ▼
FastAPI ── JSON agregado ── React/TypeScript
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
- O MVP é público e somente leitura; não há autenticação ou upload.
- Passageiros, cancelamentos e atrasos aguardam integração com outras bases ANAC.
