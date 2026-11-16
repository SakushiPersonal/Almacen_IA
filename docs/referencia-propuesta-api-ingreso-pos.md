# Propuesta — API de ingreso, su memoria y el RAG

**Fecha:** 16 de noviembre de 2026 · **Estado:** propuesta, sin implementar ·
**Depende de:** control de lotes (`0046`–`0059`, `docs/diseno-lotes-y-vencimiento.md`)

> Responde dos cosas: **qué campos usa la API** (para que la transcripción desde el emisor sea
> un mapeo, no una traducción) y **dónde vive su memoria** — un Postgres propio o el mismo
> Supabase del POS. La segunda pregunta es la que tiene consecuencias difíciles de revertir, así
> que va primero.

---

## 1. La recomendación, en una página

**Un solo Postgres: el de Supabase. Tres schemas.** No un servidor aparte para la API.

| Schema | Qué guarda | Quién escribe |
|---|---|---|
| `public` | El POS. **Sistema de registro**: stock, lotes, ventas, documentos, métricas derivadas | Sólo las RPC (`registrar_*`). La API NUNCA escribe acá directo |
| `ingesta` | La memoria de la API: el payload crudo de cada documento recibido, su resultado, y el mapeo aprendido de códigos externos | La API |
| `rag` | Corpus de texto y embeddings (`pgvector`) para el copiloto futuro | Un worker de indexación |

Cuatro razones, en orden de peso:

**1. El valor del RAG está en el JOIN con los datos operativos.** Una pregunta útil para este
negocio no es "¿qué dice el catálogo del proveedor?" sino "¿qué me conviene pedirle a este
proveedor, dado mi stock, mis lotes por vencer, mi VDP y su lead time observado?". Si el corpus
vive en otro servidor, cada recuperación se vuelve un join entre bases que hay que hacer **en
código de la API** — que es exactamente de donde este proyecto sacó la lógica de negocio
(`0031` devolvió a SQL la última agregación que vivía en el cliente). Dos servidores la
empujan de vuelta ahí, y encima sin pruebas SQL que la cubran.

**2. El aislamiento multi-tenant ya está resuelto, una vez.** RLS con `current_negocio_id()` es
la columna vertebral de seguridad del sistema: 17 políticas, advisors en cero, verificado con
sesiones autenticadas reales. Un Postgres aparte obliga a **reimplementar el aislamiento para el
RAG**, y una fuga ahí es la peor posible: el contexto de un minimarket contestando la pregunta
de otro, en lenguaje natural y con apariencia de verdad. El criterio del ADR-004 aplica igual —
si la función no recibe el inquilino como parámetro, no hay dónde escribir uno ajeno.

**3. `pgvector` ya está disponible en Supabase.** `create extension vector` y listo. No hay
infraestructura que justificar: la pregunta "¿servidor propio?" normalmente se hace porque falta
una capacidad, y acá no falta.

**4. Operación.** Un segundo Postgres es un segundo respaldo, parche, monitoreo y cadena de
conexión. Para un sistema con un inquilino real es sobrecarga pura.

### Cuándo SÍ correspondería separar, con el umbral declarado

Mismo criterio que `docs/endurecimiento-escalabilidad.md`: un umbral medido, no una intuición.

| Señal | Qué hacer ANTES de separar |
|---|---|
| La caja espera porque una importación masiva está corriendo | Schema aparte (ya propuesto), lotes de inserción acotados y ventana nocturna. Después, réplica de lectura de Supabase. Separar el servidor es el último paso, no el primero |
| El corpus crece a decenas de GB de texto | Mover **sólo** `rag` a su propio servicio vectorial, dejando `ingesta` y `public` juntos. El join operativo sigue siendo local |
| Generar embeddings consume CPU | Eso es un **worker**, no una base de datos. No requiere separar nada |
| El corpus incluye material que no es del inquilino (catálogos de proveedores, listas de precios públicas) | Misma base, `negocio_id is null` = referencia compartida de sólo lectura. Es el patrón que ya usa `feriados` |

### Lo que esto reabre, y necesita un ADR

