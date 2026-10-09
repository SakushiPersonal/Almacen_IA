# Proyecto: Almacén IA — Plan de trabajo para Claude Code

Backend FastAPI con agente RAG para minimarkets y retail pequeño.
Proyecto de aprendizaje de 4 semanas. El objetivo no es tener el código listo rápido:
es que yo (el desarrollador) entienda cada pieza y acumule roturas resueltas.

---

## CÓMO DEBES TRABAJAR CONMIGO (lee esto antes de cada sesión)

Esto es lo más importante del archivo. Si lo ignoras, el proyecto pierde su propósito.

**Reglas duras:**

1. **No escribas código de producción sin que yo lo pida explícitamente, archivo por archivo.**
   Por defecto: explica el enfoque, muéstrame la firma o el esqueleto, y déjame escribir el cuerpo.
2. **Antes de que yo ejecute algo, pregúntame qué espero que pase.** Literalmente:
   "¿qué esperas que devuelva esto?". Si no sé responder, significa que estoy copiando.
   Páralo ahí y explícame hasta que pueda predecir.
3. **Cuando algo se rompa, no lo arregles de inmediato.** Primero pregúntame:
   "¿qué esperabas y qué obtuviste?". Si no formulo la frase, no avanzamos. Luego ayúdame
   a convertirlo en preguntas que yo pueda responder en menos de 20 minutos.
4. **Cuando generes código, pídeme que prediga qué hace antes de que lo lea.**
5. **Mete errores a propósito cuando te lo pida** (sección "Retos" de cada hito) y pregúntame
   cómo debería fallar antes de correrlo.
6. **Al final de cada sesión**, recuérdame actualizar `breaks.md` y proponme las entradas
   según lo que se rompió, pero con mis palabras, no las tuyas.
7. **Si me ves aceptando algo sin entenderlo, dímelo.** Frases como "da igual por qué funciona"
   o "después lo veo" son deuda. Nómbralas.

**Qué sí puedes hacer sin fricción:** configuración y boilerplate (docker-compose, CI,
linters, estructura de carpetas), explicaciones, diagramas, revisión de mi código,
generación de datos de prueba y dudas de documentación.

**Idioma:** conversación en español. Código, commits, README y docstrings en inglés.

---

## STACK FIJO

| Capa | Herramienta |
| --- | --- |
| API | FastAPI + Pydantic v2 |
| DB | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 async + Alembic |
| Tests | pytest + pytest-asyncio + httpx |
| CI | GitHub Actions |
| Contenedores | Docker + docker-compose |
| Deploy | Railway (alternativa: AWS) |
| LLM | SDK directo (semanas 1–3), LangGraph (semana 4) |

No agregues dependencias sin justificarlas en una línea y preguntarme antes.

---

## QUÉ HACE EL PRODUCTO

El dueño de un minimarket carga su catálogo (CSV) y sus documentos (políticas de cambio,
proveedores, horarios, promociones). Luego pregunta en lenguaje natural:

- ¿Qué productos están por vencer esta semana?
- ¿Qué tengo bajo el stock mínimo y a qué proveedor se lo pido?
- ¿Cuál es la política de cambio para productos refrigerados?
- Registra un pedido de 3 cajas de bebidas al proveedor X.
- ¿Cuánto vendí ayer por categoría?

---

## RITUAL DIARIO: `breaks.md`

Archivo en la raíz del repo. Se actualiza todos los días, aunque no se haya roto nada grave.

```markdown
## 2026-10-08 — Endpoint de productos
- Esperaba: la lista con 3 productos
- Obtuve: lista vacía, sin error
- Preguntas: ¿la sesión hace commit? ¿el test usa otra DB?
- Predicción: si quito el fixture de rollback, el test verá los datos
- Resultado: acerté / fallé → qué aprendí
- Decisión: qué cambié y por qué
```

Este archivo es el material de las entrevistas. Debe tener al menos 20 entradas reales
al final del mes.

---

# HITO 1 — Base de producción (días 1–7)

**Objetivo de aprendizaje:** Python intermedio real — async, type hints, pytest.

**Objetivo de producto:** API con auth, productos, stock y ventas, testeada y con CI en verde.

### Días

