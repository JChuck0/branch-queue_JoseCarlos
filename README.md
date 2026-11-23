# Branch Queue — Gestor de Cola por Servicio

Gestor de colas en terminal para las sucursales de **Banco Meridional**. Cada cliente toma un ticket numerado asociado a un tipo de servicio, y cada agente llama al siguiente cliente de su propio servicio de forma instantánea.

## Requisitos

- Python 3.8 o superior
- Solo biblioteca estándar (`collections.deque`, `dataclasses`, `datetime`). No hay que instalar nada.

## Cómo ejecutarlo

```bash
python branch_queue.py
```

## Tipos de servicio

| Valor            | Descripción          |
|------------------|----------------------|
| `deposito`       | Depósitos            |
| `retiro`         | Retiros              |
| `gestion_cuenta` | Gestión de cuenta    |

Cualquier otro valor se rechaza con un mensaje de error claro.

## Menú de la CLI

```
=== Banco Meridional — Gestor de colas ===
1. Emitir ticket
2. Llamar al siguiente cliente
3. Ver lista de espera
4. Ver estadísticas
5. Salir
```

Ejemplo de uso:

```
Elige una opción: 1
Nombre del cliente: Ana
Tipo de servicio: deposito
Ticket emitido: #1 - Ana (deposito) - 16:40:12

Elige una opción: 2
Tipo de servicio: deposito
Llamando a: #1 - Ana (deposito) - 16:40:12
```

## Estructura del código

### `Ticket` (dataclass)

| Campo          | Tipo       | Descripción                                   |
|----------------|------------|-----------------------------------------------|
| `number`       | `int`      | Número global y secuencial (empieza en 1)     |
| `client_name`  | `str`      | Nombre del cliente                            |
| `service_type` | `str`      | `deposito`, `retiro` o `gestion_cuenta`       |
| `issued_at`    | `datetime` | Momento de emisión (automático)               |

### `BranchQueue`

Mantiene un `deque` por tipo de servicio y un contador global de tickets.

| Método                                | Descripción                                                                 |
|---------------------------------------|-----------------------------------------------------------------------------|
| `issue_ticket(client_name, service_type)` | Crea el ticket, lo encola en su servicio y lo devuelve.                 |
| `call_next(service_type)`             | Desencola y devuelve el siguiente cliente. Error si la cola está vacía.     |
| `peek_next(service_type)`             | Devuelve el siguiente cliente sin retirarlo. Error si la cola está vacía.   |
| `list_waiting()`                      | `dict` con cada servicio y su lista de tickets en orden de atención.        |
| `stats()`                             | `dict` con los clientes por servicio y la clave `"total"`.                  |

### Excepciones propias

- `InvalidServiceError`: tipo de servicio inexistente.
- `EmptyQueueError`: no hay clientes esperando en ese servicio.

## Casos borde gestionados

- Los números de ticket son **globalmente secuenciales**, aunque los clientes estén en colas distintas.
- Dentro de cada servicio se respeta el orden **FIFO** estricto.
- `call_next()` y `peek_next()` sobre una cola vacía lanzan un error descriptivo que la CLI captura; el programa no se rompe.
- Un tipo de servicio inválido se rechaza al emitir el ticket **sin consumir un número** de la secuencia.
- Un nombre de cliente vacío se rechaza.
- El bucle de la CLI controla entradas inválidas, `Ctrl+C` y fin de entrada (`EOF`).

## Notas de diseño

### ¿Por qué una cola por servicio es más eficiente que una lista compartida?

Con una única lista compartida, `call_next("deposito")` tendría que recorrerla hasta encontrar el primer ticket de depósito (**O(n)**), y borrar un elemento del medio obliga además a desplazar el resto. Con un `deque` por servicio, el primer cliente de cada servicio ya está en la cabeza de su cola y `popleft()` es **O(1)**, sin importar cuánta gente espere para otros servicios. El orden FIFO sale gratis: `append()` al final, `popleft()` por delante.

### ¿Qué pasa si dos agentes del mismo servicio llaman a `call_next` a la vez?

Es una condición de carrera de tipo *comprobar y luego actuar*. Si cada agente leyera primero el siguiente ticket (`peek`) y después lo retirara, ambos podrían leer el mismo y llamar al mismo cliente dos veces.

La mutación que debe ocurrir **primero** es **extraer el ticket de la cola** (`popleft`). Quien lo extrae se queda con él en exclusiva; el segundo agente recibe el siguiente ticket (o un error si ya no queda ninguno).

En CPython `deque.popleft()` es atómico, pero la secuencia `if queue: queue.popleft()` no lo es: la cola puede vaciarse entre el `if` y el `popleft`. En un sistema con hilos reales se protegería toda la operación con un `threading.Lock`. Lo mismo aplica al contador global de tickets, cuyo incremento también debe ser una sección crítica para no repetir números.