El RAG implica un LLM, y **"Copiloto y Radar = 100 % por reglas, sin LLM ni APIs externas" es
una decisión cerrada** del proyecto. Esta propuesta no la rompe por su cuenta: la arquitectura de
datos se puede preparar sin encender ningún LLM. Pero encenderlo exige un **ADR-005** que fije,
como mínimo: qué datos salen del país, qué pasa si el proveedor del modelo no responde (el
copiloto por intents debe seguir funcionando solo), y que **ninguna cifra del negocio se genere
con el modelo** — las cifras salen de SQL y el modelo sólo las redacta. Ver §6.

---

## 2. El principio que ordena toda la API

> **La API publica DOCUMENTOS, nunca estado.**

Ningún endpoint escribe `stock_actual`, ni crea un lote, ni inserta un movimiento. El lote es
una *consecuencia* de una recepción, igual que el stock es una consecuencia de un movimiento.
Así la API hereda gratis la atomicidad, la idempotencia, el costeo FEFO y el invariante
`stock_actual = Σ lotes`.

En el momento en que exista una vía para fijar stock sin un documento que lo explique, el libro
mayor deja de explicar el saldo y todo lo construido en `0033`–`0059` —que deriva demanda desde
ese libro— pierde su base. **No hay `PUT /productos/{id}/stock`. No lo va a haber.**

Verbos de escritura, cuatro y nada más: **recepción, venta, conteo, movimiento.** Más uno de
catálogo, que no mueve stock.

### 2.1 Autenticación: clave por negocio que se traduce a un JWT, nunca `service_role`

Esta es la decisión de seguridad más importante de la API y se deduce de todo lo anterior.

- ❌ **`service_role`**: salta RLS por diseño. Cada endpoint tendría que filtrar el inquilino a
  mano, y **un solo `where negocio_id` olvidado entrega los datos de otro negocio**. Es
  precisamente lo que RLS existe para hacer imposible.
- ✅ **Clave de API por negocio → JWT de un usuario de servicio de ese negocio.** RLS sigue
  aplicando sin cambios, `current_negocio_id()` funciona igual que para la app, y las RPC se
  llaman tal cual. El aislamiento lo garantiza la base, no la disciplina del programador.

```sql
create table ingesta.api_keys (
  id          uuid primary key default gen_random_uuid(),
  negocio_id  uuid not null references public.negocios(id) on delete cascade,
  usuario_id  uuid not null references public.usuarios(id),  -- usuario de servicio del negocio
  nombre      text not null,                                 -- "ERP del proveedor X"
  hash        text not null,                                 -- nunca la clave en claro
  scopes      text[] not null default '{}',                  -- 'recepciones:write', 'metricas:read'
  revocada_en timestamptz,
  ultimo_uso  timestamptz,
  created_at  timestamptz not null default now()
);
```

---

## 3. Los campos de escritura

Convenciones comunes a todos los `POST`:

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `idempotency_key` | string (≤64) | **sí** | Clave del emisor. Reenviar devuelve el MISMO documento con `reprocesado: true`, sin mover stock. Sin esto, un reintento por timeout duplica inventario |
| `fecha` | date | no | Fecha del documento según el emisor. Informativa por ahora: las RPC fechan con `now()` (ver §7) |
| `origen` | string | no | Quién lo envía ("erp-proveedor-sur", "planilla-local"). Se guarda en la memoria y sirve para el mapeo aprendido |

### 3.1 Referencia a un producto — el objeto `producto`

Aparece en toda línea de todo documento. El emisor no conoce nuestros uuid.

```json
{ "id": null, "codigo_barras": "7801234567890", "sku": null, "descripcion": "YOG FRUT 150G" }
```

| Campo | Tipo | Nota |
|---|---|---|
| `id` | uuid | Si viene, gana sobre todo. Se valida que sea del inquilino |
| `codigo_barras` | string | Identificador **de fábrica**. Segunda prioridad |
| `sku` | string | Código interno del negocio. Tercera prioridad |
| `descripcion` | string | **No resuelve nada por sí sola.** Se guarda para el mapeo aprendido (§4.2) y para que un humano desambigüe |

