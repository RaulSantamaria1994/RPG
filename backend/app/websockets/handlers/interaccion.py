"""Mensajes `interactuar` y `continuar`: resolución de palabras clave
(individual, en apoyo, grupal por tirada o por votación) y el avance
narrativo automático de un nodo sin palabras clave propias.
"""

import secrets
import uuid

from sqlalchemy.orm.attributes import flag_modified

from app.engine.dice import resolver_tirada, resolver_tirada_opuesta
from app.engine.resolver import (
    ErrorInteraccion,
    ManaInsuficiente,
    aplicar_resultado,
    encontrar_nodo,
    encontrar_palabra_clave,
    resolver_via_atributo,
    resolver_via_hechizo,
    verificar_requisitos,
)
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.websockets.comun import (
    _avanzar_y_notificar,
    _enviar_error,
    _filtrar_confirmables,
    _personajes_no_master,
    _personaje_publico,
    _procesar_posible_muerte,
    _usa_muerte_permanente,
)
from app.websockets.manager import ConexionJugador, gestor


def _clave_palabra(nodo_id: str, texto: str) -> str:
    return f"{nodo_id}:{texto}"


def _faltan_jugadores_para_empezar(db, sala: Sala) -> int:
    """Cuántos jugadores faltan por unirse para alcanzar `sala.min_jugadores`
    (0 o menos significa que ya se puede jugar). Cuenta todo personaje creado
    en la sala, esté ausente o muerto o no: lo que importa aquí es cuánta
    gente se apuntó a la partida, no quién sigue activo en este momento."""
    return sala.min_jugadores - len(_personajes_no_master(db, sala.id))


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

        personajes_sala = _personajes_no_master(db, sala.id)
        cambios = aplicar_resultado(
            nodo_id,
            palabra,
            exito,
            estado,
            personaje,
            muerte_permanente=_usa_muerte_permanente(sala),
            personajes_sala=personajes_sala,
        )
        db.commit()

        cambios_para_mostrar = {}
        for k, v in cambios.items():
            if k != "nodo_destino":
                cambios_para_mostrar[k] = v

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
                    "cambios": cambios_para_mostrar,
                },
            },
        )
        if cambios.get("dano_aplicado"):
            await gestor.broadcast(
                str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(personaje)}
            )
        if (cambios.get("objeto_otorgado") or {}).get("categoria") == "hechizo":
            for p in personajes_sala:
                await gestor.broadcast(
                    str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(p)}
                )

        if await _procesar_posible_muerte(db, sala, personaje, personajes_sala):
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
    personajes_sala = _personajes_no_master(db, sala.id)
    participantes = _filtrar_confirmables(personajes_sala)
    total = len(participantes)

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
    resultados = []
    for p in participantes:
        tirada_de_p = resolver_tirada(getattr(p, palabra["atributo"]), palabra["dificultad"]).to_dict()
        fila_resultado = {"personaje": p.nombre}
        for clave, valor in tirada_de_p.items():
            fila_resultado[clave] = valor
        resultados.append(fila_resultado)

    if regla == "todos_aciertan":
        exito = True
        for r in resultados:
            if not r["exito"]:
                exito = False
    else:
        exito = False
        for r in resultados:
            if r["exito"]:
                exito = True
    tirada_payload = {"resultados": resultados, "regla": regla, "exito": exito}

    cambios = aplicar_resultado(
        nodo_id,
        palabra,
        exito,
        estado,
        personaje,
        muerte_permanente=_usa_muerte_permanente(sala),
        personajes_sala=participantes,
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
    if (cambios.get("objeto_otorgado") or {}).get("categoria") == "hechizo":
        for p in participantes:
            await gestor.broadcast(
                str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(p)}
            )

    if await _procesar_posible_muerte(db, sala, personaje, personajes_sala):
        return

    await _avanzar_y_notificar(db, sala, cambios["nodo_destino"])


def _opciones_grupales_sin_dificultad(nodo: dict) -> list[dict]:
    """Las palabras clave en modo grupal sin dificultad de un mismo nodo
    forman, juntas, una única decisión por votación."""
    opciones = []
    for p in nodo.get("palabras_clave", []) or []:
        if p.get("modo_interaccion") == "grupal" and not p.get("dificultad"):
            opciones.append(p)
    return opciones


async def _resolver_grupal_voto(
    db, sala: Sala, conexion: ConexionJugador, personaje: Personaje, nodo_id: str, palabra: dict, datos: dict
) -> None:
    nodo = encontrar_nodo(sala.historia.contenido, nodo_id)
    opciones = _opciones_grupales_sin_dificultad(nodo)

    votos = gestor.registrar_voto(str(sala.id), nodo_id, str(personaje.id), palabra["texto"])
    personajes_sala = _personajes_no_master(db, sala.id)
    total = len(_filtrar_confirmables(personajes_sala))

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
    ganadoras = []
    for texto, n in recuento.items():
        if n == maximo:
            ganadoras.append(texto)
    ganadoras.sort()
    empate = len(ganadoras) > 1
    if empate:
        texto_ganador = ganadoras[secrets.randbelow(len(ganadoras))]
    else:
        texto_ganador = ganadoras[0]

    palabra_ganadora = palabra
    for p in opciones:
        if p["texto"] == texto_ganador:
            palabra_ganadora = p

    estado = sala.estado_sala
    cambios = aplicar_resultado(
        nodo_id,
        palabra_ganadora,
        True,
        estado,
        personaje,
        muerte_permanente=_usa_muerte_permanente(sala),
        personajes_sala=personajes_sala,
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
    if (cambios.get("objeto_otorgado") or {}).get("categoria") == "hechizo":
        for p in personajes_sala:
            await gestor.broadcast(
                str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(p)}
            )

    if await _procesar_posible_muerte(db, sala, personaje, personajes_sala):
        return

    await _avanzar_y_notificar(db, sala, cambios["nodo_destino"])


async def _manejar_interactuar(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol == "master":
        await _enviar_error(conexion, "El máster no interactúa directamente con palabras clave.")
        return

    faltan = _faltan_jugadores_para_empezar(db, sala)
    if faltan > 0:
        if faltan == 1:
            terminacion_falta = ""
        else:
            terminacion_falta = "n"
        await _enviar_error(
            conexion,
            f"Hacen falta al menos {sala.min_jugadores} jugadores para empezar a jugar "
            f"(falta{terminacion_falta} {faltan}).",
        )
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
    faltan = _faltan_jugadores_para_empezar(db, sala)
    if faltan > 0:
        if faltan == 1:
            terminacion_falta = ""
        else:
            terminacion_falta = "n"
        await _enviar_error(
            conexion,
            f"Hacen falta al menos {sala.min_jugadores} jugadores para empezar a jugar "
            f"(falta{terminacion_falta} {faltan}).",
        )
        return

    estado = sala.estado_sala
    nodo = encontrar_nodo(sala.historia.contenido, estado.nodo_actual_id)
    if nodo.get("tipo") != "narrativo" or not nodo.get("nodo_siguiente"):
        await _enviar_error(conexion, "No hay un nodo siguiente automático desde aquí.")
        return
    await _avanzar_y_notificar(db, sala, nodo["nodo_siguiente"])
