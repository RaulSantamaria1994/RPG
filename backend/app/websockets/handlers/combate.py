"""Mensaje `combate_accion`: golpear, proteger a alguien, escabullirse,
actuar bajo presión, o usar un objeto durante un combate. Todo salvo el
objeto se resuelve con una movida (2d6 + característica, mismas bandas que
el resto del juego) — el enemigo no tiene turno propio ni tira: su
contraataque, si lo hay, va dentro de la propia resolución de la movida
del jugador (ver app/engine/combate.py).
"""

import uuid

from sqlalchemy.orm.attributes import flag_modified

from app.engine import combate as combate_engine
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.websockets.comun import (
    _avanzar_turnos_invalidos,
    _avanzar_y_notificar,
    _broadcast_nodo,
    _enviar_error,
    _personajes_no_master,
    _personaje_publico,
    _procesar_posible_muerte,
    _usa_muerte_permanente,
)
from app.websockets.manager import ConexionJugador, gestor


async def _tras_dano(db, sala: Sala, estado, afectados: list[Personaje]) -> bool:
    """Tras aplicar el daño de una acción de combate: notifica a quien lo
    sufrió, procesa un posible epílogo (individual o muerte total), y si ya
    no queda nadie activo, resuelve la derrota del grupo entero. Devuelve
    True si la partida ya quedó resuelta por esta vía."""
    flag_modified(estado, "combate")
    db.commit()

    for p in afectados:
        await gestor.broadcast(
            str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(p)}
        )
        if await _procesar_posible_muerte(db, sala, p):
            return True

    activos = [p for p in _personajes_no_master(db, sala.id) if p.estado == "activo"]
    if not activos:
        combate = estado.combate
        combate["terminado"] = True
        combate["resultado"] = "derrota"
        flag_modified(estado, "combate")
        db.commit()
        nodo_actual = sala.historia.contenido["nodos"][estado.nodo_actual_id]
        destino = nodo_actual.get("nodo_derrota")
        if destino:
            await _avanzar_y_notificar(db, sala, destino)
        else:
            await _broadcast_nodo(sala)
        return True

    return False