La resolución la hace `resolver_producto(jsonb)` (`0059`) **en SQL**, con sus tres tolerancias
—espacios del lector, mayúsculas, el cero inicial de UPC-A contra EAN-13— y su precedencia. La
API no reimplementa esa regla: una segunda copia divergiría, y la prueba `30` ata las dos que ya
existen.

**Producto que no resuelve → el documento falla completo** (HTTP 422, nombrando la línea). Crear
productos como efecto secundario de una recepción es cómodo y deja el catálogo lleno de basura.
El alta va por §3.6.

### 3.2 `POST /v1/recepciones`

El endpoint central: es el que crea los lotes, y por lo tanto el único momento en que la fecha de
vencimiento existe.

```json
{
  "idempotency_key": "rec-2026-11-16-0001",
  "origen": "erp-proveedor-sur",
  "proveedor": { "id": null, "nombre": "Distribuidora Sur", "rut": "76.543.210-K" },
  "items": [
    {
      "producto": { "codigo_barras": "7801234567890" },
      "cantidad": 24,
      "costo_unit": 890,
      "fecha_vencimiento": "2026-12-05",
      "codigo_lote": "L2411A"
    }
  ]
}
```

| Campo del ítem | Tipo | Obligatorio | Columna / parámetro |
|---|---|---|---|
| `producto` | objeto ref | **sí** | → `resolver_producto` → `recepcion_items.producto_id` |
| `cantidad` | number > 0 | **sí** | `recepcion_items.cantidad`, `lotes.cantidad_inicial` |
| `costo_unit` | number ≥ 0 | no | `recepcion_items.costo_unit` y `lotes.costo_unit`. Si falta, el lote hereda `productos.costo` y el costo del producto NO se toca |
| `fecha_vencimiento` | date | **sí si el producto es perecible** | `lotes.fecha_vencimiento`. Si falta y el producto declara `vida_util_dias`, el servidor la estima; si no declara nada, **falla nombrando el producto** |
| `codigo_lote` | string | no | `lotes.codigo_lote`. Informativo: no identifica el lote en el sistema |

**Una línea = un lote.** Dos tandas del mismo producto con vencimientos distintos en la misma
entrega son **dos líneas**. El mapeo JSON → base es directo, sin transformación.

Respuesta `201`:

```json
{
  "documento_id": "…",
  "recepcion_id": "…",
  "reprocesado": false,
  "lotes": [
    { "id": "…", "producto_id": "…", "cantidad": 24,
      "fecha_vencimiento": "2026-12-05", "costo_unit": 890 }
  ]
}
```

### 3.3 `POST /v1/ventas`

Para un POS externo o una caja secundaria que sincroniza.

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `medio_pago` | enum | no (default `efectivo`) | `efectivo · debito · credito · transferencia · otro` |
| `items[].producto` | objeto ref | **sí** | |
| `items[].cantidad` | number > 0 | **sí** | |

⚠ **El precio NO se acepta.** Lo toma el servidor del catálogo, igual que para la caja propia
(`0008`). Un emisor externo que fije el precio puede contaminar el margen y, con él, la
clasificación ABC y la selección por retorno sobre costo. El total también lo calcula el
servidor. El consumo es FEFO y el costo de la línea sale de los lotes consumidos.

### 3.4 `POST /v1/conteos`

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `items[].producto` | objeto ref | **sí** | Máximo 500 por documento, sin repetir producto (frenos de `0025`) |
| `items[].contado` | number ≥ 0 | **sí** | El **esperado lo lee el servidor** con el producto bloqueado: no se acepta del emisor, o la precisión de inventario deja de medir nada |

### 3.5 `POST /v1/movimientos`

Merma y ajuste. Es el único documento que admite apuntar a un lote.

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `producto` | objeto ref | **sí** | |
| `tipo` | enum | **sí** | `merma · ajuste · compra` |
| `cantidad` | number > 0 | **sí** | |
| `signo` | −1 / +1 | sí si `tipo = ajuste` | |
| `motivo` | string | **sí para `ajuste`** | Mismo freno que la interfaz: ajustar stock no puede ser un acto reflejo |
| `lote_id` | uuid | no | Salida: sale de ese lote. Sin lote: FEFO, que para una merma por vencimiento **ya acierta** (el lote vencido es el primero en orden FEFO) |
| `fecha_vencimiento` | date | no | Sólo en entradas: fecha del lote nuevo |

