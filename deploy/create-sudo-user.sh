#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

if [[ ${EUID} -ne 0 ]]; then
  echo "Execute este script como root: sudo $0" >&2
  exit 1
fi

read -r -p "Nome do novo usuário: " username

if [[ ! ${username} =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]; then
  echo "Nome inválido. Use letras minúsculas, números, _ ou -, com até 32 caracteres." >&2
  exit 1
fi

if getent passwd "${username}" >/dev/null; then
  echo "O usuário '${username}' já existe. Nenhuma alteração foi feita." >&2
  exit 1
fi

read -r -s -p "Senha do novo usuário: " password
echo
read -r -s -p "Confirme a senha: " password_confirmation
echo

if [[ -z ${password} ]]; then
  echo "A senha não pode estar vazia." >&2
  exit 1
fi

if [[ ${password} != "${password_confirmation}" ]]; then
  echo "As senhas não coincidem." >&2
  exit 1
fi

read -r -p "Chave pública SSH completa: " ssh_public_key

if [[ ! ${ssh_public_key} =~ ^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh.com)[[:space:]][A-Za-z0-9+/=]+([[:space:]].*)?$ ]]; then
  echo "Formato de chave pública SSH inválido." >&2
  exit 1
fi

useradd --create-home --shell /bin/bash --user-group "${username}"
printf '%s:%s\n' "${username}" "${password}" | chpasswd
unset password password_confirmation

home_directory=$(getent passwd "${username}" | cut -d: -f6)
install -d -m 700 -o "${username}" -g "${username}" "${home_directory}/.ssh"
printf '%s\n' "${ssh_public_key}" > "${home_directory}/.ssh/authorized_keys"
chown "${username}:${username}" "${home_directory}/.ssh/authorized_keys"
chmod 600 "${home_directory}/.ssh/authorized_keys"

usermod --append --groups sudo "${username}"
visudo --check >/dev/null

echo
echo "Usuário criado com sucesso."
id "${username}"
echo "Home: ${home_directory}"
stat -c 'Permissões %a — %U:%G — %n' \
  "${home_directory}" \
  "${home_directory}/.ssh" \
  "${home_directory}/.ssh/authorized_keys"
echo "O sudo continuará exigindo a senha do usuário."
