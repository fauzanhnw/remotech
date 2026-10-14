#!/usr/bin/env bash
# Remotech — deploy backend (Django + Gunicorn). Jalankan SEKALI sebagai root,
# setelah setup-server.sh selesai:
#   curl -fsSL https://raw.githubusercontent.com/fauzanhnw/remotech/main/deploy/setup-backend.sh -o setup-backend.sh
#   sudo bash setup-backend.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: jalankan sebagai root (sudo bash setup-backend.sh)" >&2
  exit 1
fi

APP_DIR="/home/deploy/remotech"
REPO_URL_DEFAULT="https://github.com/fauzanhnw/remotech.git"
SETUP_FILE="/root/.remotech-setup"
SERVICE_SRC="${APP_DIR}/deploy/remotech.service"

echo "==> [1/8] Kredensial database"
DB_NAME="remotech"
DB_USER="remotech_user"
DB_PASSWORD=""
DB_HOST="localhost"
DB_PORT="5432"
if [[ -f "${SETUP_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${SETUP_FILE}"
  echo "    dibaca dari ${SETUP_FILE}"
else
  echo "    ${SETUP_FILE} tidak ditemukan — isi manual"
  read -r -p "    DB_NAME [remotech]: " v; DB_NAME="${v:-remotech}"
  read -r -p "    DB_USER [remotech_user]: " v; DB_USER="${v:-remotech_user}"
  read -r -s -p "    DB_PASSWORD: " DB_PASSWORD; echo
  read -r -p "    DB_HOST [localhost]: " v; DB_HOST="${v:-localhost}"
  read -r -p "    DB_PORT [5432]: " v; DB_PORT="${v:-5432}"
fi

echo "==> [2/8] Cek repository GitHub"
read -r -p "    URL repo [${REPO_URL_DEFAULT}]: " REPO_URL
REPO_URL="${REPO_URL:-${REPO_URL_DEFAULT}}"
if ! git ls-remote --heads "${REPO_URL}" main >/dev/null 2>&1; then
  echo "    WARNING: tidak bisa membaca branch 'main' dari ${REPO_URL}." >&2
  echo "    Pastikan sudah commit & push ke GitHub, lalu jalankan ulang script ini." >&2
  exit 1
fi

echo "==> [3/8] Clone repo (branch main) ke ${APP_DIR}"
if [[ -d "${APP_DIR}/.git" ]]; then
  echo "    repo sudah ada — git pull"
  sudo -u deploy git -C "${APP_DIR}" pull --ff-only
else
  sudo -u deploy git clone --branch main "${REPO_URL}" "${APP_DIR}"
fi

echo "==> [4/8] Virtual environment + install dependensi"
if [[ ! -d "${APP_DIR}/venv" ]]; then
  sudo -u deploy python3.12 -m venv "${APP_DIR}/venv"
fi
sudo -u deploy "${APP_DIR}/venv/bin/pip" install --quiet --upgrade pip
sudo -u deploy "${APP_DIR}/venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"
# Gunicorn wajib ada sebagai binary di venv (server.wsgi dijalankan lewat ini).
# Pip kadang gagal diam-diam (jaringan dsb.) — pasang ulang bila belum ada.
if [[ ! -x "${APP_DIR}/venv/bin/gunicorn" ]]; then
  echo "    gunicorn tidak ditemukan di venv — install ulang"
  sudo -u deploy "${APP_DIR}/venv/bin/pip" install gunicorn
fi
if [[ ! -x "${APP_DIR}/venv/bin/gunicorn" ]]; then
  echo "    ERROR: venv/bin/gunicorn tetap tidak ada. Cek koneksi jaringan VPS, lalu jalankan ulang script." >&2
  exit 1
fi

echo "==> [5/8] Konfigurasi config/.env"
ENV_FILE="${APP_DIR}/config/.env"
if [[ -f "${ENV_FILE}" ]]; then
  echo "    ${ENV_FILE} sudah ada — TIDAK ditimpa. Hapus manual bila ingin regenerate."
else
  SECRET_KEY=$(sudo -u deploy "${APP_DIR}/venv/bin/python" -c "import secrets; print(secrets.token_urlsafe(50))")

  read -r -p "    Domain frontend (FE_URL) [https://remotech.web.id]: " FE_URL
  FE_URL="${FE_URL:-https://remotech.web.id}"
  read -r -p "    Domain API (BASE_URL) [https://api.remotech.web.id]: " BASE_URL
  BASE_URL="${BASE_URL:-https://api.remotech.web.id}"
  API_HOST=$(echo "${BASE_URL}" | sed -E 's#^https?://##; s#/.*##')

  echo "    --- Email (SMTP Resend; kosongkan semua bila belum siap) ---"
  read -r -p "    EMAIL_HOST [smtp.resend.com]: " EMAIL_HOST
  EMAIL_HOST="${EMAIL_HOST:-smtp.resend.com}"
  read -r -p "    EMAIL_PORT [465]: " EMAIL_PORT
  EMAIL_PORT="${EMAIL_PORT:-465}"
  read -r -p "    EMAIL_HOST_USER [resend]: " EMAIL_HOST_USER
  EMAIL_HOST_USER="${EMAIL_HOST_USER:-resend}"
  read -r -s -p "    EMAIL_HOST_PASSWORD: " EMAIL_HOST_PASSWORD; echo
  read -r -p "    DEFAULT_FROM_EMAIL [noreply@remotech.web.id]: " DEFAULT_FROM_EMAIL
  DEFAULT_FROM_EMAIL="${DEFAULT_FROM_EMAIL:-noreply@remotech.web.id}"

  echo "    --- Midtrans (sandbox; boleh dikosongkan, isi nanti di ${ENV_FILE}) ---"
  read -r -p "    MIDTRANS_SERVER_KEY: " MIDTRANS_SERVER_KEY
  read -r -p "    MIDTRANS_CLIENT_KEY: " MIDTRANS_CLIENT_KEY

  mkdir -p "${APP_DIR}/config"
  install -m 600 /dev/null "${ENV_FILE}"
  {
    echo "SECRET_KEY=${SECRET_KEY}"
    echo "DEBUG=false"
    echo "ALLOWED_HOSTS=${API_HOST}"
    echo
    echo "DB_NAME=${DB_NAME}"
    echo "DB_USER=${DB_USER}"
    echo "DB_PASSWORD=${DB_PASSWORD}"
    echo "DB_HOST=${DB_HOST}"
    echo "DB_PORT=${DB_PORT}"
    echo
    echo "EMAIL_HOST=${EMAIL_HOST}"
    echo "EMAIL_PORT=${EMAIL_PORT}"
    echo "EMAIL_USE_TLS=false"
    echo "EMAIL_USE_SSL=true"
    echo "EMAIL_HOST_USER=${EMAIL_HOST_USER}"
    echo "EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}"
    echo "DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL}"
    echo
    echo "BASE_URL=${BASE_URL}"
    echo "FE_URL=${FE_URL}"
    echo
    echo "MIDTRANS_SERVER_KEY=${MIDTRANS_SERVER_KEY}"
    echo "MIDTRANS_CLIENT_KEY=${MIDTRANS_CLIENT_KEY}"
    echo "MIDTRANS_IS_PRODUCTION=false"
    echo
    echo "CORS_ALLOWED_ORIGINS=${FE_URL}"
  } > "${ENV_FILE}"
  chown deploy:deploy "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "    ${ENV_FILE} dibuat"
fi

echo "==> [6/8] Migrate + collectstatic + superuser"
VENV_PY="${APP_DIR}/venv/bin/python"
sudo -u deploy "${VENV_PY}" "${APP_DIR}/manage.py" migrate --noinput
sudo -u deploy "${VENV_PY}" "${APP_DIR}/manage.py" collectstatic --noinput
read -r -p "    Buat superuser admin sekarang? [Y/n]: " CREATE_SU
if [[ "${CREATE_SU,,}" != "n" ]]; then
  read -r -p "    Username: " SU_USER
  read -r -p "    Email: " SU_EMAIL
  read -r -s -p "    Password: " SU_PASS; echo
  sudo -u deploy \
    DJANGO_SUPERUSER_USERNAME="${SU_USER}" \
    DJANGO_SUPERUSER_EMAIL="${SU_EMAIL}" \
    DJANGO_SUPERUSER_PASSWORD="${SU_PASS}" \
    "${VENV_PY}" "${APP_DIR}/manage.py" createsuperuser --noinput
  unset SU_PASS
fi

echo "==> [7/8] Systemd service (Gunicorn)"
cp "${SERVICE_SRC}" /etc/systemd/system/remotech.service
chmod 644 /etc/systemd/system/remotech.service
systemctl daemon-reload
systemctl enable remotech
systemctl restart remotech
sleep 2
if systemctl is-active --quiet remotech; then
  echo "    remotech.service: active (running)"
else
  echo "    ERROR: remotech.service gagal start. Log:" >&2
  journalctl -u remotech -n 20 --no-pager >&2 || true
  exit 1
fi

echo "==> [8/8] Selesai"
echo
echo "Backend hidup di 127.0.0.1:8000. Langkah sisa:"
echo "  1. DNS: A record '@' dan 'api' → IP VPS (panel Domainesia)"
echo "  2. Upload frontend dari PC (deploy/upload-frontend.ps1), lalu di VPS:"
echo "       sudo mkdir -p /var/www/remotech"
echo "       sudo cp -r /tmp/dist/* /var/www/remotech/"
echo "       sudo chown -R deploy:www-data /var/www/remotech"
echo "       sudo chmod -R o+rX /var/www/remotech"
echo "  3. Nginx:"
echo "       sudo cp ${APP_DIR}/deploy/nginx.conf /etc/nginx/sites-available/remotech"
echo "       sudo rm -f /etc/nginx/sites-enabled/default"
echo "       sudo ln -s /etc/nginx/sites-available/remotech /etc/nginx/sites-enabled/"
echo "       sudo nginx -t && sudo systemctl reload nginx"
echo "  4. SSL:"
echo "       sudo apt install -y certbot python3-certbot-nginx"
echo "       sudo certbot --nginx -d remotech.web.id -d www.remotech.web.id -d api.remotech.web.id"
echo "  5. Verifikasi: https://remotech.web.id dan https://api.remotech.web.id/admin/"