### 3.6 `POST /v1/catalogo` — alta y actualización masiva

No mueve stock. Es la propuesta `D12` del backlog y la vía de la carga inicial.

| Campo | Tipo | Nota |
|---|---|---|
| `items[].codigo_barras` / `sku` | string | Al menos uno: es la clave de upsert |
| `items[].nombre` | string | Obligatorio en el alta |
| `items[].precio`, `costo` | number | |
| `items[].categoria` | string | Por nombre; se crea si no existe (es el flujo que la pantalla ya permite) |
| `items[].perecible`, `vida_util_dias` | boolean, int | **Cárguenlos acá.** Es el dato que habilita el control de vencimiento, y pedirlo producto por producto después no va a pasar |
| `items[].stock_inicial` | number | Si viene, crea el **lote de apertura** con fecha estimada (trigger de `0049`), y queda marcado como estimada |

---

## 4. La memoria de la API — schema `ingesta`

### 4.1 El diario de documentos: recibir y promover son dos pasos

```sql
create schema ingesta;

create table ingesta.documentos (
  id              uuid primary key default gen_random_uuid(),
  negocio_id      uuid not null references public.negocios(id) on delete cascade,
  tipo            text not null check (tipo in ('recepcion','venta','conteo','movimiento','catalogo')),
  idempotency_key text not null,
  origen          text,
  payload         jsonb not null,        -- EXACTAMENTE lo recibido, sin normalizar
  recibido_en     timestamptz not null default now(),
  estado          text not null default 'recibido'
                  check (estado in ('recibido','promovido','rechazado')),
  ref_id          uuid,                  -- el documento creado en public
  error           text,
  intentos        integer not null default 0,
  procesado_en    timestamptz,
  unique (negocio_id, tipo, idempotency_key)
);
```

**Por qué dos pasos y no uno.** La API responde `202` en cuanto el payload está guardado, y la
promoción a `public` ocurre después llamando a la RPC. Eso da tres cosas que un solo paso no da:

1. **Nada se pierde.** Un documento que falla —producto desconocido, perecible sin fecha, stock
   insuficiente— queda con su `error` y su payload intacto, reprocesable una vez corregido el
   catálogo. Es **el mismo patrón del outbox del teléfono** (`outbox_ventas` con estado
   `pendiente`/`error` y resolución manual), que ya está probado en dispositivo. La API es un
   outbox para documentos de terceros.
2. **El payload crudo es la única prueba de qué mandó el emisor.** Cuando el proveedor insista
   en que envió la fecha, ahí está. Normalizar antes de guardar destruye esa evidencia.
3. **Reprocesar después de arreglar un mapeo** es posible sin pedir el reenvío.

⚠ **`payload` es append-only.** No se corrige: se promueve, se rechaza, o se reprocesa. Editar lo
recibido convierte la memoria en una opinión.

### 4.2 El mapeo aprendido — la memoria que de verdad hace falta primero

```sql
create table ingesta.mapeo_producto (
  id            uuid primary key default gen_random_uuid(),
  negocio_id    uuid not null references public.negocios(id) on delete cascade,
  origen        text not null,                -- de quién viene esta forma de nombrar
  clave_externa text not null,                -- "YOG FRUT 150G", "COD-4471"
  producto_id   uuid not null references public.productos(id) on delete cascade,
  confirmado    boolean not null default false,  -- lo confirmó un humano
  veces_usado   integer not null default 0,
  created_at    timestamptz not null default now(),
  unique (negocio_id, origen, clave_externa)
);
```

> **La primera memoria que necesita esta API no son embeddings: es esta tabla.** El 90 % del
> trabajo real de ingerir documentos de terceros es que cada emisor nombra los productos a su
> manera. Resuelto una vez y confirmado por un humano, la segunda vez el documento entra solo.
> Es barato, determinista, auditable y da resultados desde el primer día — todo lo contrario a
> empezar por el RAG.

