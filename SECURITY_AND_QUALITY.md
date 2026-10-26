# SECURITY_AND_QUALITY.md (Unidad 3)

Marca cada casilla solo si lo verificaste en tu código y escribe en una línea cómo lo comprobaste (test, comando o archivo).

## Autenticación y secretos

- [ ] La app no arranca sin `JWT_SECRET_KEY` o con un valor de ejemplo. Evidencia:
- [ ] El token incluye y se valida con `exp`, `iss` y `aud`; `sub` es el id del agente. Evidencia:
- [ ] Un token firmado con el viejo secreto público devuelve 401. Evidencia:
- [ ] No hay contraseñas ni secretos en el repositorio, en la consola ni en la configuración de la nube. Evidencia:

## Autorización

- [ ] PATCH, DELETE y generate-pitch devuelven 403 a quien no es dueño ni admin. Evidencia:
- [ ] El dueño de un inmueble nuevo sale del token y el body no puede traer `owner_agent_id`. Evidencia:

## Login y fuerza bruta

- [ ] Un correo inexistente recibe la misma respuesta y el mismo costo que una contraseña incorrecta. Evidencia:
- [ ] Tras 5 fallos en 900 s la cuenta responde 429 con `Retry-After`, incluso con la contraseña correcta. Evidencia:
- [ ] Cambiar mayúsculas o espacios del correo no evade el bloqueo. Evidencia:
- [ ] Con 40 intentos simultáneos para la misma cuenta, como máximo 5 verifican la contraseña (test con hilos propio o explicación de la sección crítica). Evidencia:

## Superficie web

- [ ] La consola usa `textContent` y CSP con nonce; un título con HTML se muestra como texto. Evidencia:
- [ ] Los errores 422 no repiten la contraseña. Evidencia:
- [ ] CORS en producción no incluye `http://localhost:3000` ni `*`. Evidencia:

## Calidad y despliegue

- [ ] `ruff check`, `ruff format --check` y `pytest` pasan en local. Evidencia:
- [ ] `DEPLOYMENT.md` tiene la URL y `/health` devuelve mi repositorio en `owner` y el commit desplegado en `commit`. Evidencia:
