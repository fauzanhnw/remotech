# Remotech

**Remote Challenge** — Program dari Remote Circle Community. Sebuah web-based learning system dengan gamification.

Dibangun menggunakan **Django**, **React**, dan **PostgreSQL**.

---

## Persyaratan

- Python >= 3.12
- PostgreSQL
- Poetry (untuk dependency management)

## Instalasi Poetry

```powershell
python -m pip install poetry
```

Pastikan direktori Scripts Python sudah masuk PATH:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User")
poetry --version
```

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
```

## Tech Stack

- **Backend:** Django 6.0
- **Database:** PostgreSQL
- **Frontend:** React *(coming soon)*
- **Dependency Manager:** Poetry