Un mapeo **no confirmado nunca promueve solo** un documento: sugiere, y alguien acepta. Misma
regla que el resto del sistema: *el sistema observa y propone, decide el humano*.

---

## 5. Lectura

Todo sale de las vistas que ya existen. La API no recalcula nada.

| Endpoint | Fuente | Para qué |
|---|---|---|
| `GET /v1/productos?incluir=stock,lotes` | `productos` + `vw_stock_producto` | Catálogo con stock registrado, por lotes, vendible y descuadre |
| `GET /v1/productos/{id}/lotes` | `lotes` | Saldos por tanda, en orden FEFO |
| `GET /v1/vencimientos?dias=7` | `vw_metricas_producto` | Unidades vencidas y por vencer, por producto |
| `GET /v1/metricas` | `vw_metricas_producto` | VDP, ROP, cobertura, capital, ABC, patrón, confianza |
| `GET /v1/alertas`, `GET /v1/recomendaciones` | `alertas`, `recomendaciones` | La inteligencia operativa, tal cual la ve la app |
| `GET /v1/documentos/{id}` | `ingesta.documentos` | Estado y trazabilidad de lo ingerido |

La información que la API inyecta alimenta la inteligencia operativa **por el mismo camino** que
la operación del mostrador: una recepción por API y una recepción a mano producen exactamente los
mismos lotes, movimientos y métricas. No hay una segunda ruta de cálculo que mantener.

---

## 6. El RAG — schema `rag`

### 6.1 Qué se vectoriza, y sobre todo qué NO

❌ **No se vectorizan números.** Stock, VDP, ROP, capital, lotes: eso se consulta en SQL, donde es
exacto, auditable y ya está probado. Un embedding de una tabla de cifras produce respuestas
plausibles e inverificables, que es justo lo que este proyecto decidió no hacer.

✅ Se vectoriza el **texto que hoy no tiene casa en SQL**:

- Catálogos y listas de precios de proveedores (PDF, planilla) — material compartido o del negocio.
- Descripciones de producto, fichas técnicas, instrucciones de conservación.
- El **histórico narrativo** que el propio sistema ya genera: `recomendaciones.motivo`,
  `contexto_radar`, mensajes de alertas, descripciones de `eventos_negocio`. Es memoria del
  negocio escrita en lenguaje del negocio.
- El manual de usuario y la documentación operativa.

```sql
create schema rag;
create extension if not exists vector;

create table rag.fuentes (
  id            uuid primary key default gen_random_uuid(),
  negocio_id    uuid references public.negocios(id) on delete cascade,  -- NULL = compartida
  tipo          text not null,      -- 'catalogo_proveedor' | 'manual' | 'historico_motor' | ...
  titulo        text not null,
  uri           text,
  hash          text,               -- para no re-indexar lo mismo
  actualizado_en timestamptz not null default now()
);

create table rag.fragmentos (
  id         uuid primary key default gen_random_uuid(),
  fuente_id  uuid not null references rag.fuentes(id) on delete cascade,
  negocio_id uuid references public.negocios(id) on delete cascade,  -- denormalizado para RLS
  orden      integer not null,
  texto      text not null,
  metadatos  jsonb not null default '{}'::jsonb,   -- producto_id, proveedor_id, fecha…
  embedding  vector(1536)
);

create index on rag.fragmentos using hnsw (embedding vector_cosine_ops);
create index idx_frag_negocio on rag.fragmentos(negocio_id);
```

`negocio_id is null` = **referencia compartida de sólo lectura**, el mismo patrón que `feriados`.

### 6.2 La regla que no se puede negociar: el filtro va DENTRO de la búsqueda

```sql
create policy fragmentos_select on rag.fragmentos
  for select to authenticated
  using (negocio_id is null or negocio_id = (select public.current_negocio_id()));
```

La búsqueda vectorial tiene que ocurrir **dentro** del límite de RLS, nunca filtrando después de
recuperar. Un `order by embedding <=> $1 limit 10` sin la política aplicada devuelve los diez
fragmentos más parecidos **de todos los inquilinos**, y filtrarlos en la API deja al modelo —o a
un error de código— a un paso de contar a un negocio lo que hace el otro. Con el `select`
envuelto en subselect, además, se cumple la disciplina de `0022`.

