"""Endpoint WebSocket de sala: un socket por jugador conectado, un canal de
difusión por sala. Aquí vive el ciclo de vida de la conexión (aceptar,
cargar sala, recibir mensajes, cerrar) y la tabla de despacho hacia los
manejadores de cada tipo de mensaje, repartidos por dominio en `handlers/`.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.security import decodificar_token
from app.websockets.comun import _enviar_error, _estado_publico, _personajes_no_master, _personaje_publico
from app.websockets.handlers.combate import _manejar_combate_accion
from app.websockets.handlers.interaccion import _manejar_continuar, _manejar_interactuar
from app.websockets.handlers.intercambio import (
    _manejar_desequipar_objeto,
    _manejar_equipar_objeto,
    _manejar_intercambio_confirmar,
    _manejar_intercambio_proponer,
)
from app.websockets.handlers.moderacion import (
    _manejar_ajustar_personaje,
    _manejar_expulsar_jugador,
    _manejar_marcar_activo,
    _manejar_marcar_ausente,
    _manejar_override_nodo,
    _manejar_override_resultado,
)
from app.websockets.manager import ConexionJugador, gestor

router = APIRouter()

MANEJADORES = {
    "interactuar": _manejar_interactuar,
    "continuar": _manejar_continuar,
    "override_nodo": _manejar_override_nodo,
    "override_resultado": _manejar_override_resultado,
    "marcar_ausente": _manejar_marcar_ausente,
    "marcar_activo": _manejar_marcar_activo,
    "ajustar_personaje": _manejar_ajustar_personaje,
    "expulsar_jugador": _manejar_expulsar_jugador,
    "combate_accion": _manejar_combate_accion,
    "intercambio_proponer": _manejar_intercambio_proponer,
    "intercambio_confirmar": _manejar_intercambio_confirmar,
    "equipar_objeto": _manejar_equipar_objeto,
    "desequipar_objeto": _manejar_desequipar_objeto,
}


@router.websocket("/ws/sala/{codigo}")
async def sala_websocket(websocket: WebSocket, codigo: str, token: str = Query(...)):
    # Se acepta primero y se valida después: un close() antes del accept()
    # es un rechazo de handshake, y los navegadores no propagan el código de
    # cierre real de un rechazo (lo normalizan a 1006), así que el cliente no
    # puede distinguir "token inválido"/"sala borrada" de un simple corte de
    # red. Con el socket ya abierto, el código de cierre sí llega tal cual.
    await websocket.accept()

    try:
        payload = decodificar_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    sala = db.query(Sala).filter(Sala.codigo == codigo.upper()).first()
    if not sala or str(sala.id) != payload.sala_id:
        await websocket.close(code=4404)
        db.close()
        return

    # Un jugador expulsado conserva un token con firma válida, pero su
    # personaje ya no existe: no se le deja volver a entrar con él.
    if payload.rol == "jugador" and (
        not payload.personaje_id or db.get(Personaje, uuid.UUID(payload.personaje_id)) is None
    ):
        await websocket.close(code=4404)
        db.close()
        return

    conexion = ConexionJugador(
        websocket=websocket, personaje_id=payload.personaje_id, nombre=payload.nombre, rol=payload.rol
    )

    try:
        gestor.conectar(str(sala.id), conexion)
        sala.ultima_actividad_en = datetime.now(timezone.utc)
        db.commit()
        personajes_publicos = []
        for p in _personajes_no_master(db, sala.id):
            personajes_publicos.append(_personaje_publico(p))

        datos_estado_inicial = {
            "sala": {"codigo": sala.codigo, "nombre": sala.nombre, "titulo_historia": sala.historia.titulo},
        }
        for clave, valor in _estado_publico(sala).items():
            datos_estado_inicial[clave] = valor
        datos_estado_inicial["personajes"] = personajes_publicos

        await gestor.enviar_a(conexion, {"tipo": "estado_inicial", "datos": datos_estado_inicial})
        personaje_conectado = (
            db.get(Personaje, uuid.UUID(conexion.personaje_id)) if conexion.personaje_id else None
        )
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "jugador_conectado",
                "datos": {
                    "nombre": conexion.nombre,
                    "rol": conexion.rol,
                    "personaje": _personaje_publico(personaje_conectado) if personaje_conectado else None,
                },
            },
        )

        while True:
            mensaje = await websocket.receive_json()
            tipo = mensaje.get("tipo")
            datos = mensaje.get("datos", {}) or {}

            # Cada conexión WS tiene su propia sesión de BD; con expire_on_commit=False
            # (necesario para que flag_modified funcione tras un commit intermedio, ver
            # _avanzar_turnos_invalidos en comun.py) esta sesión nunca ve por sí sola los
            # cambios que confirman OTRAS conexiones (p. ej. el máster forzando un salto
            # de nodo). Expirar todo al principio de cada mensaje fuerza a releer de BD.
            db.expire_all()

            manejador = MANEJADORES.get(tipo)
            if manejador is None:
                await _enviar_error(conexion, f"Tipo de mensaje '{tipo}' no reconocido.")
                continue

            # Cuenta como actividad cualquier mensaje reconocido, no solo el
            # momento de conectar — si no, una sala con una conexión abierta
            # durante días pero sin que nadie toque nada seguiría pareciendo
            # "activa" para la limpieza de salas expiradas.
            sala.ultima_actividad_en = datetime.now(timezone.utc)
            db.commit()

            try:
                await manejador(db, sala, conexion, datos)
            except KeyError as exc:
                await _enviar_error(conexion, f"Falta el campo {exc}.")
            except Exception as exc:  # noqa: BLE001 - no debe tumbar el socket de toda la sala
                db.rollback()
                await _enviar_error(conexion, f"No se pudo procesar la acción: {exc}")

    except WebSocketDisconnect:
        pass
    finally:
        gestor.desconectar(str(sala.id), conexion)
        await gestor.broadcast(
            str(sala.id),
            {"tipo": "jugador_desconectado", "datos": {"nombre": conexion.nombre, "rol": conexion.rol}},
        )
        db.close()
