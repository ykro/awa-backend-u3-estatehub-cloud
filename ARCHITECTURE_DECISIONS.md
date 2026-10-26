# ARCHITECTURE_DECISIONS.md (Unidad 3)

Responde cada pregunta con tus palabras, en 3 a 8 líneas, citando archivos o funciones de tu código. Se califica con criterio técnico, no con extensión.

## ADR-1: Dónde vive cada barrera de seguridad

**Pregunta.** ¿Por qué la verificación del token (401) vive en `get_current_agent` y la verificación de dueño (403) vive en el repositorio? ¿Qué pasaría si una ruta nueva olvidara llamar a `_get_owned_property_or_raise`? ¿Cómo lo detectaría un test?

**Respuesta.**

## ADR-2: Diseño del limitador de intentos

**Pregunta.** Describe tu estructura de datos y por qué elegiste una ventana deslizante. ¿Qué complejidad tiene cada login? ¿Cómo evitas que un atacante que prueba un millón de correos distintos agote la memoria del proceso?

**Respuesta.**

## ADR-3: Estado en memoria y número de instancias

**Pregunta.** Tu limitador guarda el estado en memoria. ¿Por qué funciona con `--max-instances 1` y qué ocurre con 3 instancias? Propón una alternativa concreta (por ejemplo Redis, Firestore o Cloud Armor) y su costo o desventaja.

**Respuesta.**

## ADR-4: Enumeración de cuentas

**Pregunta.** ¿Cómo garantiza tu implementación que un atacante no pueda distinguir un correo existente de uno inexistente, ni por el cuerpo, ni por las cabeceras, ni por el tiempo de respuesta? ¿Qué parte del taller ayuda y qué parte agregaste tú?

**Respuesta.**

## ADR-5: Tokens sin revocación

**Pregunta.** Si un token de Ana se filtra, ¿cuánto tiempo puede usarlo un atacante en esta API? Propón un mecanismo para revocarlo y explica qué perdemos al implementarlo.

**Respuesta.**

## ADR-6: AGENTS.md y uso de IA

**Pregunta.** ¿Qué reglas agregaste a la sección 4 de `AGENTS.md`? Se esperan al menos 3 reglas verificables (que un revisor pueda comprobar en el código o con un test, no consejos genéricos). Describe una respuesta concreta de tu asistente antes y después de agregarlas.

**Respuesta.**

## ADR-7: Concurrencia y precio del bloqueo por cuenta

**Pregunta.** Explica cómo garantizas que 40 intentos simultáneos para la misma cuenta no verifiquen más de 5 contraseñas (qué ocurre dentro de tu sección crítica y en qué orden). Luego analiza el precio de tu diseño: un atacante puede bloquear a propósito la cuenta del admin legítimo. Compara con limitar por IP, pedir CAPTCHA o usar espera exponencial, y di qué combinarías en producción.

**Respuesta.**

## Declaración de uso de IA

Marca con una `x` y completa.

- [ ] No usé asistentes de IA.
- [ ] Usé asistentes de IA. Herramientas:
- Partes del código o de los tests en las que intervino la IA:
- Errores de la IA que detecté y corregí (al menos uno, con archivo y explicación):
