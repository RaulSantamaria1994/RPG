"""Mensajes `interactuar` y `continuar`: resolución de una movida (o, si la
palabra clave no referencia ninguna, una decisión simple sin tirada), de la
movida "ayudar a otro" por separado, y el avance narrativo automático de un
nodo sin palabras clave propias.
"""

import uuid

from sqlalchemy.orm.attributes import flag_modified

from app.engine.dice import Banda, ResultadoTirada
from app.engine.resolver import (
    ErrorInteraccion,
    ManaInsuficiente,
    aplicar_resultado,
    encontrar_nodo,
    encontrar_palabra_clave,
    resolver_ayudar,
    resolver_via_hechizo,
    resolver_via_movida,
    verificar_requisitos,
)
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.websockets.comun import (
    _avanzar_y_notificar,
    _enviar_error,
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


async def _resolver_ayudar(
    db, sala: Sala, conexion: ConexionJugador, personaje: Personaje, nodo_id: str, palabra: dict
) -> None:
    """Movida 'ayudar a otro': una tirada aparte, sin bloquear la palabra
    clave principal. Si no sale fallo, deja un +1 marcado para quien
    resuelva esa misma palabra clave a continuación (ver `_resolver_movida`,
    que lo consume una sola vez)."""
    clave = _clave_palabra(nodo_id, palabra["texto"])
    estado = sala.estado_sala
    resultado = resolver_ayudar(personaje)

    if resultado.exito:
        flags = dict(estado.flags or {})
        flags[f"__ayuda__{clave}"] = True
        estado.flags = flags
        flag_modified(estado, "flags")
        db.commit()

    await gestor.broadcast(
        str(sala.id),
        {
            "tipo": "ayuda_resuelta",
            "datos": {
                "personaje_id": str(personaje.id),
                "personaje_nombre": personaje.nombre,
                "palabra_clave": palabra["texto"],
                "tirada": resultado.to_dict(),
            },
        },
    )


async def _resolver_movida(
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

        usar_suerte = bool(datos.get("usar_suerte", False))

        if datos.get("via") == "hechizo":
            resultado, hechizo = resolver_via_hechizo(
                palabra, personaje, datos["hechizo_id"], sala.historia.contenido
            )
            tirada_payload = resultado.to_dict()
            tirada_payload["hechizo"] = hechizo["nombre"]
        else:
            flags = dict(estado.flags or {})
            bono_ayuda = 1 if flags.pop(f"__ayuda__{clave}", None) else 0
            if bono_ayuda:
                estado.flags = flags
                flag_modified(estado, "flags")

            resultado = resolver_via_movida(palabra, personaje, usar_suerte=usar_suerte, bono=bono_ayuda)
            tirada_payload = resultado.to_dict()

        personajes_sala = _personajes_no_master(db, sala.id)
        cambios = aplicar_resultado(
            nodo_id,
            palabra,
            resultado,
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
                    "exito": resultado.exito,
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


async def _resolver_decidir(
    db, sala: Sala, conexion: ConexionJugador, personaje: Personaje, nodo_id: str, palabra: dict
) -> None:
    """Una palabra clave sin `movida` no se tira: es una decisión narrativa
    (p. ej. qué camino seguir). Quien la confirma, decide — el motor ya no
    cuenta votos (ver docs/motor_pbta_plan.md, sección 0): el grupo lo
    habla fuera del sistema, y uno de ellos pulsa la opción acordada."""
    estado = sala.estado_sala
    resultado = ResultadoTirada(dados=(0, 0), modificador=0, total=0, banda=Banda.EXITO)

    personajes_sala = _personajes_no_master(db, sala.id)
    cambios = aplicar_resultado(
        nodo_id,
        palabra,
        resultado,
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

    if datos.get("rol_apoyo") == "apoyo":
        await _resolver_ayudar(db, sala, conexion, personaje, nodo_id, palabra)
        return

    # Lanzar un hechizo siempre pasa por la tirada (ver resolver_via_hechizo
    # en resolver.py), aunque la palabra clave no referencie ninguna movida.
    if palabra.get("movida") or datos.get("via") == "hechizo":
        await _resolver_movida(db, sala, conexion, personaje, nodo_id, palabra, datos)
    else:
        await _resolver_decidir(db, sala, conexion, personaje, nodo_id, palabra)


async def _manejar_continuar(db, sala: Sala, conexion: ConexionJugador, datos: dict) -> None:
    if conexion.rol != "master":
        await _enviar_error(conexion, "Solo el máster puede avanzar un nodo narrativo.")
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
    nodo = encontrar_nodo(sala.historia.contenido, estado.nodo_actual_id)
    if nodo.get("tipo") != "narrativo" or not nodo.get("nodo_siguiente"):
        await _enviar_error(conexion, "No hay un nodo siguiente automático desde aquí.")
        return
    await _avanzar_y_notificar(db, sala, nodo["nodo_siguiente"])
