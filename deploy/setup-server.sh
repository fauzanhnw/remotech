#!/usr/bin/env bash
# Remotech — bootstrap server (Ubuntu 24.04). Jalankan SEKALI sebagai root:
#   curl -fsSL https://raw.githubusercontent.com/fauzanhnw/remotech/main/deploy/setup-server.sh -o setup-server.sh
#   sudo bash setup-server.sh
# Setelah selesai, lanjutkan dengan setup-backend.sh.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: jalankan sebagai root (sudo bash setup-server.sh)" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> [1/8] Update sistem"
apt-get update -y
apt-get upgrade -y

echo "==> [2/8] User kerja 'deploy'"
if id deploy &>/dev/null; then
  echo "    user 'deploy' sudah ada, lewati"
else
  read -r -s -p "    Password untuk user 'deploy': " DEPLOY_PASS
  echo
  adduser --gecos "" --disabled-password deploy
  echo "deploy:${DEPLOY_PASS}" | chpasswd
  unset DEPLOY_PASS
fi
usermod -aG sudo deploy
# Ubuntu membuat home 750; Nginx (www-data) perlu traverse untuk menyajikan
# /home/deploy/remotech/staticfiles (admin) & media. o+x = masuk saja, tanpa listing.
chmod o+x /home/deploy

echo "==> [3/8] Firewall (ufw)"
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> [4/8] Swap 2 GB (pengaman RAM di VPS 1 GB)"
if [[ -f /swapfile ]]; then
  echo "    /swapfile sudah ada, lewati"
else
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> [5/8] Install paket (nginx, postgresql, python3.12, git)"
apt-get install -y nginx postgresql postgresql-contrib python3.12 python3.12-venv python3-pip git

echo "==> [6/8] Database PostgreSQL"
read -r -s -p "    Password untuk DB user 'remotech_user': " DB_PASS
echo
PSQL="sudo -u postgres psql -v ON_ERROR_STOP=1"
DB_EXISTS=$($PSQL -tAc "SELECT 1 FROM pg_database WHERE datname='remotech'" || true)
if [[ "$DB_EXISTS" == "1" ]]; then
  echo "    database 'remotech' sudah ada, lewati pembuatan"
else
  $PSQL <<EOSQL
CREATE DATABASE remotech;
CREATE USER remotech_user WITH PASSWORD '${DB_PASS}';
ALTER ROLE remotech_user SET client_encoding TO 'utf8';
ALTER ROLE remotech_user SET default_transaction_isolation TO 'read committed';
-- PostgreSQL 15+: schema 'public' hanya bisa ditulis owner database.
ALTER DATABASE remotech OWNER TO remotech_user;
GRANT ALL PRIVILEGES ON DATABASE remotech TO remotech_user;
EOSQL
fi

# Disimpan untuk dipakai setup-backend.sh (hanya root yang bisa baca).
install -m 600 /dev/null /root/.remotech-setup
{
  echo "DB_NAME=remotech"
  echo "DB_USER=remotech_user"
  echo "DB_PASSWORD=${DB_PASS}"
  echo "DB_HOST=localhost"
  echo "DB_PORT=5432"
} > /root/.remotech-setup
unset DB_PASS
echo "    kredensial DB disimpan di /root/.remotech-setup"

echo "==> [7/8] Tuning PostgreSQL untuk RAM 1 GB"
PG_VER=$(ls /etc/postgresql | sort -V | tail -1)
TUNING_DIR="/etc/postgresql/${PG_VER}/main/conf.d"
mkdir -p "${TUNING_DIR}"
cat > "${TUNING_DIR}/tuning.conf" <<'EOF'
shared_buffers = 128MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 256MB
EOF
systemctl restart postgresql

echo "==> [8/8] Selesai"
echo
echo "Server siap. Langkah berikutnya:"
echo "  1. Pastikan repo main sudah di-push ke GitHub"
echo "  2. Jalankan backend setup:"
echo "       curl -fsSL https://raw.githubusercontent.com/fauzanhnw/remotech/main/deploy/setup-backend.sh -o setup-backend.sh"
echo "       sudo bash setup-backend.sh"
