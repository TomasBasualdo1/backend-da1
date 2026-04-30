# backend-da1

## Running FastAPI Locally

### 1. Create the virtual environment

```bash
python -m venv venv
```

```macos
python3 -m venv venv
```

### 2. Activate the virtual environment

**macOS**

```bash
source venv/bin/activate
```

**Windows**

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

If a `requirements.txt` file exists:

```bash
pip install -r requirements.txt
```

If it does not exist, install the basic FastAPI packages:

```bash
pip install fastapi uvicorn
```

### 4. Start the application

```bash
uvicorn main:app --reload
```

### 5. Open in the browser

Open:

```text
http://127.0.0.1:8000
```

Automatic documentation:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
