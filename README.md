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

Arsitektur: Nginx menyajikan frontend (React) di domain utama dan mem-proxy API Django (Gunicorn) di subdomain `api.`, dengan PostgreSQL lokal. Script bootstrap ada di folder [`deploy/`](deploy/).

### 1. Setup server + backend (sekali jalan di VPS)

```bash
# sebagai root
curl -fsSL https://raw.githubusercontent.com/fauzanhnw/remotech/main/deploy/setup-server.sh -o setup-server.sh
sudo bash setup-server.sh

curl -fsSL https://raw.githubusercontent.com/fauzanhnw/remotech/main/deploy/setup-backend.sh -o setup-backend.sh
sudo bash setup-backend.sh
```

`setup-server.sh`: swap, firewall, paket, database PostgreSQL + tuning.
`setup-backend.sh`: clone repo `main`, venv, `config/.env` (interaktif), migrate, superuser, service Gunicorn.

> Prasyarat: push branch `main` ke GitHub sebelum `setup-backend.sh` (script clone dari sana).

### 2. Deploy frontend (dari PC)

```powershell
# set remotech-web/.env: VITE_API_BASE_URL=https://api.<domain>, VITE_MIDTRANS_CLIENT_KEY=...
.\deploy\upload-frontend.ps1 -VpsIp <ip-vps>
```

Lalu di VPS:
```bash
sudo mkdir -p /var/www/remotech
sudo cp -r /tmp/dist/* /var/www/remotech/
sudo chown -R deploy:www-data /var/www/remotech
sudo chmod -R o+rX /var/www/remotech
```

### 3. Nginx, DNS, dan SSL

- DNS: A record `@` dan `api` → IP VPS
- Nginx:
  ```bash
  sudo cp /home/deploy/remotech/deploy/nginx.conf /etc/nginx/sites-available/remotech
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo ln -s /etc/nginx/sites-available/remotech /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx
  ```
- SSL: `sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx -d <domain> -d www.<domain> -d api.<domain>`
- Referensi `.env` produksi: [`deploy/env.production.example`](deploy/env.production.example)

### Update deploy

```bash
# di VPS
cd /home/deploy/remotech && sudo -u deploy git pull
sudo -u deploy venv/bin/pip install -r requirements.txt
sudo -u deploy venv/bin/python manage.py migrate --noinput
sudo systemctl restart remotech
# frontend: build & upload ulang (langkah 2)
```
