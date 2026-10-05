"""Endpoint WebSocket de sala: un socket por jugador conectado, un canal de
difusión por sala. Aquí vive el flujo central del spec: nodo -> interacción
-> tirada -> nodo, con foco/bloqueo de palabras clave, tiradas combinadas,
combate reactivo (el enemigo responde a la acción del jugador, sin turno
propio) y overrides del máster.
"""

import secrets
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
    marcado como ausentes, o quienes ya hayan muerto de forma permanente."""
    return [p for p in _personajes_no_master(db, sala_id) if p.estado not in ("ausente", "muerto")]


def _usa_muerte_permanente(sala: Sala) -> bool:
    """La muerte definitiva solo se activa si el máster la eligió al crear
    la sala Y la historia define a dónde saltar cuando muere el último
    personaje con vida (no todas las historias tienen ese epílogo escrito)."""
    return bool(sala.muerte_permanente) and bool(sala.historia.contenido.get("nodo_muerte_total"))


def _texto_epilogo_tetrico(sala: Sala, personaje: Personaje) -> str:
    contenido = sala.historia.contenido
    epilogos = contenido.get("desenlaces_tetricos") or {}
    clave = personaje.personaje_pregenerado_id
    return (
        (clave and epilogos.get(clave))
        or contenido.get("desenlace_tetrico_generico")
        or f"{personaje.nombre} cae, y su historia termina aquí."
    )


async def _procesar_posible_muerte(db, sala: Sala, personaje: Personaje) -> bool:
    """Si `personaje` acaba de morir de forma permanente, notifica su
    desenlace personal (el resto del grupo sigue jugando) o, si era el
    último con vida, hace saltar la partida entera al epílogo de muerte
    total. Devuelve True si la partida ya se resolvió por esa vía, para
    que el llamador no siga avanzando nodos por su cuenta."""
    if personaje.estado != "muerto":
        return False

    otros_vivos = any(
        p.estado != "muerto"
        for p in _personajes_no_master(db, sala.id)
        if p.id != personaje.id
    )
    if otros_vivos:
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "personaje_muerto",
                "datos": {
                    "personaje_id": str(personaje.id),
                    "personaje_nombre": personaje.nombre,
                    "epilogo": _texto_epilogo_tetrico(sala, personaje),
                },
            },
        )
        return False

    await _avanzar_y_notificar(db, sala, sala.historia.contenido["nodo_muerte_total"])
    return True


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

    if resumen["objetos_otorgados"]:
        await gestor.broadcast(
            str(sala.id),
            {
                "tipo": "objetos_otorgados",
                "datos": {"objetos": resumen["objetos_otorgados"], "destino": "grupo"},
            },
        )

    await _broadcast_nodo(sala)

    if resumen["nodo"].get("tipo") == "combate":
        await _avanzar_turnos_invalidos(db, sala)


async def _avanzar_turnos_invalidos(db, sala: Sala) -> None:
    """Salta los turnos de personajes inactivos (ausentes, inconscientes o
    muertos) hasta llegar a uno que pueda actuar. Los enemigos ya no tienen
    turno propio: responden de inmediato a la acción del jugador implicado
    (ver `_reaccion_enemigo`), así que aquí solo se ordena el turno entre
    jugadores. Si ninguno puede actuar, el combate se da por perdido.
    """
    estado = sala.estado_sala
    combate = estado.combate
    if not combate or combate.get("terminado"):
        return

    personajes = {str(p.id): p for p in _personajes_no_master(db, sala.id)}
    total = len(combate["orden_iniciativa"])

    for _ in range(total):
        id_turno = combate["orden_iniciativa"][combate["turno_index"]].split(":", 1)[1]
        personaje = personajes.get(id_turno)
        if personaje is not None and personaje.estado == "activo":
            break
        combate_engine.avanzar_turno(combate)
    else:
        combate["terminado"] = True
        combate["resultado"] = "derrota"

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
    await gestor.broadcast(
        str(sala.id), {"tipo": "combate_resultado", "datos": {"origen": "enemigo", **resultado}}
    )
    await gestor.broadcast(
        str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
    )

    if await _procesar_posible_muerte(db, sala, personaje):
        return True

    activos = [p for p in _personajes_no_master(db, sala.id) if p.estado == "activo"]
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
        elif not palabra.get("dificultad"):
            # Decisión de personaje sin tirada: quien confirma, decide. Mismo
            # atajo que ya existe en _resolver_grupal para "grupal, sin dificultad".
            tirada_payload = {"exito": True, "sin_tirada": True}
        else:
            resultado = resolver_via_atributo(palabra, personaje, estado, desventaja)
            tirada_payload = resultado.to_dict()

        exito = tirada_payload["exito"]

        cambios = aplicar_resultado(
            nodo_id, palabra, exito, estado, personaje, muerte_permanente=_usa_muerte_permanente(sala)
        )
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
        if cambios.get("dano_aplicado"):
            await gestor.broadcast(
                str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
            )

        if await _procesar_posible_muerte(db, sala, personaje):
            return

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
    """Una palabra clave en modo "grupal" se resuelve de dos formas
    distintas según lleve dificultad o no:

    - Con dificultad: es una prueba conjunta (todos intentan lo mismo a la
      vez), así que se exige que todos confirmen esa misma acción antes de
      tirar los dados — ver `_resolver_grupal_tirada`.
    - Sin dificultad: es una decisión narrativa entre varias opciones
      (las demás palabras clave en modo "grupal" sin dificultad de este
      mismo nodo), así que se resuelve por votación — ver
      `_resolver_grupal_voto`.
    """
    if palabra.get("dificultad"):
        await _resolver_grupal_tirada(db, sala, conexion, personaje, nodo_id, palabra, datos)
    else:
        await _resolver_grupal_voto(db, sala, conexion, personaje, nodo_id, palabra, datos)


async def _resolver_grupal_tirada(
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

    cambios = aplicar_resultado(
        nodo_id, palabra, exito, estado, personaje, muerte_permanente=_usa_muerte_permanente(sala)
    )
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
    if cambios.get("dano_aplicado"):
        await gestor.broadcast(
            str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
        )

    if await _procesar_posible_muerte(db, sala, personaje):
        return

    await _avanzar_y_notificar(db, sala, cambios["nodo_destino"])


def _opciones_grupales_sin_dificultad(nodo: dict) -> list[dict]:
    """Las palabras clave en modo grupal sin dificultad de un mismo nodo
    forman, juntas, una única decisión por votación."""
    return [
        p
        for p in nodo.get("palabras_clave", []) or []
        if p.get("modo_interaccion") == "grupal" and not p.get("dificultad")
    ]


async def _resolver_grupal_voto(
    db, sala: Sala, conexion: ConexionJugador, personaje: Personaje, nodo_id: str, palabra: dict, datos: dict
) -> None:
    nodo = encontrar_nodo(sala.historia.contenido, nodo_id)
    opciones = _opciones_grupales_sin_dificultad(nodo)

    votos = gestor.registrar_voto(str(sala.id), nodo_id, str(personaje.id), palabra["texto"])
    total = len(_personajes_confirmables(db, sala.id))

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "voto_registrado",
            "datos": {
                "personaje_id": str(personaje.id),
                "personaje_nombre": personaje.nombre,
                "opcion": palabra["texto"],
                "votados": len(votos),
                "total": total,
            },
        },
    )

    if len(votos) < total:
        return

    gestor.limpiar_votos(str(sala.id), nodo_id)

    recuento: dict[str, int] = {}
    for texto_elegido in votos.values():
        recuento[texto_elegido] = recuento.get(texto_elegido, 0) + 1
    maximo = max(recuento.values())
    ganadoras = sorted(texto for texto, n in recuento.items() if n == maximo)
    empate = len(ganadoras) > 1
    texto_ganador = ganadoras[secrets.randbelow(len(ganadoras))] if empate else ganadoras[0]
    palabra_ganadora = next((p for p in opciones if p["texto"] == texto_ganador), palabra)

    estado = sala.estado_sala
    cambios = aplicar_resultado(
        nodo_id, palabra_ganadora, True, estado, personaje, muerte_permanente=_usa_muerte_permanente(sala)
    )
    db.commit()

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "votacion_resuelta",
            "datos": {"recuento": recuento, "empate": empate, "opcion_ganadora": texto_ganador},
        },
    )
    if cambios.get("dano_aplicado"):
        await gestor.broadcast(
            str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
        )

    if await _procesar_posible_muerte(db, sala, personaje):
        return

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
        if personaje.estado == "muerto":
            raise ErrorInteraccion("Tu personaje ha caído: ya no puede actuar.")
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
    cambios = aplicar_resultado(
        nodo_id, palabra, exito, estado, personaje, muerte_permanente=_usa_muerte_permanente(sala)
    )
    db.commit()

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

    if await _procesar_posible_muerte(db, sala, personaje):
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
        if await _reaccion_enemigo(db, sala, combate, estado, personaje, datos["enemigo_id"]):
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
        if await _reaccion_enemigo(db, sala, combate, estado, personaje, None):
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
        objeto = next((o for o in inventario_grupo if o.get("objeto_id") == objeto_id), None)
        origen = "grupo" if objeto is not None else None
        if objeto is None:
            objeto = next((o for o in inventario_personal if o.get("objeto_id") == objeto_id), None)
            origen = "personal" if objeto is not None else None

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
            if origen == "grupo":
                inventario_grupo.remove(objeto)
                estado.inventario_grupo = inventario_grupo
                flag_modified(estado, "inventario_grupo")
            else:
                inventario_personal.remove(objeto)
                personaje.inventario = inventario_personal
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
        if origen == "grupo":
            await _broadcast_nodo(sala)
        if await _reaccion_enemigo(db, sala, combate, estado, personaje, None):
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
        if hechizo_id not in (personaje.hechizos_conocidos or []):
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
