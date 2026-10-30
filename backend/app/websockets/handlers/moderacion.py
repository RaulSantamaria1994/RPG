"""Mensajes exclusivos del máster: forzar un salto de nodo o el resultado
de una tirada, marcar a un jugador ausente/activo, ajustar su vida o maná a
mano, y expulsarlo de la sala.
"""

import uuid

from app.engine.dice import Banda, ResultadoTirada
from app.engine.resolver import ErrorInteraccion, aplicar_resultado, encontrar_nodo, encontrar_palabra_clave
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.websockets.comun import (
    _avanzar_turnos_invalidos,
    _avanzar_y_notificar,
    _enviar_error,
    _personajes_no_master,
    _personaje_publico,
    _procesar_posible_muerte,
    _usa_muerte_permanente,
)
from app.websockets.manager import ConexionJugador, gestor


async def _manejar_override_nodo(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "master":
        await _enviar_error(conexion, "Solo el máster puede forzar un salto de nodo.")
        return
    try:
        encontrar_nodo(sala.historia.contenido, datos["nodo_id"])
    except ErrorInteraccion as exc:
        await _enviar_error(conexion, str(exc))
        return
    await _avanzar_y_notificar(db, sala, datos["nodo_id"])


async def _manejar_override_resultado(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "master":
        await _enviar_error(conexion, "Solo el máster puede forzar el resultado de una tirada.")
        return
    estado = sala.estado_sala
    nodo_id = estado.nodo_actual_id
    try:
        nodo = encontrar_nodo(sala.historia.contenido, nodo_id)
        palabra = encontrar_palabra_clave(nodo, datos["palabra_clave"])
        personaje = db.get(Personaje, uuid.UUID(datos["personaje_id"]))
        if personaje is None:
            raise ErrorInteraccion("Ese personaje no existe.")
    except (ErrorInteraccion, KeyError) as exc:
        await _enviar_error(conexion, str(exc) if isinstance(exc, ErrorInteraccion) else "Datos incompletos.")
        return

    # El máster fuerza el resultado a mano: sin tirada real, así que no hay
    # banda de 7-9 que forzar, solo éxito limpio o fallo.
    exito = bool(datos.get("exito", True))
    resultado_forzado = ResultadoTirada(
        dados=(0, 0), modificador=0, total=0, banda=Banda.EXITO if exito else Banda.FALLO
    )
    personajes_sala = _personajes_no_master(db, sala.id)
    cambios = aplicar_resultado(
        nodo_id,
        palabra,
        resultado_forzado,
        estado,
        personaje,
        muerte_permanente=_usa_muerte_permanente(sala),
        personajes_sala=personajes_sala,
    )
    db.commit()

    if (cambios.get("objeto_otorgado") or {}).get("categoria") == "hechizo":
        for p in personajes_sala:
            await gestor.broadcast(
                str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(p)}
            )

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "tirada_resultado",
            "datos": {"palabra_clave": palabra["texto"], "exito": exito, "override_master": True},
        },
    )
    if cambios.get("dano_aplicado"):
        await gestor.broadcast(
            str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
        )

    if await _procesar_posible_muerte(db, sala, personaje, personajes_sala):
        return

    await _avanzar_y_notificar(db, sala, cambios["nodo_destino"])


