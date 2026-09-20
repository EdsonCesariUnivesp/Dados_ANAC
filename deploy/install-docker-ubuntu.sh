#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Execute este script com sudo." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  docker.io \
  docker-compose-v2 \
  git

systemctl enable --now docker
usermod -aG docker emoji

docker --version
docker compose version
systemctl --no-pager --full status docker | sed -n '1,12p'

echo "Docker instalado. Abra uma nova sessão SSH para aplicar o grupo docker ao usuário emoji."
