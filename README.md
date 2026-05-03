# backend-da1

FastAPI backend for the auction platform.

## Project Structure

```
backend-da1/
├── main.py                     # Entry point
├── app/
│   ├── config.py               # Environment settings
│   ├── dependencies.py         # Shared dependencies (DB, auth)
│   ├── core/                   # Database, security utilities
│   ├── schemas/                # Pydantic models (request/response)
│   ├── api/                    # Route handlers (controllers)
│   ├── services/               # Business logic layer
│   ├── repositories/           # Data access layer
│   └── models/                 # Database models (future ORM)
```

## Quick Start

### 1. Create the virtual environment

```bash
python -m venv .venv
```

#### (python3 si es MacOS/Linux)

### 2. Activate the virtual environment

#### macOS / Linux

```bash
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

#### Windows Command Prompt

```bat
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy and paste the `.env` file in the project root (request the actual values from the project owner):

```env
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

### 5. Start the application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Open the app

- App: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Notes

- The virtual environment is named `.venv` (dot-prefixed, gitignored by default).
- Make sure the virtual environment is active before installing dependencies or running the server.
- If PowerShell blocks script execution, use Command Prompt or run as administrator.
