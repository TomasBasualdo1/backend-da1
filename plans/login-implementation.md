# Plan: Implement Login Function

## Overview
Implement `POST /auth/login` endpoint to authenticate users against Supabase database and return JWT token.

## Database Schema (Actual Supabase Structure)

Based on the provided schema:

**`personas` table** (contains auth credentials):
- `identificador` (PK)
- `documento` (the login username)
- `password_hash` (NOT `password` - this is the column name)
- `email` (unique)
- `nombre`, `apellido`, `direccion`, `estado`, `fotoFrente`, `fotoDorso`

**`clientes` table** (contains auth status fields):
- `identificador` (PK, FK to `personas.identificador`)
- `estadoRegistro` (pendiente/aprobado/rechazado) - DEFAULT 'pendiente'
- `bloqueado` (boolean) - DEFAULT false
- `multaActiva` (boolean) - DEFAULT false
- `admitido` (si/no)
- `categoria` (comun/especial/plata/oro/platino)

**Relationship**: `personas.identificador` = `clientes.identificador`

## Implementation Steps

### 1. Add Pydantic Models to `app/api/auth.py`

```python
from pydantic import BaseModel

class LoginRequest(BaseModel):
    documento: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

### 2. Implement `AuthService.login()` in `app/services/auth_service.py`

```python
from psycopg import Connection
from fastapi import HTTPException, status

class AuthService:
    @staticmethod
    def login(db: Connection, documento: str, password: str):
        """
        Authenticate user with documento and password.
        Returns user data dict or raises HTTPException.
        """
        # Join personas and clientes tables
        query = """
            SELECT 
                p.identificador as usuario_id,
                p.documento,
                p.nombre,
                p.password_hash,
                c.admitido,
                c.categoria,
                c."estadoRegistro",
                c.bloqueado,
                c."multaActiva"
            FROM personas p
            JOIN clientes c ON p.identificador = c.identificador
            WHERE p.documento = %s
        """
        
        with db.cursor() as cursor:
            cursor.execute(query, (documento,))
            user = cursor.fetchone()
        
        # Check if user exists
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password using password_hash column
        from app.core.security import verify_password
        if not verify_password(password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is blocked
        if user.get('bloqueado'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is blocked"
            )
        
        # Check if registration is approved (note camelCase column name)
        if user.get('estadoRegistro') != 'aprobado':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User registration not approved"
            )
        
        # Check if user is admitted
        if user.get('admitido') != 'si':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not admitted"
            )
        
        return {
            'usuario_id': user['usuario_id'],
            'categoria': user['categoria'],
            'admitido': user['admitido']
        }
```

**Important notes**:
- Column name is `password_hash` (not `password`)
- Use quotes for camelCase columns: `"estadoRegistro"`, `"multaActiva"`
- Join is between `personas` and `clientes` on `identificador`

### 3. Implement Login Endpoint in `app/api/auth.py`

Replace the empty `login()` function:

```python
@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Connection = Depends(get_db)):
    # Authenticate user
    user_data = AuthService.login(db, credentials.documento, credentials.password)
    
    # Create JWT token with required claims
    from app.core.security import create_access_token
    token_data = {
        "usuarioId": user_data['usuario_id'],
        "categoria": user_data['categoria'],
        "admitido": user_data['admitido']
    }
    access_token = create_access_token(token_data)
    
    return TokenResponse(access_token=access_token)
```

### 4. Verify Imports in `app/api/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from pydantic import BaseModel

from app.core.security import create_access_token, verify_password
from app.services.auth_service import AuthService
from app.core.database import get_db_connection
```

## Testing

After implementation, test with a user that exists in your Supabase `personas` table:

```bash
# Make sure the user has:
# - password_hash set (hashed with bcrypt)
# - estadoRegistro = 'aprobado'
# - bloqueado = false
# - admitido = 'si'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"documento": "35123456", "password": "MiClaveSecreta123"}'
```

Expected success response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Files to Modify
1. `app/api/auth.py` - Add Pydantic models and endpoint implementation
2. `app/services/auth_service.py` - Add `login()` static method

## Pre-requisites for Testing
Ensure you have a test user with:
- `personas.documento` set
- `personas.password_hash` = bcrypt hash of the password (use `get_password_hash()` from `app/core/security.py`)
- `clientes.estadoRegistro` = 'aprobado'
- `clientes.bloqueado` = false
- `clientes.admitido` = 'si'
