# Requisitos de segurança

## OWASP Top 10:2025

| Categoria | Controle obrigatório no projeto |
|---|---|
| A01 Controle de acesso quebrado | MVP somente leitura; rotas administrativas não publicadas; CORS em allowlist; nenhum caminho de arquivo vindo do cliente |
| A02 Configuração incorreta | debug e documentação desativáveis em produção; headers de segurança; erros sem stack trace; HTTPS na borda |
| A03 Cadeia de suprimentos | versões fixadas, lockfiles, auditoria de dependências e revisão de workflows |
| A04 Falhas criptográficas | segredos fora do Git; HTTPS; nenhuma criptografia própria |
| A05 Injeção | validação por Pydantic, SQL parametrizado, dimensões em allowlist e neutralização de CSV futuro |
| A06 Design inseguro | limites de período, paginação, rate limiting e threat model documentado |
| A07 Falhas de autenticação | sem autenticação no MVP; futura administração deverá usar provedor consolidado e MFA |
| A08 Integridade | checksum da fonte, dados brutos imutáveis, branch protegida e pipeline reproduzível |
| A09 Logs e alertas | logs estruturados, correlação, alertas de erro/abuso e ausência de segredos em logs |
| A10 Condições excepcionais | tratamento centralizado, timeout, limites de recursos e falha fechada |

## Critérios de release

- Nenhum segredo detectado no repositório.
- Nenhuma vulnerabilidade crítica conhecida em dependência de produção.
- Testes de validação, injeção, CORS, headers e limites aprovados.
- `APP_ENV=production`, origem CORS explícita e HTTPS no ambiente publicado.
- Arquivo de dados resolvido por configuração do servidor, nunca por parâmetro HTTP.
