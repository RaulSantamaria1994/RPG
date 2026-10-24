"""Mensaje `combate_accion`: atacar, huir, negociar, usar un objeto o lanzar
un hechizo durante un combate, y la reacción inmediata del enemigo implicado
tras cada acción del jugador (los enemigos no tienen turno propio).
"""

import uuid

from sqlalchemy.orm.attributes import flag_modified

from app.engine import combate as combate_engine
from app.engine.dice import resolver_tirada
from app.engine.hechizos_base import hechizos_disponibles
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


async def _reaccion_enemigo(
    db, sala: Sala, combate: dict, estado, personaje: Personaje, enemigo_id: str | None
) -> bool:
    """Tras una acción de combate del jugador que no haya terminado el
    combate, el enemigo implicado (o uno vivo al azar si la acción no
    apuntaba a ninguno) le devuelve el golpe de inmediato — no espera a
    ningún turno propio. Si está aturdido, consume el aturdimiento y no
    ataca esta vez. Devuelve True si la partida ya quedó resuelta (muerte
    total o derrota del grupo) y el llamador no debe seguir avanzando el
    turno por su cuenta.
    """
    if combate.get("terminado"):
        return False

    if enemigo_id:
        enemigo = combate_engine.enemigo_en_combate(combate, enemigo_id)
        if enemigo is not None and enemigo["derrotado"]:
            enemigo = None
    else:
        enemigo = combate_engine.elegir_enemigo_reactivo(combate)

    if enemigo is None:
        return False

    if enemigo.get("aturdido"):
        enemigo["aturdido"] = False
        flag_modified(estado, "combate")
        db.commit()
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "combate_resultado",
                "datos": {"origen": "enemigo", "accion": "aturdido", "enemigo_id": enemigo["enemigo_id"]},
            },
        )
        return False

    resultado = combate_engine.resolver_ataque_enemigo(
        combate, enemigo["enemigo_id"], personaje, muerte_permanente=_usa_muerte_permanente(sala)
    )
    flag_modified(estado, "combate")
    db.commit()
    datos_resultado = {"origen": "enemigo"}
    for clave, valor in resultado.items():
        datos_resultado[clave] = valor
    await gestor.broadcast(str(sala.id), {"tipo": "combate_resultado", "datos": datos_resultado})
    await gestor.broadcast(
        str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
    )

    if await _procesar_posible_muerte(db, sala, personaje):
        return True

    activos = []
    for p in _personajes_no_master(db, sala.id):
        if p.estado == "activo":
            activos.append(p)
    if not activos:
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

    if accion == "atacar":
        resultado = combate_engine.resolver_ataque_jugador(
            combate, personaje, datos["enemigo_id"], personaje.fuerza
        )
        flag_modified(estado, "combate")
        db.commit()
        datos_resultado = {
            "origen": "jugador",
            "personaje_id": str(personaje.id),
            "personaje_nombre": personaje.nombre,
        }
        for clave, valor in resultado.items():
            datos_resultado[clave] = valor
        await gestor.broadcast(str(sala.id), {"tipo": "combate_resultado", "datos": datos_resultado})
        if combate_engine.evaluar_fin_combate(combate) == "victoria":
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual.get("nodo_victoria"))
            return
        if await _reaccion_enemigo(db, sala, combate, estado, personaje, datos["enemigo_id"]):
            return
    elif accion == "huir":
        resultado = resolver_tirada(personaje.agilidad, dificultad=combate.get("dificultad_huida", 12))
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "combate_resultado",
                "datos": {
                    "origen": "jugador",
                    "accion": "huir",
                    "personaje_id": str(personaje.id),
                    "personaje_nombre": personaje.nombre,
                    "tirada": resultado.to_dict(),
                },
            },
        )
        if resultado.exito and nodo_actual.get("nodo_huida"):
            combate["terminado"] = True
            combate["resultado"] = "huida"
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual["nodo_huida"])
            return
        if await _reaccion_enemigo(db, sala, combate, estado, personaje, None):
            return
    elif accion == "negociar":
        resultado = resolver_tirada(personaje.astucia, dificultad=combate.get("dificultad_negociacion", 13))
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "combate_resultado",
                "datos": {
                    "origen": "jugador",
                    "accion": "negociar",
                    "personaje_id": str(personaje.id),
                    "personaje_nombre": personaje.nombre,
                    "tirada": resultado.to_dict(),
                },
            },
        )
        if resultado.exito and nodo_actual.get("nodo_negociacion"):
            combate["terminado"] = True
            combate["resultado"] = "negociacion"
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual["nodo_negociacion"])
            return
        if await _reaccion_enemigo(db, sala, combate, estado, personaje, None):
            return
    elif accion == "objeto":
        try:
            objeto_id = datos["objeto_id"]
        except KeyError:
            await _enviar_error(conexion, "Falta el objeto a usar.")
            return

        # El inventario es común al grupo: el objeto puede estar en el
        # fondo compartido o, por compatibilidad con historias antiguas,
        # en el inventario personal de quien lo usa.
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
            efecto_para_mostrar = {}
            for clave, valor in efecto.items():
                efecto_para_mostrar[clave] = valor
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

        if tipo_efecto == "dano" and combate_engine.evaluar_fin_combate(combate) == "victoria":
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual.get("nodo_victoria"))
            return

        if await _reaccion_enemigo(db, sala, combate, estado, personaje, enemigo_objetivo_id):
            return
    elif accion == "hechizo":
        try:
            hechizo_id = datos["hechizo_id"]
        except KeyError:
            await _enviar_error(conexion, "Falta el hechizo a lanzar.")
            return

        hechizo = hechizos_disponibles(sala.historia.contenido).get(hechizo_id)
        if hechizo is None or hechizo["efecto"] not in (
            "dano_directo",
            "restaura_vida_o_mana",
            "aturdir_enemigo",
        ):
            await _enviar_error(conexion, "Ese hechizo no se puede usar en combate.")
            return
        # Un grimorio equipado presta el hechizo aunque el personaje nunca
        # lo haya aprendido — por eso no basta con mirar hechizos_conocidos.
        grimorio_id = (personaje.hechizo_equipado or {}).get("hechizo_id")
        if hechizo_id not in (personaje.hechizos_conocidos or []) and hechizo_id != grimorio_id:
            await _enviar_error(conexion, "No conoces ese hechizo.")
            return
        if personaje.mana_actual < hechizo["coste_mana"]:
            await _enviar_error(conexion, "No tienes maná suficiente.")
            return

        personaje.mana_actual -= hechizo["coste_mana"]
        resultado_tirada = resolver_tirada(personaje.voluntad, hechizo["dificultad"])
        efecto_aplicado = None
        objetivo_enemigo_id = None

        if hechizo["efecto"] in ("dano_directo", "aturdir_enemigo"):
            objetivo_enemigo_id = datos.get("objetivo_enemigo_id")

        if resultado_tirada.exito:
            if hechizo["efecto"] in ("dano_directo", "aturdir_enemigo"):
                enemigo = combate_engine.enemigo_en_combate(combate, objetivo_enemigo_id or "")
                if enemigo is None:
                    await _enviar_error(conexion, "Ese enemigo no está en el combate.")
                    return
                if hechizo["efecto"] == "dano_directo":
                    dano = max(1, personaje.voluntad // 2 + 2)
                    enemigo["vida"] = max(0, enemigo["vida"] - dano)
                    if enemigo["vida"] == 0:
                        enemigo["derrotado"] = True
                    efecto_aplicado = {"tipo": "dano", "enemigo_id": objetivo_enemigo_id, "dano": dano}
                else:
                    enemigo["aturdido"] = True
                    efecto_aplicado = {"tipo": "aturdido", "enemigo_id": objetivo_enemigo_id}
            else:  # restaura_vida_o_mana
                objetivo_id = datos.get("objetivo_personaje_id")
                try:
                    objetivo = db.get(Personaje, uuid.UUID(objetivo_id)) if objetivo_id else None
                except ValueError:
                    objetivo = None
                if objetivo is None or objetivo.sala_id != sala.id:
                    await _enviar_error(conexion, "Ese objetivo no es válido.")
                    return
                cantidad = 6
                objetivo.vida_actual = min(objetivo.vida_max, objetivo.vida_actual + cantidad)
                efecto_aplicado = {
                    "tipo": "curacion",
                    "personaje_id": str(objetivo.id),
                    "cantidad": cantidad,
                }

        flag_modified(estado, "combate")
        db.commit()
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "combate_resultado",
                "datos": {
                    "origen": "jugador",
                    "accion": "hechizo",
                    "personaje_id": str(personaje.id),
                    "personaje_nombre": personaje.nombre,
                    "hechizo": hechizo["nombre"],
                    "tirada": resultado_tirada.to_dict(),
                    "efecto": efecto_aplicado,
                },
            },
        )
        if hechizo["efecto"] == "dano_directo" and combate_engine.evaluar_fin_combate(combate) == "victoria":
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual.get("nodo_victoria"))
            return

        # El aturdimiento exitoso es justo lo que evita que ese enemigo
        # responda: no tendría sentido consumirlo en el mismo instante en
        # que se aplica.
        aturdido_con_exito = resultado_tirada.exito and hechizo["efecto"] == "aturdir_enemigo"
        if not aturdido_con_exito:
            if await _reaccion_enemigo(db, sala, combate, estado, personaje, objetivo_enemigo_id):
                return
    else:
        await _enviar_error(conexion, f"Acción de combate '{accion}' no reconocida.")
        return

    combate_engine.avanzar_turno(combate)
    flag_modified(estado, "combate")
    db.commit()
    await _avanzar_turnos_invalidos(db, sala)
