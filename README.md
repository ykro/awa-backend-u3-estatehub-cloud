# EstateHub Cloud API (Unidad 3)

API inmobiliaria con autenticación JWT, autorización por propietario (anti-IDOR), protección contra fuerza bruta en el login y despliegue en Google Cloud Run.

## Puesta en marcha

En la raíz de tu repositorio:

```bash
uv sync
cp .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"   # pega el resultado en JWT_SECRET_KEY de .env
uv run uvicorn app.main:app --reload
```

- Consola: `http://127.0.0.1:8000/` (formulario de login vacío). Cuentas de demo locales: `ana@altamira.gt` y `carlos@veranda.gt` (agentes, contraseña `DEMO_AGENT_PASSWORD` de tu `.env`) y `admin@estatehub.gt` (admin, `DEMO_ADMIN_PASSWORD`).
- Swagger: `http://127.0.0.1:8000/docs`.
- Sin `JWT_SECRET_KEY` válido la app no arranca y lo dice. Es intencional (fail-fast).
- Sin `SEED_DEMO_DATA=true` la base arranca vacía. En la nube nunca se siembran usuarios.

El codelab paso a paso, la guía de la unidad y la guía de despliegue en Cloud Run están en el material de la unidad.

## Verificación local

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
```

Estado inicial: `tests/test_demo.py` en verde (2), `tests/test_workshop.py` en rojo (9), `tests/test_challenge.py` en rojo (4) y `tests/student/` en rojo (2 plantillas).

## Mapa del trabajo

| Parte | Dónde | Cuándo |
| :--- | :--- | :--- |
| Taller guiado, paso 1: setup, `.env` y diagnóstico | `.env` | En el taller |
| Taller guiado, paso 2: emitir y verificar JWT | `app/security.py` (`create_access_token`, `decode_access_token`) | En el taller |
| Taller guiado, paso 3: login sin enumeración | `app/repository.py` (`authenticate_and_issue_token`) | En el taller |
| Taller guiado, paso 4: barrera 401 | `app/main.py` (`get_current_agent`) | En el taller |
| Taller guiado, paso 5: guarda de dueño 403 | `app/repository.py` (`_get_owned_property_or_raise`) | En el taller |
| Despliegue guiado | `.github/workflows/deploy.yml`, `DEPLOYMENT.md` | En el taller |
| Reto autónomo | `app/login_guard.py`, `app/main.py` | Tarea |
| Tests propios | `tests/student/test_my_scenarios.py` | Tarea |
| ADR y checklist | `ARCHITECTURE_DECISIONS.md`, `SECURITY_AND_QUALITY.md`, `AGENTS.md` | Tarea |

## Reto autónomo: protección contra fuerza bruta en el login

Hoy cualquiera puede probar millones de contraseñas contra `POST /api/v1/auth/token`. Debes limitar los intentos fallidos por cuenta. El contrato es exacto: los tests públicos y los ocultos lo verifican al pie de la letra.

### Reglas

1. **Llave del contador.** El correo normalizado: sin espacios al inicio o al final y en minúsculas (usa `normalize_email` de `app/security.py`). `" ANA@Altamira.GT"` y `"ana@altamira.gt"` son la misma cuenta.
2. **Qué es un fallo.** Toda respuesta 401 del login: contraseña incorrecta o correo inexistente. Los correos inexistentes se cuentan igual que los existentes y reciben exactamente la misma respuesta (código, cuerpo y cabeceras), para no revelar qué cuentas existen. Un 422 (cuerpo inválido) no es un intento.
3. **Ventana deslizante.** Parámetros: `LOGIN_MAX_ATTEMPTS = 5` y `LOGIN_WINDOW_SECONDS = 900` (ya están en `Settings`). Un fallo registrado en el instante `t` cuenta mientras `ahora - t < 900`; cuando `ahora - t >= 900`, ya no cuenta.
4. **Bloqueo.** Antes de verificar la contraseña: si la cuenta tiene 5 o más fallos vigentes, responde 429 sin verificar credenciales, aunque la contraseña sea correcta. Los intentos 1 a 5 responden 401; el sexto (si los cinco siguen vigentes) responde 429.
5. **Las respuestas 429 no cuentan** como fallo ni extienden el bloqueo.
6. **Fin del bloqueo.** Llega cuando deja de haber 5 fallos vigentes, es decir, cuando el más antiguo de los últimos 5 fallos cumple 900 segundos.
7. **Éxito.** Un login exitoso (posible solo si la cuenta no está bloqueada) borra todos los fallos de esa cuenta.
8. **Independencia.** Bloquear una cuenta no afecta a ninguna otra.
9. **Concurrencia.** Si llegan N intentos simultáneos para la misma cuenta, como máximo 5 llegan a verificar la contraseña; el resto responde 429. Consultar el bloqueo y reservar el intento deben ocurrir en una sola sección crítica, antes de verificar la contraseña.

### Respuesta 429

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 850
Content-Type: application/json

{"error": {"code": "TOO_MANY_ATTEMPTS",
           "message": "<texto en español>",
           "details": {"retry_after_seconds": 850}}}
```

