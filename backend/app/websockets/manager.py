"""Gestor de conexiones WebSocket: una lista de sockets por sala, con
broadcast a todos los conectados. Vive en memoria del proceso — coherente
con el spec (un proceso persistente por despliegue); el estado real de la
partida sigue viviendo en PostgreSQL vía EstadoSala.
"""

from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class ConexionJugador:
    websocket: WebSocket
    personaje_id: str | None
    nombre: str
    rol: str


@dataclass
class SalaConexiones:
    conexiones: list[ConexionJugador] = field(default_factory=list)
    # claves de palabra_clave (nodo_id:texto) actualmente bloqueadas, y quién las bloquea
    palabras_bloqueadas: dict[str, str] = field(default_factory=dict)
    # confirmaciones pendientes para interacciones en modo grupal/apoyo: clave -> set(personaje_id)
    confirmaciones: dict[str, set[str]] = field(default_factory=dict)
    # votos pendientes de una decisión grupal por votación (sin dificultad):
    # nodo_id -> {personaje_id: texto de la opción elegida}
    votos_grupales: dict[str, dict[str, str]] = field(default_factory=dict)


class GestorConexiones:
    def __init__(self) -> None:
        self._salas: dict[str, SalaConexiones] = {}

    def _sala(self, sala_id: str) -> SalaConexiones:
        return self._salas.setdefault(sala_id, SalaConexiones())

    def conectar(self, sala_id: str, conexion: ConexionJugador) -> None:
        """Registra una conexión ya aceptada. El accept() se hace en el
        endpoint antes de validar token/sala, para que un cierre por sesión
        inválida use un código de cierre real (con el socket ya abierto) en
        vez de un rechazo de handshake, que los navegadores no propagan.
        """
        self._sala(sala_id).conexiones.append(conexion)

    def desconectar(self, sala_id: str, conexion: ConexionJugador) -> None:
        sala = self._salas.get(sala_id)
        if sala and conexion in sala.conexiones:
            sala.conexiones.remove(conexion)

    async def broadcast(self, sala_id: str, mensaje: dict) -> None:
        for conexion in list(self._sala(sala_id).conexiones):
            try:
                await conexion.websocket.send_json(mensaje)
            except Exception:
                self.desconectar(sala_id, conexion)

    async def enviar_a(self, conexion: ConexionJugador, mensaje: dict) -> None:
        await conexion.websocket.send_json(mensaje)

    def bloquear_palabra(self, sala_id: str, clave: str, nombre_jugador: str) -> bool:
        bloqueadas = self._sala(sala_id).palabras_bloqueadas
        if clave in bloqueadas:
            return False
        bloqueadas[clave] = nombre_jugador
        return True

    def liberar_palabra(self, sala_id: str, clave: str) -> None:
        self._sala(sala_id).palabras_bloqueadas.pop(clave, None)

    def registrar_confirmacion(self, sala_id: str, clave: str, personaje_id: str) -> set[str]:
        confirmaciones = self._sala(sala_id).confirmaciones.setdefault(clave, set())
        confirmaciones.add(personaje_id)
        return confirmaciones

    def limpiar_confirmaciones(self, sala_id: str, clave: str) -> None:
        self._sala(sala_id).confirmaciones.pop(clave, None)

    def registrar_voto(self, sala_id: str, nodo_id: str, personaje_id: str, texto: str) -> dict[str, str]:
        votos = self._sala(sala_id).votos_grupales.setdefault(nodo_id, {})
        votos[personaje_id] = texto
        return votos

    def limpiar_votos(self, sala_id: str, nodo_id: str) -> None:
        self._sala(sala_id).votos_grupales.pop(nodo_id, None)


gestor = GestorConexiones()
