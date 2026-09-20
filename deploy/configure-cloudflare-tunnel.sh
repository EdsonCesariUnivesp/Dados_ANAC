#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

project_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "${project_directory}"

install -d -m 700 .secrets

read -r -s -p "Token específico do túnel Cloudflare (eyJ...): " tunnel_token </dev/tty
echo >/dev/tty

if [[ -z ${tunnel_token} ]]; then
  echo "Token vazio; nenhuma alteração foi feita." >&2
  exit 1
fi

if [[ ! ${tunnel_token} =~ ^eyJ[A-Za-z0-9._-]+$ ]]; then
  echo "Formato inesperado. Use o token do túnel, não um API Token geral." >&2
  exit 1
fi

temporary_file=$(mktemp .secrets/cloudflare-tunnel-token.XXXXXX)
trap 'rm -f "${temporary_file}"; unset tunnel_token' EXIT
printf '%s' "${tunnel_token}" > "${temporary_file}"
unset tunnel_token
chmod 600 "${temporary_file}"
mv -f "${temporary_file}" .secrets/cloudflare-tunnel-token
trap - EXIT

echo "Token gravado com $(stat -c %s .secrets/cloudflare-tunnel-token) bytes."
docker compose up -d cloudflared
docker compose ps cloudflared