| Día | Construyo yo | Reto de ruptura |
| --- | --- | --- |
| 1 | Repo, estructura por capas (routers / services / repositories), docker-compose con Postgres, CI que corre pytest | Predecir qué pasa si la API arranca antes que Postgres; comprobarlo y arreglarlo con healthcheck |
| 2 | Modelos SQLAlchemy 2.0 async: Producto, Categoría, Proveedor, Lote con vencimiento. Migraciones Alembic | Cambiar un modelo sin migrar y predecir el error exacto antes de correr |
| 3 | CRUD de productos con Pydantic v2, paginación y filtros por categoría | Borrar el router y reconstruirlo desde un archivo vacío, sin mirar |
| 4 | Importador de catálogo desde CSV: validación, errores por fila, carga masiva | Cargar 10.000 filas; predecir el tiempo antes y luego optimizar |
| 5 | Auth JWT con roles (dueño, empleado) y dependencias de FastAPI | Predecir qué devuelve un token expirado en cada endpoint y escribir los tests que lo prueban |
| 6 | Ventas y movimientos de stock con transacciones; endpoint de productos bajo el mínimo | Lanzar dos ventas simultáneas del último producto; predecir si el stock queda negativo |
| 7 | Buffer: deuda de tests, refactor, repaso de `breaks.md` | Explicar en voz alta, en inglés, el recorrido de un request desde el router hasta la DB |

### Preguntas que debes hacerme en este hito

- ¿Por qué `async def` y no `def` en este endpoint? ¿Qué pasa si llamo código bloqueante dentro?
- ¿Qué hay exactamente dentro de la sesión de SQLAlchemy en este punto?
- ¿Qué diferencia hay entre el schema Pydantic y el modelo de la DB, y por qué están separados?

### Terminado cuando

- [ ] `docker compose up` levanta API y DB sin pasos manuales
- [ ] Los tests cubren auth, ventas y stock
- [ ] CI en verde en cada push
- [ ] Al menos 5 entradas en `breaks.md`

---

# HITO 2 — RAG desde cero con SDK directo (días 8–14)

**Objetivo de aprendizaje:** entender cada pieza del pipeline RAG sin frameworks.

**Objetivo de producto:** la API responde preguntas sobre los documentos del negocio, con citas.

### Días

| Día | Construyo yo | Reto de ruptura |
| --- | --- | --- |
| 8 | Extensión pgvector, tabla de chunks, endpoint para subir PDF y texto | Antes de guardar, predecir cuántos chunks saldrán de un PDF de 5 páginas |
| 9 | Chunking con solapamiento; embeddings en background tasks | Subir un documento de 200 páginas; predecir si el request se bloquea |
| 10 | Retrieval por similitud con filtro por negocio (multi-tenant) | Antes de cada búsqueda, anotar qué fragmento espero que salga primero |
| 11 | Endpoint `/ask`: prompt con contexto, respuesta con citas, streaming | Preguntar algo que no está en los documentos; predecir si inventa, y corregirlo |
| 12 | Set de evaluación: 20 preguntas reales con respuesta esperada + script que mide aciertos | Cambiar el tamaño de chunk; predecir cuánto sube o baja el puntaje |
| 13 | Tests con el LLM mockeado; costo y latencia registrados por consulta | Medir cuánto cuesta responder 100 preguntas; predecirlo primero |
| 14 | Buffer y repaso de `breaks.md` | Explicar RAG a alguien no técnico; donde acelere o repita la documentación, hay un hueco |

### Preguntas que debes hacerme en este hito

- ¿Qué es un embedding, en tus palabras, sin usar la frase "vector semántico"?
- ¿Por qué importa el solapamiento entre chunks? ¿Qué se rompe sin él?
- ¿Qué índice usa pgvector aquí y qué pasa si no creo ninguno?

### Terminado cuando

- [ ] El set de evaluación pasa al menos 16 de 20
- [ ] Toda respuesta trae citas al documento de origen
- [ ] Los tests corren sin llamar al LLM real
- [ ] Al menos 10 entradas acumuladas en `breaks.md`

---

# HITO 3 — Agente con herramientas y deploy (días 15–21)

**Objetivo de aprendizaje:** tool calling, manejo de fallos del LLM y operación real.

**Objetivo de producto:** agente desplegado y usado por un negocio real.

### Herramientas del agente

- `buscar_producto` — stock, precio y ubicación
- `productos_por_vencer` — lotes que vencen en N días
- `bajo_stock_minimo` — qué reponer y a qué proveedor
- `registrar_pedido` — pedido a proveedor, con confirmación antes de escribir
- `resumen_ventas` — ventas por día y categoría
- `buscar_documentos` — el RAG del hito 2, como una herramienta más

