# Remotech

**Remote Challenge** — Program dari Remote Circle Community. Sebuah web-based learning system dengan gamification.

Dibangun menggunakan **Django**, **React**, dan **PostgreSQL**.

---

## Persyaratan

- Python >= 3.12
- PostgreSQL
- Poetry (untuk dependency management)

## Instalasi Poetry (abaikan bila sudah terinstall)
Jalankan di powershell:

```powershell
python -m pip install poetry
```

Atur agar venv berada di dalam project

```powershell
poetry config virtualenvs.in-project true
```
[Panduan lengkap instalasi poetry ](https://python-poetry.org/docs/#installing-with-the-official-installer)

## Instalasi Project

```powershell
# Clone repository
git clone [Repository clone url]
cd remotech

# Install dependencies
poetry install

# Aktifkan virtual environment
poetry shell
```

## Konfigurasi Database

Buat file `config/.env`:

```env
DB_NAME=remotech
DB_USER=postgres
DB_PASSWORD=dev
DB_HOST=localhost
DB_PORT=5342
```

Konfigurasi akan otomatis terbaca dari file tersebut. Jika file atau variabel tidak ditemukan, akan menggunakan nilai default.

Setelah database PostgreSQL sudah siap dan database `remotech` sudah dibuat, jalankan migrasi:

```powershell
python manage.py migrate
```

## Menjalankan Server

```powershell
python manage.py runserver
```

API berjalan di `http://localhost:8000/` (browseble API di `/api/` bila mengikuti konfigurasi URL bawaan).

## Frontend (React)

Frontend React 19 + TypeScript + antd + Vite berada di folder `remotech-web/`:

```powershell
cd remotech-web

# Install dependencies
npm install

# Development server (Vite, default http://localhost:5173)
npm run dev

# Build produksi
npm run build

# Lint
npm run lint
```

## Menjalankan Test

```powershell
# Test backend (Django test runner)
python manage.py test server.apps.remotech

# Lint backend (ruff)
poetry run ruff check .
poetry run ruff format --check .
```

## Pengembangan

```powershell
# Menambah dependency
poetry add <nama-package>

# Menambah dependency (dev)
poetry add --group dev <nama-package>

# Update semua dependency
poetry update

# Ekspor ke requirements.txt
poetry export -f requirements.txt -o requirements.txt
# atau sebagai alternatif
poetry run pip freeze > requirements.txt
```

## Tech Stack

- **Backend:** Django 6.0 + Django REST Framework
- **Database:** PostgreSQL
- **Frontend:** React 19 + TypeScript + Ant Design + Vite
- **Dependency Manager:** Poetry (backend), npm (frontend)
- **Lint:** Ruff (backend), ESLint (frontend)

## Deploy ke VPS (Ubuntu 24.04)

Arsitektur: Nginx menyajikan frontend (React) di domain utama dan mem-proxy API Django (Gunicorn) di subdomain `api.`, dengan PostgreSQL lokal.

### 1. Siapkan server

```bash
apt update && apt upgrade -y
adduser deploy && usermod -aG sudo deploy
apt install ufw nginx postgresql python3.12 python3.12-venv python3-pip git -y
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable

# Swap 2GB (wajib untuk VPS 1GB RAM)
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Buat database PostgreSQL:

```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE remotech;
CREATE USER remotech_user WITH PASSWORD '<password-kuat>';
ALTER ROLE remotech_user SET client_encoding TO 'utf8';
ALTER ROLE remotech_user SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE remotech TO remotech_user;
\q
```

### 2. Deploy backend

```bash
su - deploy
git clone <repo-url> && cd remotech
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Buat config/.env (lihat config/env.example), lalu:
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

Jalankan dengan Gunicorn via systemd — buat `/etc/systemd/system/remotech.service`:

```ini
[Unit]
Description=Remotech Django API
After=network.target postgresql.service

[Service]
User=deploy
Group=www-data
WorkingDirectory=/home/deploy/remotech
ExecStart=/home/deploy/remotech/venv/bin/gunicorn server.wsgi:application --bind 127.0.0.1:8000 --workers 2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now remotech
```

### 3. Deploy frontend

```powershell
cd remotech-web
# .env: VITE_API_BASE_URL=https://api.<domain>, VITE_MIDTRANS_CLIENT_KEY=...
npm run build
scp -r dist/* deploy@<ip-vps>:/tmp/dist/
```

Di VPS:

```bash
sudo mkdir -p /var/www/remotech && sudo cp -r /tmp/dist/* /var/www/remotech/
```

### 4. Nginx, DNS, dan SSL

- A record `@` dan `api` → IP VPS di panel DNS
- Config Nginx: domain utama serve `/var/www/remotech` (fallback `index.html`), subdomain `api` proxy ke `127.0.0.1:8000`, plus alias `/static/` (STATIC_ROOT) dan `/media/` (MEDIA_ROOT)
- SSL: `sudo certbot --nginx -d <domain> -d api.<domain>`
- Production: set `DEBUG=false`, `SECRET_KEY` baru, `ALLOWED_HOSTS=api.<domain>` di `config/.env`, lalu `sudo systemctl restart remotech`
