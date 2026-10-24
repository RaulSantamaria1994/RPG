"""Mensajes de intercambio de objetos entre jugadores (proponer/confirmar)
y de equipar/desequipar arma o grimorio desde el inventario común.
"""

import uuid

from sqlalchemy.orm.attributes import flag_modified

from app.models.personaje import Personaje
from app.models.sala import Sala
from app.websockets.comun import _broadcast_nodo, _enviar_error, _personaje_publico
from app.websockets.manager import ConexionJugador, gestor


async def _manejar_intercambio_proponer(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "jugador":
        await _enviar_error(conexion, "Solo un jugador puede proponer un intercambio.")
        return
    try:
        origen = db.get(Personaje, uuid.UUID(conexion.personaje_id))
        objeto_id = datos["objeto_id"]
        destino_personaje_id = datos["destino_personaje_id"]
    except (KeyError, ValueError, TypeError):
        await _enviar_error(conexion, "Datos incompletos.")
        return

    objeto = None
    for o in origen.inventario or []:
        if o.get("objeto_id") == objeto_id:
            objeto = o
    if objeto is None:
        await _enviar_error(conexion, "No tienes ese objeto en tu inventario.")
        return

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "intercambio_propuesto",
            "datos": {
                "origen_personaje_id": conexion.personaje_id,
                "origen_personaje_nombre": origen.nombre,
                "objeto_id": objeto_id,
                "objeto_nombre": objeto.get("nombre", objeto_id),
                "destino_personaje_id": destino_personaje_id,
            },
        },
    )


async def _manejar_intercambio_confirmar(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "jugador":
        await _enviar_error(conexion, "Solo un jugador puede confirmar un intercambio.")
        return
    try:
        origen = db.get(Personaje, uuid.UUID(datos["origen_personaje_id"]))
        destino = db.get(Personaje, uuid.UUID(conexion.personaje_id))
        objeto_id = datos["objeto_id"]
    except (KeyError, ValueError, TypeError):
        await _enviar_error(conexion, "Datos incompletos.")
        return
    # `origen` lo decide el cliente (es quien propuso el intercambio, no esta
    # conexión) — sin este chequeo, cualquiera podría pasar el id de un
    # personaje de OTRA sala y robarle un objeto con solo saber su id y el
    # de uno de sus objetos.
    if origen is None or origen.sala_id != sala.id:
        await _enviar_error(
            conexion,
            "Ese personaje no existe en esta sala.",
            origen_personaje_id=datos["origen_personaje_id"],
            objeto_id=objeto_id,
        )
        return

    inventario_origen = list(origen.inventario or [])
    objeto = None
    for o in inventario_origen:
        if o.get("objeto_id") == objeto_id:
            objeto = o
    if objeto is None:
        # El cliente que propuso ya no tiene el objeto (lo usó, lo dio a
        # otro...): además del error, hay que decirle al destinatario cuál
        # propuesta concreta ha quedado obsoleta, para que deje de mostrarla
        # como si siguiera en pie.
        await _enviar_error(
            conexion,
            "Ese objeto ya no está disponible.",
            origen_personaje_id=str(origen.id),
            objeto_id=objeto_id,
        )
        return

    inventario_origen.remove(objeto)
    origen.inventario = inventario_origen
    flag_modified(origen, "inventario")

    inventario_destino = list(destino.inventario or [])
    inventario_destino.append(objeto)
    destino.inventario = inventario_destino
    flag_modified(destino, "inventario")

    db.commit()
    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "intercambio_completado",
            "datos": {
                "origen_personaje_id": str(origen.id),
                "destino_personaje_id": str(destino.id),
                "objeto": objeto,
            },
        },
    )


# A qué ranura del personaje va cada categoría de objeto equipable, y a la
# inversa, qué ranura (en los términos que ya usa el cliente) pide liberar
# un desequipar. "hechizo" como categoría ya significa otra cosa (ver
# `otorgar_objeto` en el motor): enseña el hechizo a todo el grupo en vez
# de quedar como objeto físico, así que un grimorio equipable usa "grimorio".
_CAMPO_POR_CATEGORIA = {"arma": "arma_equipada", "grimorio": "hechizo_equipado"}
_CAMPO_POR_RANURA = {"arma": "arma_equipada", "hechizo": "hechizo_equipado"}


async def _manejar_equipar_objeto(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "jugador":
        await _enviar_error(conexion, "Solo un jugador puede equipar objetos.")
        return
    try:
        objeto_id = datos["objeto_id"]
    except KeyError:
        await _enviar_error(conexion, "Falta el objeto a equipar.")
        return

    personaje = db.get(Personaje, uuid.UUID(conexion.personaje_id))
    estado = sala.estado_sala
    inventario_grupo = list(estado.inventario_grupo or [])
    objeto = None
    for o in inventario_grupo:
        if o.get("objeto_id") == objeto_id:
            objeto = o
    if objeto is None:
        await _enviar_error(conexion, "Ese objeto no está en el inventario común.")
        return

    campo = _CAMPO_POR_CATEGORIA.get(objeto.get("categoria"))
    if campo is None:
        await _enviar_error(conexion, "Ese objeto no se puede equipar.")
        return

    # Si ya llevaba algo en esa ranura, vuelve al inventario común — un
    # cambio de equipo no hace desaparecer el objeto anterior.
    anterior = getattr(personaje, campo)
    inventario_grupo.remove(objeto)
    if anterior is not None:
        inventario_grupo.append(anterior)
    setattr(personaje, campo, objeto)
    estado.inventario_grupo = inventario_grupo
    flag_modified(estado, "inventario_grupo")
    db.commit()

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "equipo_cambiado",
            "datos": {
                "personaje_nombre": personaje.nombre,
                "objeto_nombre": objeto.get("nombre", objeto_id),
                "ranura": "arma" if campo == "arma_equipada" else "hechizo",
                "accion": "equipar",
            },
        },
    )
    await gestor.broadcast(str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)})
    await _broadcast_nodo(sala)


async def _manejar_desequipar_objeto(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "jugador":
        await _enviar_error(conexion, "Solo un jugador puede desequipar objetos.")
        return
    campo = _CAMPO_POR_RANURA.get(datos.get("ranura"))
    if campo is None:
        await _enviar_error(conexion, "Ranura no reconocida.")
        return

    personaje = db.get(Personaje, uuid.UUID(conexion.personaje_id))
    objeto = getattr(personaje, campo)
    if objeto is None:
        await _enviar_error(conexion, "No tienes nada equipado en esa ranura.")
        return

    setattr(personaje, campo, None)
    estado = sala.estado_sala
    inventario_grupo = list(estado.inventario_grupo or [])
    inventario_grupo.append(objeto)
    estado.inventario_grupo = inventario_grupo
    flag_modified(estado, "inventario_grupo")
    db.commit()

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "equipo_cambiado",
            "datos": {
                "personaje_nombre": personaje.nombre,
                "objeto_nombre": objeto.get("nombre", objeto.get("objeto_id")),
                "ranura": datos["ranura"],
                "accion": "desequipar",
            },
        },
    )
    await gestor.broadcast(str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)})
    await _broadcast_nodo(sala)