async def _manejar_marcar_ausente(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "master":
        await _enviar_error(conexion, "Solo el máster puede marcar a un jugador como ausente.")
        return
    try:
        personaje = db.get(Personaje, uuid.UUID(datos["personaje_id"]))
    except (KeyError, ValueError):
        await _enviar_error(conexion, "Datos incompletos.")
        return
    if personaje is None or personaje.sala_id != sala.id:
        await _enviar_error(conexion, "Ese personaje no existe en esta sala.")
        return
    if personaje.estado == "muerto":
        await _enviar_error(conexion, "Ese personaje ha muerto de forma permanente.")
        return

    personaje.estado = "ausente"
    db.commit()
    await gestor.broadcast(
        str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
    )
    await _avanzar_turnos_invalidos(db, sala)


async def _manejar_marcar_activo(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "master":
        await _enviar_error(conexion, "Solo el máster puede reactivar a un jugador.")
        return
    try:
        personaje = db.get(Personaje, uuid.UUID(datos["personaje_id"]))
    except (KeyError, ValueError):
        await _enviar_error(conexion, "Datos incompletos.")
        return
    if personaje is None or personaje.sala_id != sala.id:
        await _enviar_error(conexion, "Ese personaje no existe en esta sala.")
        return
    if personaje.estado == "muerto":
        await _enviar_error(conexion, "Ese personaje ha muerto de forma permanente.")
        return

    personaje.estado = "activo"
    db.commit()
    await gestor.broadcast(
        str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
    )


async def _manejar_ajustar_personaje(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    """Control manual del máster sobre la vida y el maná de un personaje:
    para curar tras un descanso narrativo que no sea un punto_descanso,
    aplicar una consecuencia que no encaja en ninguna palabra clave, o
    corregir algo sobre la marcha. `delta_vida`/`delta_mana` son enteros
    (pueden ser negativos) que se suman al valor actual, recortado a
    [0, máximo]. Si así se cura a alguien inconsciente por encima de 0 de
    vida, vuelve a quedar activo; si lo deja a 0, se aplica la misma regla
    de muerte permanente que el resto del daño del juego.
    """
    if conexion.rol != "master":
        await _enviar_error(conexion, "Solo el máster puede ajustar la vida o el maná de un personaje.")
        return
    try:
        personaje = db.get(Personaje, uuid.UUID(datos["personaje_id"]))
        delta_vida = int(datos.get("delta_vida") or 0)
        delta_mana = int(datos.get("delta_mana") or 0)
    except (KeyError, ValueError, TypeError):
        await _enviar_error(conexion, "Datos incompletos.")
        return
    if personaje is None or personaje.sala_id != sala.id:
        await _enviar_error(conexion, "Ese personaje no existe en esta sala.")
        return
    if personaje.estado == "muerto":
        await _enviar_error(conexion, "Ese personaje ha muerto de forma permanente.")
        return
    if not delta_vida and not delta_mana:
        return

    vida_antes = personaje.vida_actual
    mana_antes = personaje.mana_actual
    personaje.vida_actual = max(0, min(personaje.vida_max, personaje.vida_actual + delta_vida))
    personaje.mana_actual = max(0, min(personaje.mana_max, personaje.mana_actual + delta_mana))

    if personaje.vida_actual == 0 and personaje.estado == "activo":
        personaje.estado = "muerto" if _usa_muerte_permanente(sala) else "inconsciente"
    elif personaje.vida_actual > 0 and personaje.estado == "inconsciente":
        personaje.estado = "activo"

    db.commit()
    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "personaje_ajustado",
            "datos": {
                "personaje_id": str(personaje.id),
                "nombre": personaje.nombre,
                "delta_vida": personaje.vida_actual - vida_antes,
                "delta_mana": personaje.mana_actual - mana_antes,
            },
        },
    )
    await gestor.broadcast(
        str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
    )

    await _procesar_posible_muerte(db, sala, personaje)


async def _manejar_expulsar_jugador(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    """Expulsión definitiva (a diferencia de "marcar ausente", que es
    reversible): borra el personaje, así que su token deja de servir y no
    puede volver a entrar con él — tendría que unirse de nuevo desde cero
    si el máster se lo permite."""
    if conexion.rol != "master":
        await _enviar_error(conexion, "Solo el máster puede expulsar a un jugador.")
        return
    try:
        personaje_id = str(datos["personaje_id"])
        personaje = db.get(Personaje, uuid.UUID(personaje_id))
    except (KeyError, ValueError):
        await _enviar_error(conexion, "Datos incompletos.")
        return
    if personaje is None or personaje.sala_id != sala.id:
        await _enviar_error(conexion, "Ese personaje no existe en esta sala.")
        return

    nombre = personaje.nombre
    jugador_nombre = personaje.jugador_nombre
    objetivo = gestor.conexion_de_personaje(str(sala.id), personaje_id)

    db.delete(personaje)
    db.commit()

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "jugador_expulsado",
            "datos": {"personaje_id": personaje_id, "nombre": nombre, "jugador_nombre": jugador_nombre},
        },
    )

    if objetivo:
        await objetivo.websocket.close(code=4403)
