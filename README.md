
## Pokretanje s Dockerom

Najjednostavnije pokretanje cijelog projekta:

```bash
docker compose up --build
```

Aplikacija se otvara na:

```txt
http://localhost:8000
```

Swagger dokumentacija:

```txt
http://localhost:8000/docs
```

Health check:

```txt
http://localhost:8000/health
```

## Lokalno pokretanje bez app containera

Prvo pokreni samo PostgreSQL bazu:

```bash
docker compose up -d db
```

Zatim napravi virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\activate
```

Linux/macOS/Git Bash:

```bash
source .venv/bin/activate
```

Instaliraj dependencyje:

```bash
pip install -r requirements.txt
```

Na Windows PowerShellu postavi database URL:

```powershell
$env:DATABASE_URL="postgresql+psycopg://termini:termini@localhost:5432/termini_db"
$env:SECRET_KEY="dev-secret-key"
```

Pokreni FastAPI:

```bash
uvicorn app.main:app --reload
```

## Testovi

Ako testove pokrećeš lokalno, neka PostgreSQL baza radi:

```bash
docker compose up -d db
```

Zatim:

```bash
pytest
```

## Lint i format

```bash
ruff check .
black --check .
```

Za automatsko formatiranje:

```bash
black .
```

## Trenutni skeleton endpointi

System:

- `GET /health`

Auth:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Termini:

- `GET /termini`
- `GET /termini/{termin_id}`
- `POST /termini`
- `PUT /termini/{termin_id}`
- `DELETE /termini/{termin_id}`

Prijave:

- `POST /termini/{termin_id}/prijava`
- `DELETE /termini/{termin_id}/prijava`
- `GET /me/prijave`
- `GET /termini/{termin_id}/popunjenost`

