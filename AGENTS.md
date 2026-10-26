# AGENTS.md: reglas para asistentes de IA en EstateHub Cloud

Este archivo es la base. Como parte de la entrega debes ampliarlo con al menos 3 reglas verificables propias del reto (sección 4) y explicar en `ARCHITECTURE_DECISIONS.md` qué cambió en las respuestas de tu asistente al usarlo.

## 1. Seguridad (no negociable)

1. Ningún endpoint devuelve la entidad `Agent`. Las respuestas usan `AgentPublic`; el catálogo público no expone correos.
2. 401 y 403 no se mezclan:
   - Falta el token, la firma no coincide, expiró, `iss` o `aud` no corresponden, o el agente ya no existe: `AuthenticationError`, HTTP 401.
   - Token válido sin ser dueño ni admin: `ForbiddenOwnerError`, HTTP 403. Toda ruta que modifica o usa un inmueble por id pasa por `_get_owned_property_or_raise`.
3. Secretos solo desde `app.config.settings`. Prohibido escribir llaves, contraseñas u orígenes CORS en el código o en la consola HTML.
4. La consola pinta datos con `textContent`, nunca con `innerHTML`, y no carga scripts externos.
5. Los DTOs de entrada usan `extra="forbid"`; el dueño de un inmueble sale del token, nunca del body.
6. El handler de 422 devuelve solo `loc`, `msg` y `type`.

## 2. Contrato de errores

Todos los errores usan `{"error": {"code": "...", "message": "...", "details": {...}}}`.

## 3. Verificación obligatoria antes de proponer un cambio

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
```

No modifiques `tests/conftest.py`, `tests/test_*.py` ni `.github/workflows/`.

## 4. Reglas del reto (complétalas tú)

<!-- Escribe aquí al menos 3 reglas verificables (comprobables en el código o con un test)
     que tu asistente debe respetar al trabajar en app/login_guard.py:
     llave del contador, de dónde sale el tiempo, qué no puede revelar la respuesta, etc. -->
