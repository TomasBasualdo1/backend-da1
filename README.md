# backend-da1

FastAPI backend for local development.

## Quick Start

### 1. Create the virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

Use the command that matches your system and shell.

#### macOS / Linux / Git Bash

```bash
source venv/bin/activate
```

#### Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

#### Windows Command Prompt

```bat
venv\Scripts\activate.bat
```

#### Windows Git Bash

```bash
source .venv/Scripts/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Open the app

App URL:

```text
http://127.0.0.1:8000
```

API docs:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Notes

- If PowerShell blocks script execution, run it once as administrator or use Command Prompt instead.
- Make sure the virtual environment is active before installing dependencies or starting the server.