async def _manejar_combate_accion(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    estado = sala.estado_sala
    combate = estado.combate
    if not combate or combate.get("terminado"):
        await _enviar_error(conexion, "No hay combate activo.")
        return

    turno = combate["orden_iniciativa"][combate["turno_index"]]
    if turno != f"personaje:{conexion.personaje_id}":
        await _enviar_error(conexion, "No es tu turno.")
        return

    personaje = db.get(Personaje, uuid.UUID(conexion.personaje_id))
    accion = datos.get("accion")
    nodo_actual = sala.historia.contenido["nodos"][estado.nodo_actual_id]
    muerte_permanente = _usa_muerte_permanente(sala)

    if accion == "golpear":
        try:
            enemigo_id = datos["enemigo_id"]
        except KeyError:
            await _enviar_error(conexion, "Falta a qué enemigo atacar.")
            return
        if combate_engine.enemigo_en_combate(combate, enemigo_id) is None:
            await _enviar_error(conexion, "Ese enemigo no está en el combate.")
            return

        resultado = combate_engine.resolver_golpear(combate, personaje, enemigo_id, muerte_permanente)
        datos_resultado = {
            "origen": "jugador",
            "accion": "golpear",
            "personaje_id": str(personaje.id),
            "personaje_nombre": personaje.nombre,
        }
        datos_resultado.update(resultado)
        await gestor.broadcast(str(sala.id), {"tipo": "combate_resultado", "datos": datos_resultado})

        if resultado["dano_recibido"] and await _tras_dano(db, sala, estado, [personaje]):
            return
        if combate_engine.evaluar_fin_combate(combate) == "victoria":
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual.get("nodo_victoria"))
            return

    elif accion == "proteger":
        try:
            protegido_id = datos["protegido_personaje_id"]
            enemigo_id = datos["enemigo_id"]
        except KeyError:
            await _enviar_error(conexion, "Falta a quién proteger o de qué enemigo.")
            return
        try:
            protegido = db.get(Personaje, uuid.UUID(protegido_id))
        except ValueError:
            protegido = None
        if protegido is None or protegido.sala_id != sala.id:
            await _enviar_error(conexion, "Ese personaje no está en esta sala.")
            return
        if combate_engine.enemigo_en_combate(combate, enemigo_id) is None:
            await _enviar_error(conexion, "Ese enemigo no está en el combate.")
            return

        resultado = combate_engine.resolver_proteger(
            combate, personaje, protegido, enemigo_id, muerte_permanente
        )
        datos_resultado = {
            "origen": "jugador",
            "accion": "proteger",
            "personaje_id": str(personaje.id),
            "personaje_nombre": personaje.nombre,
        }
        datos_resultado.update(resultado)
        await gestor.broadcast(str(sala.id), {"tipo": "combate_resultado", "datos": datos_resultado})

        afectados = []
        if resultado["dano_protector"]:
            afectados.append(personaje)
        if resultado["dano_protegido"]:
            afectados.append(protegido)
        if afectados and await _tras_dano(db, sala, estado, afectados):
            return

    elif accion == "escabullirse":
        resultado = combate_engine.resolver_escabullirse(combate, personaje, muerte_permanente)
        datos_resultado = {
            "origen": "jugador",
            "accion": "escabullirse",
            "personaje_id": str(personaje.id),
            "personaje_nombre": personaje.nombre,
        }
        datos_resultado.update(resultado)
        await gestor.broadcast(str(sala.id), {"tipo": "combate_resultado", "datos": datos_resultado})

        if resultado["dano_recibido"] and await _tras_dano(db, sala, estado, [personaje]):
            return
        if resultado["huido"] and nodo_actual.get("nodo_huida"):
            combate["terminado"] = True
            combate["resultado"] = "huida"
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual["nodo_huida"])
            return

    elif accion == "actuar_bajo_presion":
        resultado = combate_engine.resolver_actuar_bajo_presion(combate, personaje, muerte_permanente)
        datos_resultado = {
            "origen": "jugador",
            "accion": "actuar_bajo_presion",
            "personaje_id": str(personaje.id),
            "personaje_nombre": personaje.nombre,
        }
        datos_resultado.update(resultado)
        await gestor.broadcast(str(sala.id), {"tipo": "combate_resultado", "datos": datos_resultado})

        if resultado["dano_recibido"] and await _tras_dano(db, sala, estado, [personaje]):
            return

    elif accion == "objeto":
        try:
            objeto_id = datos["objeto_id"]
        except KeyError:
            await _enviar_error(conexion, "Falta el objeto a usar.")
            return

        # El inventario es común al grupo: el objeto puede estar en el
        # fondo compartido o en el inventario personal de quien lo usa.
        inventario_grupo = list(estado.inventario_grupo or [])
        inventario_personal = list(personaje.inventario or [])

        objeto = None
        for o in inventario_grupo:
            if o.get("objeto_id") == objeto_id:
                objeto = o
        if objeto is not None:
            origen = "grupo"
        else:
            for o in inventario_personal:
                if o.get("objeto_id") == objeto_id:
                    objeto = o
            origen = "personal" if objeto is not None else None

        efecto = (objeto or {}).get("efecto") or {}
        tipo_efecto = efecto.get("tipo")
        if objeto is None or tipo_efecto not in ("curar_vida", "curar_mana", "dano"):
            await _enviar_error(conexion, "Ese objeto no se puede usar en combate.")
            return

        cantidad = efecto.get("cantidad", 0)
        enemigo_objetivo_id = None
        if tipo_efecto == "curar_vida":
            personaje.vida_actual = min(personaje.vida_max, personaje.vida_actual + cantidad)
        elif tipo_efecto == "curar_mana":
            personaje.mana_actual = min(personaje.mana_max, personaje.mana_actual + cantidad)
        else:  # dano: un objeto de ataque (arma arrojadiza, bomba improvisada...)
            enemigo_objetivo_id = datos.get("enemigo_id")
            enemigo = combate_engine.enemigo_en_combate(combate, enemigo_objetivo_id or "")
            if enemigo is None:
                await _enviar_error(conexion, "Elige a qué enemigo usar este objeto.")
                return
            enemigo["vida"] = max(0, enemigo["vida"] - cantidad)
            if enemigo["vida"] == 0:
                enemigo["derrotado"] = True
            flag_modified(estado, "combate")

        if objeto.get("consumible", True):
            if origen == "grupo":
                inventario_grupo.remove(objeto)
                estado.inventario_grupo = inventario_grupo
                flag_modified(estado, "inventario_grupo")
            else:
                inventario_personal.remove(objeto)
                personaje.inventario = inventario_personal
                flag_modified(personaje, "inventario")

        db.commit()
        if tipo_efecto == "dano":
            efecto_para_mostrar = dict(efecto)
            efecto_para_mostrar["enemigo_id"] = enemigo_objetivo_id
        else:
            efecto_para_mostrar = efecto
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "combate_resultado",
                "datos": {
                    "origen": "jugador",
                    "accion": "objeto",
                    "personaje_id": str(personaje.id),
                    "personaje_nombre": personaje.nombre,
                    "objeto": objeto,
                    "efecto": efecto_para_mostrar,
                },
            },
        )
        if origen == "grupo":
            await _broadcast_nodo(sala)
        else:
            await gestor.broadcast(
                str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
            )

        if tipo_efecto == "dano" and combate_engine.evaluar_fin_combate(combate) == "victoria":
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual.get("nodo_victoria"))
            return

    else:
        await _enviar_error(conexion, f"Acción de combate '{accion}' no reconocida.")
        return

    combate_engine.avanzar_turno(combate)
    flag_modified(estado, "combate")
    db.commit()
    await _avanzar_turnos_invalidos(db, sala)