- `Retry-After` es un entero de segundos: el tiempo que falta para que termine el bloqueo, redondeado hacia arriba y nunca menor que 1. Ejemplo: si faltan 849.2 s, responde `850`.
- `details` contiene solo `retry_after_seconds`, con el mismo valor que la cabecera.
- El cuerpo no repite el correo ni la contraseña.

### Restricciones de diseño

- El tiempo sale únicamente de la dependencia `get_clock()` y el limitador de `get_login_guard()` (ambas en `app/login_guard.py`). Los tests las reemplazan para avanzar el reloj sin dormir y para empezar cada test con un limitador limpio. Cualquier `time.time()` o estado global fuera de esas dependencias hará fallar los tests.
- `LoginAttemptGuard(max_attempts=..., window_seconds=...)` debe aceptar esos argumentos con nombre. El resto del diseño es tuyo.
- El estado vive en memoria del proceso. Explica en el ADR por qué eso basta con `--max-instances 1` y qué harías con varias instancias.
- Las peticiones concurrentes llegan en hilos distintos: protege el estado compartido y cumple la regla 9. Los tests ocultos lanzan ráfagas de peticiones simultáneas.

### Tests propios (`tests/student/`)

Escribe al menos 2 tests nuevos (unos 45 minutos). Tus tests propios suman si pasan contra la solución de referencia y detectan mutantes que la suite pública no detecta (errores sembrados en el reto). Reescribir un test público no suma. Un test que no puede fallar no detecta nada. No agregues `conftest.py` en `tests/student/`; para peticiones simultáneas con hilos usa el fixture `file_client`.

### Carga estimada

Reto de 2 a 3 horas, más unos 45 minutos de tests propios y 45 minutos de documentos (ADR, checklist, `AGENTS.md` y `DEPLOYMENT.md`).

## Rúbrica (100 puntos)

| Componente | Puntos | Cómo se mide |
| :--- | ---: | :--- |
| Taller guiado | 20 | `tests/test_workshop.py`, proporcional |
| Reto, tests públicos | 10 | `tests/test_challenge.py`, proporcional |
| Reto, tests ocultos | 25 | tests ocultos con más bordes y datos distintos, proporcional |
| Tests propios | 10 | pasan contra la referencia y detectan mutantes que la suite pública no detecta; los errores sembrados se agrupan por concepto (2 conceptos distintos = completo, 1 = mitad) |
| Despliegue | 10 | `DEPLOYMENT.md` con URL; `GET /health` responde 200 con `"owner"` igual a tu repositorio y `"commit"` en su historial |
| ADR y checklist | 15 | revisión manual: ADR 10, checklist 2, sección propia de `AGENTS.md` 2 y declaración de uso de IA 1 |
| Calidad e integridad | 10 | `ruff check` y `ruff format --check` limpios (5) + sin sospechas de integridad (5) |

La CI de GitHub es retroalimentación, no la nota. El calificador del curso trabaja sobre una copia limpia: los tests oficiales, `conftest.py`, `pyproject.toml` y `uv.lock` salen de su copia, y además corre tests ocultos. Modificar tests oficiales o workflows, agregar `conftest.py` en `tests/student/`, o que `app/` consulte a pytest o lea archivos de `tests/` se reporta como sospecha de integridad.

<!-- texto-escaner:inicio (generado por scripts/texto_escaner.py; no editar a mano) -->

### Qué marca el escáner del calificador

El calificador revisa tu código y tus tests antes de correrlos. Si encuentra algo de esta lista, tu nota queda **retenida** hasta que el docente la revise: no pierdes puntos automáticamente, pero tampoco se publica. Nada de esto hace falta para resolver los retos.

**Por qué existe.** Tus tests corren en la misma máquina que los tests ocultos. Lo que se marca es lo que permitiría leer esos tests, cambiar el resultado de las pruebas o salir a internet desde el calificador.

**En este proyecto (Python).**