### Días

| Día | Construyo yo | Reto de ruptura |
| --- | --- | --- |
| 15 | Loop del agente con SDK directo; las 3 herramientas de solo lectura | Antes de cada pregunta, predecir qué herramienta elegirá el modelo y con qué argumentos |
| 16 | Herramientas de escritura con confirmación, validación de argumentos, límite de iteraciones | Hacer que el LLM devuelva argumentos inválidos; la API no debe caerse |
| 17 | Salidas estructuradas, timeouts, reintentos, historial de conversación en la DB | Cortar la red a mitad de una respuesta; predecir qué ve el usuario |
| 18 | Deploy en Railway: Postgres gestionado, secretos, migraciones en el pipeline | Documentar el primer "en local funciona y en producción no" |
| 19 | CI/CD completo: tests, build de imagen, deploy automático en push a main | Romper un test a propósito y verificar que el deploy se bloquea |
| 20 | Interfaz mínima para el usuario real (bot de Telegram o página de chat simple) | Pedir al usuario 10 preguntas sin mi ayuda; cada fallo va a `breaks.md` |
| 21 | Buffer: arreglar lo que el usuario rompió | Elegir el peor bug de la semana y escribir su historia completa |

### Preguntas que debes hacerme en este hito

- ¿Qué pasa si el modelo llama la misma herramienta en bucle? ¿Dónde está el corte?
- ¿Qué parte de esto es determinista y qué parte depende del modelo?
- Si el pedido se registra dos veces, ¿dónde estuvo el fallo?

### Terminado cuando

- [ ] URL pública que responde
- [ ] Deploy automático desde main
- [ ] Un negocio real lo usó al menos una vez
- [ ] Al menos 15 entradas acumuladas en `breaks.md`

---

# HITO 4 — LangGraph, pulido y entrevistas (días 22–28)

**Objetivo de aprendizaje:** comparar enfoques con criterio propio y saber defender el proyecto.

**Objetivo de producto:** repo presentable en inglés y postulaciones enviadas.

### Días

| Día | Construyo yo | Reto de ruptura |
| --- | --- | --- |
| 22 | Reescribir el agente con LangGraph, detrás de un feature flag | Antes de migrar, predecir qué comportamiento cambiará; comprobar con el set de evaluación |
| 23 | Comparar ambas versiones: aciertos, latencia, costo, complejidad. Decidir cuál queda | Escribir la decisión como ADR corto: contexto, opciones, por qué |
| 24 | Observabilidad: logs estructurados, trazas por consulta, costo por negocio, rate limiting | Simular 50 usuarios simultáneos; predecir dónde se rompe primero |
| 25 | README en inglés: diagrama de arquitectura, cómo correrlo, decisiones, lecciones de `breaks.md` | Explicar el proyecto en 2 minutos en inglés, grabándome |
| 26 | CV y LinkedIn con el proyecto al centro; 5 postulaciones personalizadas | Por cada oferta, anotar qué parte del proyecto responde a sus requisitos |
| 27 | Simulacro: revisar código generado por IA con errores escondidos, en voz alta y en inglés | Antes de leer cada bloque, predecir qué hace; contar cuántos errores encontré |
| 28 | Simulacro de entrevista: "worst bug", "why did you build it", "what would you change". Plan del mes 2 | Responder solo desde `breaks.md`, sin inventar |

### Lo que debes hacer tú en los días 27 y 28

- Día 27: genera 3 fragmentos de código plausibles con errores sutiles (N+1, race condition,
  excepción que traga el error, fuga de contexto entre tenants). No me digas cuántos errores
  hay ni dónde. Yo los busco en voz alta.
- Día 28: entrevístame en inglés. Preguntas de juicio, no de memoria. Sé exigente con las
  respuestas vagas y pídeme el caso concreto.

### Terminado cuando

- [ ] Repo público con README en inglés y diagrama de arquitectura
- [ ] ADR comparando SDK directo vs LangGraph
- [ ] Pitch de 2 minutos grabado
- [ ] Primeras postulaciones enviadas
- [ ] Al menos 20 entradas en `breaks.md`

---

## ARRANQUE

Primera sesión: empieza por el día 1 del Hito 1. Antes de escribir nada, pregúntame cómo
creo que debería estructurarse el proyecto y por qué. Después compara con tu propuesta
y discutimos las diferencias.
