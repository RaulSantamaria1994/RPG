"""Endpoint WebSocket de sala: un socket por jugador conectado, un canal de
difusión por sala. Aquí vive el flujo central del spec: nodo -> interacción
-> tirada -> nodo, con foco/bloqueo de palabras clave, tiradas combinadas,
combate por rondas y overrides del máster.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm.attributes import flag_modified

from app.database import SessionLocal
from app.engine import combate as combate_engine
from app.engine.dice import resolver_tirada, resolver_tirada_opuesta
from app.engine.hechizos_base import hechizos_disponibles
from app.engine.resolver import (
    ErrorInteraccion,
    ManaInsuficiente,
    aplicar_descanso,
    aplicar_resultado,
    avanzar_a_nodo,
    encontrar_nodo,
    encontrar_palabra_clave,
    resolver_via_atributo,
    resolver_via_hechizo,
    verificar_requisitos,
)
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.security import decodificar_token
from app.websockets.manager import ConexionJugador, gestor

router = APIRouter()


def _clave_palabra(nodo_id: str, texto: str) -> str:
    return f"{nodo_id}:{texto}"


def _personajes_no_master(db, sala_id) -> list[Personaje]:
    return (
        db.query(Personaje)
        .filter(Personaje.sala_id == sala_id, Personaje.es_master.is_(False))
        .all()
    )


def _personajes_confirmables(db, sala_id) -> list[Personaje]:
    """Personajes que cuentan para tiradas grupales y para el orden de
    iniciativa de un combate nuevo: todos menos quienes el máster haya
    marcado como ausentes."""
    return [p for p in _personajes_no_master(db, sala_id) if p.estado != "ausente"]


def _estado_publico(sala: Sala) -> dict:
    estado = sala.estado_sala
    nodo = sala.historia.contenido["nodos"][estado.nodo_actual_id]
    return {
        "nodo_actual_id": estado.nodo_actual_id,
        "nodo": nodo,
        "flags": {k: v for k, v in (estado.flags or {}).items() if not k.startswith("__")},
        "palabras_clave_usadas": estado.palabras_clave_usadas,
        "inventario_grupo": estado.inventario_grupo,
        "fase": estado.fase,
        "combate": estado.combate,
        "finalizada": estado.finalizada,
        "tipo_final": estado.tipo_final,
    }


def _personaje_publico(p: Personaje) -> dict:
    return {
        "id": str(p.id),
        "nombre": p.nombre,
        "jugador_nombre": p.jugador_nombre,
        "vida_actual": p.vida_actual,
        "vida_max": p.vida_max,
        "mana_actual": p.mana_actual,
        "mana_max": p.mana_max,
        "inventario": p.inventario,
        "hechizos_conocidos": p.hechizos_conocidos,
        "rasgos": p.rasgos,
        "estado": p.estado,
        "fuerza": p.fuerza,
        "astucia": p.astucia,
        "voluntad": p.voluntad,
        "agilidad": p.agilidad,
    }


async def _enviar_error(conexion: ConexionJugador, mensaje: str) -> None:
    await gestor.enviar_a(conexion, {"tipo": "error", "datos": {"mensaje": mensaje}})


async def _broadcast_nodo(sala: Sala) -> None:
    await gestor.broadcast(
        str(sala.id), {"tipo": "nodo_actualizado", "datos": _estado_publico(sala)}
    )


async def _avanzar_y_notificar(db, sala: Sala, nodo_id: str) -> None:
    estado = sala.estado_sala
    resumen = avanzar_a_nodo(estado, sala.historia.contenido, nodo_id)

    if resumen["descanso"]:
        aplicar_descanso(estado, _personajes_no_master(db, sala.id), resumen["nodo"])

    if resumen["nodo"].get("tipo") == "combate":
        combate = combate_engine.iniciar_combate(resumen["nodo"], _personajes_confirmables(db, sala.id))
        estado.combate = combate
        flag_modified(estado, "combate")

    db.commit()
    await _broadcast_nodo(sala)

    if resumen["nodo"].get("tipo") == "combate":
        await _avanzar_turnos_invalidos(db, sala)


def _elegir_objetivo(personajes: list[Personaje]) -> Personaje | None:
    activos = [p for p in personajes if p.estado == "activo"]
    if not activos:
        return None
    return min(activos, key=lambda p: p.vida_actual)


async def _avanzar_turnos_invalidos(db, sala: Sala) -> None:
    """Resuelve automáticamente los turnos que no requieren acción de un
    jugador real: ataques de enemigos, enemigos derrotados, enemigos
    aturdidos y turnos de personajes inactivos (ausentes o inconscientes).
    Se detiene en cuanto llega a un turno de un personaje que sí puede
    actuar, o cuando el combate termina.
    """
    estado = sala.estado_sala
    combate = estado.combate
    if not combate or combate.get("terminado"):
        return

    personajes = {str(p.id): p for p in _personajes_no_master(db, sala.id)}

    while not combate["terminado"]:
        entrada = combate["orden_iniciativa"][combate["turno_index"]]
        tipo_turno, id_turno = entrada.split(":", 1)

        if tipo_turno == "enemigo":
            enemigo = combate_engine.enemigo_en_combate(combate, id_turno)
            if enemigo is None or enemigo["derrotado"]:
                combate_engine.avanzar_turno(combate)
                continue

            if enemigo.get("aturdido"):
                enemigo["aturdido"] = False
                flag_modified(estado, "combate")
                db.commit()
                await gestor.broadcast(
                    str(sala.id),
                    {
                        "tipo": "combate_resultado",
                        "datos": {"origen": "enemigo", "accion": "aturdido", "enemigo_id": id_turno},
                    },
                )
                combate_engine.avanzar_turno(combate)
                continue

            objetivo = _elegir_objetivo(list(personajes.values()))
            if objetivo is None:
                combate["terminado"] = True
                combate["resultado"] = "derrota"
                break

            resultado = combate_engine.resolver_ataque_enemigo(combate, id_turno, objetivo)
            flag_modified(estado, "combate")
            db.commit()
            await gestor.broadcast(
                str(sala.id), {"tipo": "combate_resultado", "datos": {"origen": "enemigo", **resultado}}
            )

            if all(p.estado != "activo" for p in personajes.values()):
                combate["terminado"] = True
                combate["resultado"] = "derrota"
                break

            combate_engine.avanzar_turno(combate)
        else:
            personaje = personajes.get(id_turno)
            if personaje is None or personaje.estado != "activo":
                combate_engine.avanzar_turno(combate)
                continue
            break  # turno válido de un jugador activo: se espera su acción

    flag_modified(estado, "combate")
    db.commit()

    if combate.get("terminado"):
        nodo_actual = sala.historia.contenido["nodos"][estado.nodo_actual_id]
        destino_map = {
            "victoria": nodo_actual.get("nodo_victoria"),
            "derrota": nodo_actual.get("nodo_derrota"),
        }
        destino = destino_map.get(combate["resultado"])
        if destino:
            await _avanzar_y_notificar(db, sala, destino)
        else:
            await _broadcast_nodo(sala)
    else:
        await _broadcast_nodo(sala)


async def _resolver_individual(
    db, sala: Sala, conexion: ConexionJugador, personaje: Personaje, nodo_id: str, palabra: dict, datos: dict
) -> None:
    clave = _clave_palabra(nodo_id, palabra["texto"])
    if not gestor.bloquear_palabra(str(sala.id), clave, personaje.nombre):
        await _enviar_error(conexion, "Otro jugador ya está resolviendo esa acción.")
        return

    await gestor.broadcast(
        str(sala.id),
        {"tipo": "palabra_clave_bloqueada", "datos": {"clave": clave, "jugador": personaje.nombre}},
    )

    try:
        estado = sala.estado_sala
        verificar_requisitos(nodo_id, palabra, estado, personaje)

        desventaja = bool(datos.get("desventaja", False))
        via = datos.get("via", "atributo")

        flags = dict(estado.flags or {})
        ventaja_apoyo = flags.pop(f"__apoyo__{clave}", None)
        if ventaja_apoyo is not None:
            estado.flags = flags
            flag_modified(estado, "flags")

        if via == "hechizo":
            resultado, hechizo = resolver_via_hechizo(
                palabra, personaje, datos["hechizo_id"], sala.historia.contenido, estado, desventaja
            )
            tirada_payload = resultado.to_dict()
            tirada_payload["hechizo"] = hechizo["nombre"]
        elif palabra.get("modo_interaccion") == "opuesta":
            npc_mod = palabra.get("npc_modificador", 0)
            tirada_payload = resolver_tirada_opuesta(getattr(personaje, palabra["atributo"]), npc_mod)
        else:
            resultado = resolver_via_atributo(palabra, personaje, estado, desventaja)
            tirada_payload = resultado.to_dict()

        exito = tirada_payload["exito"]

        cambios = aplicar_resultado(nodo_id, palabra, exito, estado, personaje)
        db.commit()

        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "tirada_resultado",
                "datos": {
                    "personaje_id": str(personaje.id),
                    "personaje_nombre": personaje.nombre,
                    "palabra_clave": palabra["texto"],
                    "tirada": tirada_payload,
                    "exito": exito,
                    "cambios": {k: v for k, v in cambios.items() if k != "nodo_destino"},
                },
            },
        )

        await _avanzar_y_notificar(db, sala, cambios["nodo_destino"])
    except (ErrorInteraccion, ManaInsuficiente) as exc:
        await _enviar_error(conexion, str(exc))
    finally:
        gestor.liberar_palabra(str(sala.id), clave)
        await gestor.broadcast(
            str(sala.id), {"tipo": "palabra_clave_liberada", "datos": {"clave": clave}}
        )


async def _resolver_apoyo(
    db, sala: Sala, conexion: ConexionJugador, personaje: Personaje, nodo_id: str, palabra: dict, datos: dict
) -> None:
    clave = _clave_palabra(nodo_id, palabra["texto"])
    rol_intento = datos.get("rol_apoyo", "principal")
    estado = sala.estado_sala

    if rol_intento == "apoyo":
        atributo_apoyo = palabra.get("atributo_apoyo")
        dificultad_apoyo = palabra.get("dificultad_apoyo", palabra.get("dificultad", 10))
        resultado = resolver_tirada(getattr(personaje, atributo_apoyo), dificultad_apoyo)

        flags = dict(estado.flags or {})
        if resultado.exito:
            flags[f"__apoyo__{clave}"] = True
            estado.flags = flags
            flag_modified(estado, "flags")
            db.commit()

        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "apoyo_resuelto",
                "datos": {
                    "personaje_id": str(personaje.id),
                    "personaje_nombre": personaje.nombre,
                    "palabra_clave": palabra["texto"],
                    "tirada": resultado.to_dict(),
                },
            },
        )
        return

    await _resolver_individual(db, sala, conexion, personaje, nodo_id, palabra, datos)


async def _resolver_grupal(
    db, sala: Sala, conexion: ConexionJugador, personaje: Personaje, nodo_id: str, palabra: dict, datos: dict
) -> None:
    clave = _clave_palabra(nodo_id, palabra["texto"])
    confirmaciones = gestor.registrar_confirmacion(str(sala.id), clave, str(personaje.id))
    total = len(_personajes_confirmables(db, sala.id))

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "confirmacion_registrada",
            "datos": {"clave": clave, "confirmados": len(confirmaciones), "total": total},
        },
    )

    if len(confirmaciones) < total:
        return

    gestor.limpiar_confirmaciones(str(sala.id), clave)
    estado = sala.estado_sala

    if palabra.get("dificultad"):
        regla = palabra.get("regla_grupal", "mejor_resultado")
        participantes = _personajes_confirmables(db, sala.id)
        resultados = [
            {"personaje": p.nombre, **resolver_tirada(getattr(p, palabra["atributo"]), palabra["dificultad"]).to_dict()}
            for p in participantes
        ]
        exito = (
            all(r["exito"] for r in resultados)
            if regla == "todos_aciertan"
            else any(r["exito"] for r in resultados)
        )
        tirada_payload = {"resultados": resultados, "regla": regla, "exito": exito}
    else:
        exito = True
        tirada_payload = {"exito": True, "sin_tirada": True}

    cambios = aplicar_resultado(nodo_id, palabra, exito, estado, personaje)
    db.commit()

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "tirada_resultado",
            "datos": {
                "palabra_clave": palabra["texto"],
                "tirada": tirada_payload,
                "exito": exito,
                "modo": "grupal",
            },
        },
    )
    await _avanzar_y_notificar(db, sala, cambios["nodo_destino"])


async def _manejar_interactuar(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol == "master":
        await _enviar_error(conexion, "El máster no interactúa directamente con palabras clave.")
        return

    estado = sala.estado_sala
    nodo_id = estado.nodo_actual_id
    try:
        nodo = encontrar_nodo(sala.historia.contenido, nodo_id)
        if nodo.get("tipo") == "combate":
            raise ErrorInteraccion("Este nodo es de combate: usa la acción de combate.")
        palabra = encontrar_palabra_clave(nodo, datos["palabra_clave"])
        personaje = db.get(Personaje, uuid.UUID(conexion.personaje_id))
        if personaje is None:
            raise ErrorInteraccion("Tu personaje ya no existe en esta sala.")
        if personaje.estado == "ausente":
            raise ErrorInteraccion(
                "Estás marcado como ausente: pide al máster que te reactive para poder actuar."
            )
        verificar_requisitos(nodo_id, palabra, estado, personaje)
    except (ErrorInteraccion, KeyError) as exc:
        await _enviar_error(conexion, str(exc) if isinstance(exc, ErrorInteraccion) else "Datos incompletos.")
        return

    modo = palabra.get("modo_interaccion", "individual")
    if modo == "grupal":
        await _resolver_grupal(db, sala, conexion, personaje, nodo_id, palabra, datos)
    elif modo == "apoyo":
        await _resolver_apoyo(db, sala, conexion, personaje, nodo_id, palabra, datos)
    else:
        await _resolver_individual(db, sala, conexion, personaje, nodo_id, palabra, datos)


async def _manejar_continuar(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    estado = sala.estado_sala
    nodo = encontrar_nodo(sala.historia.contenido, estado.nodo_actual_id)
    if nodo.get("tipo") != "narrativo" or not nodo.get("nodo_siguiente"):
        await _enviar_error(conexion, "No hay un nodo siguiente automático desde aquí.")
        return
    await _avanzar_y_notificar(db, sala, nodo["nodo_siguiente"])


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

    exito = bool(datos.get("exito", True))
    cambios = aplicar_resultado(nodo_id, palabra, exito, estado, personaje)
    db.commit()

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "tirada_resultado",
            "datos": {"palabra_clave": palabra["texto"], "exito": exito, "override_master": True},
        },
    )
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

    personaje.estado = "activo"
    db.commit()
    await gestor.broadcast(
        str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
    )


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
        await gestor.broadcast(
            str(sala.id), {"tipo": "combate_resultado", "datos": {"origen": "jugador", **resultado}}
        )
        if combate_engine.evaluar_fin_combate(combate) == "victoria":
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual.get("nodo_victoria"))
            return
    elif accion == "huir":
        resultado = resolver_tirada(personaje.agilidad, dificultad=combate.get("dificultad_huida", 12))
        await gestor.broadcast(
            str(sala.id),
            {"tipo": "combate_resultado", "datos": {"origen": "jugador", "accion": "huir", "tirada": resultado.to_dict()}},
        )
        if resultado.exito and nodo_actual.get("nodo_huida"):
            combate["terminado"] = True
            combate["resultado"] = "huida"
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual["nodo_huida"])
            return
    elif accion == "negociar":
        resultado = resolver_tirada(personaje.astucia, dificultad=combate.get("dificultad_negociacion", 13))
        await gestor.broadcast(
            str(sala.id),
            {"tipo": "combate_resultado", "datos": {"origen": "jugador", "accion": "negociar", "tirada": resultado.to_dict()}},
        )
        if resultado.exito and nodo_actual.get("nodo_negociacion"):
            combate["terminado"] = True
            combate["resultado"] = "negociacion"
            flag_modified(estado, "combate")
            db.commit()
            await _avanzar_y_notificar(db, sala, nodo_actual["nodo_negociacion"])
            return
    elif accion == "objeto":
        try:
            objeto_id = datos["objeto_id"]
        except KeyError:
            await _enviar_error(conexion, "Falta el objeto a usar.")
            return
        inventario = list(personaje.inventario or [])
        objeto = next((o for o in inventario if o.get("objeto_id") == objeto_id), None)
        efecto = (objeto or {}).get("efecto") or {}
        if objeto is None or efecto.get("tipo") not in ("curar_vida", "curar_mana"):
            await _enviar_error(conexion, "Ese objeto no se puede usar en combate.")
            return

        cantidad = efecto.get("cantidad", 0)
        if efecto["tipo"] == "curar_vida":
            personaje.vida_actual = min(personaje.vida_max, personaje.vida_actual + cantidad)
        else:
            personaje.mana_actual = min(personaje.mana_max, personaje.mana_actual + cantidad)

        if objeto.get("consumible", True):
            inventario.remove(objeto)
            personaje.inventario = inventario
            flag_modified(personaje, "inventario")

        db.commit()
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "combate_resultado",
                "datos": {
                    "origen": "jugador",
                    "accion": "objeto",
                    "personaje_id": str(personaje.id),
                    "objeto": objeto,
                    "efecto": efecto,
                },
            },
        )
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
        if hechizo_id not in (personaje.hechizos_conocidos or []):
            await _enviar_error(conexion, "No conoces ese hechizo.")
            return
        if personaje.mana_actual < hechizo["coste_mana"]:
            await _enviar_error(conexion, "No tienes maná suficiente.")
            return

        personaje.mana_actual -= hechizo["coste_mana"]
        resultado_tirada = resolver_tirada(personaje.voluntad, hechizo["dificultad"])
        efecto_aplicado = None

        if resultado_tirada.exito:
            if hechizo["efecto"] in ("dano_directo", "aturdir_enemigo"):
                enemigo_id = datos.get("objetivo_enemigo_id")
                enemigo = combate_engine.enemigo_en_combate(combate, enemigo_id or "")
                if enemigo is None:
                    await _enviar_error(conexion, "Ese enemigo no está en el combate.")
                    return
                if hechizo["efecto"] == "dano_directo":
                    dano = max(1, personaje.voluntad // 2 + 2)
                    enemigo["vida"] = max(0, enemigo["vida"] - dano)
                    if enemigo["vida"] == 0:
                        enemigo["derrotado"] = True
                    efecto_aplicado = {"tipo": "dano", "enemigo_id": enemigo_id, "dano": dano}
                else:
                    enemigo["aturdido"] = True
                    efecto_aplicado = {"tipo": "aturdido", "enemigo_id": enemigo_id}
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
                    "hechizo": hechizo["nombre"],
                    "tirada": resultado_tirada.to_dict(),
                    "efecto": efecto_aplicado,
                },
            },
        )
        if combate_engine.evaluar_fin_combate(combate) == "victoria":
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
    await _broadcast_nodo(sala)
    await _avanzar_turnos_invalidos(db, sala)


async def _manejar_intercambio_proponer(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    origen = db.get(Personaje, uuid.UUID(conexion.personaje_id))
    objeto = next(
        (o for o in (origen.inventario or []) if o.get("objeto_id") == datos["objeto_id"]), None
    )
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
                "objeto_id": datos["objeto_id"],
                "objeto_nombre": objeto.get("nombre", datos["objeto_id"]),
                "destino_personaje_id": datos["destino_personaje_id"],
            },
        },
    )


async def _manejar_intercambio_confirmar(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    origen = db.get(Personaje, uuid.UUID(datos["origen_personaje_id"]))
    destino = db.get(Personaje, uuid.UUID(conexion.personaje_id))
    objeto_id = datos["objeto_id"]

    inventario_origen = list(origen.inventario or [])
    objeto = next((o for o in inventario_origen if o.get("objeto_id") == objeto_id), None)
    if objeto is None:
        await _enviar_error(conexion, "Ese objeto ya no está disponible.")
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


MANEJADORES = {
    "interactuar": _manejar_interactuar,
    "continuar": _manejar_continuar,
    "override_nodo": _manejar_override_nodo,
    "override_resultado": _manejar_override_resultado,
    "marcar_ausente": _manejar_marcar_ausente,
    "marcar_activo": _manejar_marcar_activo,
    "combate_accion": _manejar_combate_accion,
    "intercambio_proponer": _manejar_intercambio_proponer,
    "intercambio_confirmar": _manejar_intercambio_confirmar,
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

    conexion = ConexionJugador(
        websocket=websocket, personaje_id=payload.personaje_id, nombre=payload.nombre, rol=payload.rol
    )

    try:
        gestor.conectar(str(sala.id), conexion)
        sala.ultima_actividad_en = datetime.now(timezone.utc)
        db.commit()
        await gestor.enviar_a(
            conexion,
            {
                "tipo": "estado_inicial",
                "datos": {
                    "sala": {"codigo": sala.codigo, "nombre": sala.nombre, "titulo_historia": sala.historia.titulo},
                    **_estado_publico(sala),
                    "personajes": [_personaje_publico(p) for p in _personajes_no_master(db, sala.id)],
                },
            },
        )
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
            # _resolver_turnos_enemigos) esta sesión nunca ve por sí sola los cambios que
            # confirman OTRAS conexiones (p. ej. el máster forzando un salto de nodo).
            # Expirar todo al principio de cada mensaje fuerza a releer de BD.
            db.expire_all()

            manejador = MANEJADORES.get(tipo)
            if manejador is None:
                await _enviar_error(conexion, f"Tipo de mensaje '{tipo}' no reconocido.")
                continue

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