- En `app/` puedes importar: `__future__`, `abc`, `app`, `base64`, `bisect`, `collections`, `contextlib`, `copy`, `dataclasses`, `datetime`, `decimal`, `enum`, `fastapi`, `functools`, `google.genai`, `hashlib`, `heapq`, `hmac`, `html`, `itertools`, `json`, `jwt`, `logging`, `math`, `operator`, `os` (solo `os.environ` y `os.getenv`), `pydantic`, `pydantic_settings`, `re`, `secrets`, `sqlalchemy`, `sqlmodel`, `starlette`, `statistics`, `string`, `textwrap`, `threading`, `time`, `typing`, `typing_extensions`, `unicodedata`, `uuid` y `zoneinfo`.
- En `tests/student/` puedes importar: `__future__`, `abc`, `app`, `asyncio`, `base64`, `collections`, `concurrent.futures`, `contextlib`, `copy`, `dataclasses`, `datetime`, `decimal`, `enum`, `fastapi`, `functools`, `hashlib`, `hmac`, `itertools`, `json`, `jwt`, `math`, `operator`, `pydantic`, `pytest`, `random`, `re`, `sqlalchemy`, `sqlmodel`, `starlette`, `statistics`, `string`, `tests`, `textwrap`, `threading`, `time`, `typing`, `unicodedata`, `unittest` (incluido `unittest.mock`), `uuid` y `zoneinfo`.
- Sí puedes: `chr(0x200B)` y cualquier `chr`, unir textos (`"a" + "b"`, f-strings), `vars(objeto)` para comparar (`assert vars(x) == {...}`), `mock.patch("app.…")`, `mock.patch.dict("os.environ", {...})`, `monkeypatch.setenv`, `random` y `functools.singledispatch`.
- Se marca: `eval`, `exec`, `compile`, `open`, `input`, `breakpoint`, `globals`, `locals`, `__import__`, `memoryview`; `vars()` sin argumentos o usado para indexar, recorrer o guardar; `getattr`/`setattr`/`hasattr`/`delattr` con un nombre que no es un texto fijo (salvo sobre `self` o `cls`) o con un nombre prohibido; `operator.attrgetter`/`methodcaller` con nombres calculados o prohibidos; atributos mágicos (`__dict__`, `__globals__`, `__subclasses__`…, salvo `__name__`, `__init__`, `__class__` y `__all__`); acceso a módulos del sistema a través de otro objeto (`.sys`, `.builtins`, `.subprocess`, `.inspect`, `.io`, `.os` fuera de `environ`/`getenv`…); frames (`_getframe`, `f_back`…); procesos y archivos (`system`, `popen`, `fork`, `exec*`, `create_subprocess_exec`, `read_text`, `write_text`, `listdir`, `chdir`, `unlink`…); variables de entorno leídas con un nombre calculado o recorridas (en `app/`); textos, aunque estén armados por partes, que mencionen `pytest`, `junit`, `AWA_`, `site-packages`, `builtins` o atributos mágicos (en `app/`). En tests, además: rutas de módulos no permitidos escritas como texto (`mock.patch("subprocess.run")`, `"_pytest…"`), hooks de pytest (`def pytest_…`), `pytest_plugins`, `request.config.pluginmanager`/`hook`, y los internos de `mock.patch` y `monkeypatch` (`temp_original`, `getter`, `_setattr`); un `conftest.py` propio.

**En todos los proyectos** se marca además: modificar o borrar archivos oficiales, agregar archivos fuera de tus carpetas, enlaces simbólicos, y archivos como `sitecustomize.py`, `pytest.ini`, `init.gradle` o `.npmrc`. Y tus tests deben dar siempre el mismo resultado: un test que falla al azar no cuenta.

<!-- texto-escaner:fin -->

## Endpoints

| Método | Ruta | Protección |
| :--- | :--- | :--- |
| `GET` | `/` | Pública (consola con CSP) |
| `GET` | `/health` | Pública |
| `POST` | `/api/v1/auth/token` | Pública, limitada por cuenta (reto) |
| `GET` | `/api/v1/auth/me` | Bearer JWT |
| `GET` | `/api/v1/agents` | Bearer JWT, solo admin (403 para el resto) |
| `GET` | `/api/v1/properties` | Pública (sin correos) |
| `POST` | `/api/v1/properties` | Bearer JWT (el dueño sale del token) |
| `PATCH` | `/api/v1/properties/{id}/status` | Bearer JWT + dueño o admin |
| `DELETE` | `/api/v1/properties/{id}` | Bearer JWT + dueño o admin |
| `POST` | `/api/v1/properties/{id}/generate-pitch` | Bearer JWT + dueño o admin |
