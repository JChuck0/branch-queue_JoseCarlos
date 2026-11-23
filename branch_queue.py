"""
Branch Queue — Gestor de cola por servicio (Banco Meridional).

Solo usa la biblioteca estándar: collections.deque y datetime.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

VALID_SERVICES = ("deposito", "retiro", "gestion_cuenta")


# ---------------------------------------------------------------------------
# Errores descriptivos
# ---------------------------------------------------------------------------
class InvalidServiceError(ValueError):
    """El tipo de servicio no existe."""


class EmptyQueueError(LookupError):
    """No hay clientes esperando en la cola de ese servicio."""


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------
@dataclass
class Ticket:
    number: int
    client_name: str
    service_type: str
    issued_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        hora = self.issued_at.strftime("%H:%M:%S")
        return f"#{self.number} - {self.client_name} ({self.service_type}) - {hora}"


# ---------------------------------------------------------------------------
# Gestor de colas
# ---------------------------------------------------------------------------
class BranchQueue:
    def __init__(self):
        # Una cola (deque) independiente por tipo de servicio
        self._queues = {service: deque() for service in VALID_SERVICES}
        # Contador global: compartido por todos los servicios
        self._next_number = 1

    # -- utilidades internas ------------------------------------------------
    def _validate_service(self, service_type):
        """Normaliza y valida el tipo de servicio. Lanza error si no existe."""
        if not isinstance(service_type, str):
            raise InvalidServiceError(
                f"Tipo de servicio inválido: {service_type!r}. "
                f"Opciones válidas: {', '.join(VALID_SERVICES)}."
            )
        normalized = service_type.strip().lower()
        if normalized not in self._queues:
            raise InvalidServiceError(
                f"Tipo de servicio inválido: '{service_type}'. "
                f"Opciones válidas: {', '.join(VALID_SERVICES)}."
            )
        return normalized

    # -- operaciones de cola ------------------------------------------------
    def issue_ticket(self, client_name, service_type):
        """Crea un ticket, lo encola en su servicio y lo devuelve."""
        service = self._validate_service(service_type)  # validar ANTES de gastar número
        name = client_name.strip() if isinstance(client_name, str) else ""
        if not name:
            raise ValueError("El nombre del cliente no puede estar vacío.")

        ticket = Ticket(
            number=self._next_number,
            client_name=name,
            service_type=service,
        )
        self._next_number += 1
        self._queues[service].append(ticket)
        return ticket

    def call_next(self, service_type):
        """Desencola y devuelve el siguiente cliente de ese servicio."""
        service = self._validate_service(service_type)
        queue = self._queues[service]
        if not queue:
            raise EmptyQueueError(
                f"No hay clientes esperando para el servicio '{service}'."
            )
        return queue.popleft()  # O(1): el que lleva más tiempo esperando

    def peek_next(self, service_type):
        """Devuelve el siguiente cliente sin retirarlo."""
        service = self._validate_service(service_type)
        queue = self._queues[service]
        if not queue:
            raise EmptyQueueError(
                f"No hay clientes esperando para el servicio '{service}'."
            )
        return queue[0]

    def list_waiting(self):
        """Dict {servicio: [tickets en orden de atención]}."""
        return {service: list(queue) for service, queue in self._queues.items()}

    def stats(self):
        """Dict con clientes en espera por servicio y clave 'total'."""
        result = {service: len(queue) for service, queue in self._queues.items()}
        result["total"] = sum(result.values())
        return result


# ---------------------------------------------------------------------------
# Interfaz CLI
# ---------------------------------------------------------------------------
def ask_service():
    print("Tipos de servicio: " + ", ".join(VALID_SERVICES))
    return input("Tipo de servicio: ")


def show_waiting(branch):
    waiting = branch.list_waiting()
    for service, tickets in waiting.items():
        print(f"\n{service.upper()} ({len(tickets)} en espera)")
        if not tickets:
            print("  (vacía)")
        for position, ticket in enumerate(tickets, start=1):
            print(f"  {position}. {ticket}")


def show_stats(branch):
    stats = branch.stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    branch = BranchQueue()

    menu = (
        "\n=== Banco Meridional — Gestor de colas ===\n"
        "1. Emitir ticket\n"
        "2. Llamar al siguiente cliente\n"
        "3. Ver lista de espera\n"
        "4. Ver estadísticas\n"
        "5. Salir\n"
    )

    while True:
        print(menu)
        try:
            option = input("Elige una opción: ").strip()

            if option == "1":
                name = input("Nombre del cliente: ")
                service = ask_service()
                ticket = branch.issue_ticket(name, service)
                print(f"Ticket emitido: {ticket}")

            elif option == "2":
                service = ask_service()
                ticket = branch.call_next(service)
                print(f"Llamando a: {ticket}")

            elif option == "3":
                show_waiting(branch)

            elif option == "4":
                show_stats(branch)

            elif option == "5":
                print("Hasta luego.")
                break

            else:
                print("Opción no válida. Elige un número del 1 al 5.")

        except (InvalidServiceError, EmptyQueueError, ValueError) as error:
            print(f"Error: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            break


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# NOTAS DE DISEÑO (también puedes copiarlas a un DESIGN.md)
# ---------------------------------------------------------------------------
#
# 1) ¿Por qué una cola por servicio es más eficiente que una lista compartida?
#    Con una única lista, call_next("deposito") tendría que recorrerla hasta
#    encontrar el primer ticket de depósito (O(n)), y además borrarlo del
#    medio obliga a desplazar elementos. Con un deque por servicio, el primer
#    cliente de cada servicio ya está en la cabeza de SU cola, y popleft() es
#    O(1) sin importar cuánta gente espere en las otras colas. El orden FIFO
#    por servicio sale gratis: append() al final, popleft() por delante.
#
# 2) ¿Y si dos agentes del mismo servicio llaman a call_next a la vez?
#    Es una condición de carrera de tipo "comprobar y luego actuar": si cada
#    agente hiciera primero peek_next() (leer el primero) y luego lo
#    retirara, ambos podrían leer el mismo ticket y llamar al mismo cliente
#    dos veces. La mutación que debe ocurrir PRIMERO es sacar el ticket de la
#    cola (popleft). Quien lo extrae se lo "queda" en exclusiva; el segundo
#    agente obtiene el siguiente ticket (o error si ya no queda ninguno).
#    En CPython, deque.popleft() es atómico, pero la secuencia
#    "if queue: queue.popleft()" no lo es (la cola puede vaciarse entre el
#    if y el popleft). En un sistema con hilos reales se protegería toda la
#    operación con un threading.Lock (o se capturaría IndexError del
#    popleft). Lo mismo aplica al contador global de tickets: incrementarlo
#    también debe ser una sección crítica, para no repetir números.