# 06 · Testing & Validación

## Estado de testing

- Framework: **`unittest`** de la stdlib (no hay `pytest` en `requirements.txt`).
- Los tests **mockean la base de datos** con `MagicMock` y/o usan `app.dependency_overrides` + `fastapi.testclient.TestClient`. **No requieren Postgres real.**
- Cobertura parcial: hay 3 archivos de test, no una suite completa.

| Archivo | Cubre |
|---------|-------|
| `tests/test_usuarios.py` | Endpoints de `/usuarios/me` con `TestClient` + override de `get_db`/`get_current_user`. |
| `tests/test_flow_articulo_producto.py` | Flujo consignación: `create_article` + `evaluate_article` con DB mockeada. |
| `tests/test_email.py` | `EmailService`. |

## Cómo correr los tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
# o un archivo puntual:
python -m unittest tests.test_usuarios -v
```

> No hay `pytest.ini`, `conftest.py` ni config de coverage. Si querés usar `pytest`, instalalo aparte; los tests `unittest` corren igual bajo pytest.

## Lint / formato

- No hay linter/formatter configurado para Python en el repo (no hay `ruff`, `flake8`, `black`, `pyproject.toml`).
- Mantené consistencia manual con el archivo vecino.

## Validación manual (lo más útil hoy)

1. Levantá la API (`uvicorn main:app --reload`) y usá **Swagger UI** (`/docs`) para probar endpoints.
2. Flujo de humo recomendado:
   - `POST /auth/registro/paso1` (multipart con 2 fotos) → revisar email/token.
   - `POST /auth/registro/paso2` (token + password).
   - `POST /auth/login` → obtener `access_token`.
   - Con Bearer: `GET /usuarios/me`, `GET /subastas`, `POST /subastas/{id}/join`, `POST /subastas/{id}/items/{item_id}/pujar`.
   - Admin (`usuarioId == 12`): `POST /admin/subastas`, `POST /admin/articulos/{id}/evaluar`.
3. Para SSE: conectarse a `GET /subastas/{id}/stream` (curl con `-N`) y pujar desde otra sesión para ver el evento.

## Checklist antes de commitear

- [ ] La API arranca sin error (`uvicorn ...`) — valida `.env` y `config.py`.
- [ ] Los tests existentes pasan (`python -m unittest discover -s tests`).
- [ ] Probé el endpoint afectado en `/docs`.
- [ ] Queries parametrizadas; sin `db.commit()` faltante.
- [ ] No rompí el contrato (Swagger/`schemas.py`); si lo cambié, avisé al frontend.
- [ ] No subí secretos: `.env` está gitignored — verificá no haber hardcodeado claves.
- [ ] Si la feature tiene spec, actualicé `frontend-da1/context/progress-tracker.md`.