### 6.3 Recuperación HÍBRIDA, y la jerarquía entre las dos mitades

```
pregunta
  ├─ hechos     → SQL determinista (vw_metricas_producto, lotes, vw_lead_time_proveedor)
  └─ contexto   → rag.fragmentos (top-k por similitud, acotado por RLS)
        ↓
     el modelo REDACTA; las cifras vienen del primer camino, nunca del segundo
```

- **Ninguna cifra del negocio la produce el modelo.** Las cifras se calculan en SQL y se le pasan
  ya resueltas. El modelo elige las palabras, no los números.
- **Los 5 intents tipados siguen siendo el camino determinista.** Si el proveedor del modelo no
  responde, el copiloto sigue funcionando exactamente como hoy. El RAG es aditivo, no un
  reemplazo.
- **Toda respuesta cita su fuente** (`fuente_id` + fragmento). Es la misma exigencia que el resto
  del sistema: un cálculo que se lee en pantalla es un cálculo que se puede depurar.

### 6.4 Qué falta decidir antes de escribir una línea de esto

Un **ADR-005**, por la convención del propio proyecto (toda decisión estructural exige ADR antes
de codificar): qué datos del negocio salen hacia el proveedor del modelo y con qué base legal,
qué pasa cuando no responde, quién paga los tokens, y el límite duro de que las cifras no se
generan. Hasta que ese ADR exista, lo que corresponde construir es el schema `ingesta` —que
rinde solo, sin ningún LLM— y dejar `rag` como terreno preparado.

---

## 7. Límites conocidos de esta propuesta

1. **Los documentos no se pueden antedatar.** Las RPC fechan con `now()` y `fecha_ingreso` del
   lote es `current_date`. Para cargar historia (una migración desde otro sistema) haría falta un
   parámetro de fecha en `registrar_recepcion`, con el riesgo de que una fecha del pasado
   desordene la reconstrucción de stock de `0034`. Queda declarado, no resuelto.
2. **La promoción es de a un documento.** Un lote de 5.000 líneas de catálogo necesita su propio
   camino por tandas; recepciones y ventas no tienen ese volumen en este segmento.
3. **No hay webhooks de salida.** Si el emisor quiere saber que su documento se promovió, hoy
   consulta `GET /v1/documentos/{id}`.
4. **El schema `ingesta` no tiene todavía pruebas SQL.** Cuando se implemente, le corresponden al
   menos dos: que un reenvío no promueva dos veces, y que un documento de un negocio no sea
   visible para otro.

---

## 8. Orden sugerido de construcción

| # | Paso | Por qué ahí |
|---|---|---|
| 1 | Aplicar `0046`–`0059` en Supabase y `npm run gen:types` | Todo lo demás asume ese esquema; la pantalla de recepción ya lo asume |
| 2 | `ingesta.api_keys` + el puente clave → JWT | Sin esto, la tentación de usar `service_role` gana por comodidad y después no se revierte |
| 3 | `ingesta.documentos` + `POST /v1/recepciones` + `GET /v1/productos` | El circuito completo con el endpoint que más valor trae: el que carga lotes con fecha |
| 4 | `ingesta.mapeo_producto` | A partir del segundo documento del mismo emisor, se paga solo |
| 5 | El resto de los `POST` y las lecturas | Mecánico una vez que el patrón está |
| 6 | ADR-005 y, sólo después, `rag` | El orden importa: la decisión antes del código |

---

## 9. Referencias

- `docs/diseno-lotes-y-vencimiento.md` — el esquema que esta API usa, y por qué.
- `docs/adr-004-recalculo-bajo-demanda.md` — el criterio de "la función no recibe el inquilino".
- `docs/endurecimiento-escalabilidad.md` — por qué RLS con subselect e índices por `negocio_id`.
- `docs/backlog-producto.md` — `D12` (carga inicial de catálogo) entra por `POST /v1/catalogo`.
- `supabase/migrations/0059_resolver_producto.sql` — la resolución de identidad externa.
- `src/features/ventas/outbox.ts` — el patrón de diario con reintentos del que `ingesta` es hermano.
