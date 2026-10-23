# Deploy e operação

## Preparação

1. Instale Docker Engine com Compose v2.
2. Clone o repositório e gere as camadas de dados descritas em `docs/pipeline.md`.
3. Copie `.env.example` para `.env` e ajuste somente valores não secretos.
4. Mantenha tokens em arquivos fora do Git, com permissão mínima.

## Container local ou VPS

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 dashboard
curl http://127.0.0.1:8000/api/v1/health
```

O serviço é publicado apenas em `127.0.0.1:8000`, executa com filesystem somente
leitura, remove todas as capabilities Linux e monta dados curados como somente leitura.

## Cloudflare Tunnel

Crie um túnel remotamente gerenciado e direcione o hostname ao serviço interno
`http://dashboard:8000`. Grave o token em `.secrets/cloudflare-tunnel-token` e execute:

```bash
bash deploy/configure-cloudflare-tunnel.sh
docker compose up -d cloudflared
docker compose logs --tail=100 cloudflared
```

Não coloque o token no Compose, README, `.env`, histórico do shell ou issue pública.
Para aplicações com políticas diferentes, crie aplicações Cloudflare Access separadas
por hostname ou caminho e associe políticas específicas a cada uma.

## Atualização

```bash
git pull --ff-only
docker compose up -d --build
docker compose ps
```

Antes de atualizar produção, execute os testes, confirme espaço em disco e preserve
uma cópia dos Parquets curados anteriores para rollback.

## Diagnóstico

```bash
docker compose ps
docker compose logs --tail=200 dashboard
docker compose logs --tail=200 cloudflared
curl -i http://127.0.0.1:8000/api/v1/health
```

- HTTP 503 nos endpoints opcionais: gere ou monte o Parquet correspondente;
- túnel inativo: confirme token, saúde do `dashboard` e DNS do hostname;
- container reiniciando: verifique permissões dos volumes e caminhos das variáveis;
- resposta 429: ajuste o consumidor ou, após análise, `RATE_LIMIT_PER_MINUTE`.

## Rollback

Use uma revisão Git conhecida e os Parquets compatíveis daquela versão:

```bash
git switch --detach COMMIT_VALIDADO
docker compose up -d --build
```

Não use `git reset --hard` em um diretório com alterações locais não preservadas.
