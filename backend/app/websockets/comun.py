"""Núcleo compartido por todos los manejadores de mensajes de sala: estado
público, avance de nodo, turnos de combate inválidos y procesamiento de
muerte. Estas piezas se llaman unas a otras (p. ej. `_procesar_posible_muerte`
puede terminar llamando a `_avanzar_y_notificar`, que a su vez puede llamar
de vuelta a `_procesar_posible_muerte` tras daño al llegar a un nodo), así
que viven juntas en un solo módulo en vez de repartidas por dominio.
"""

from sqlalchemy.orm.attributes import flag_modified

from app.engine import combate as combate_engine
from app.engine.resolver import aplicar_descanso, avanzar_a_nodo
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.websockets.manager import ConexionJugador, gestor


def _personajes_no_master(db, sala_id) -> list[Personaje]:
    return (
        db.query(Personaje)
        .filter(Personaje.sala_id == sala_id, Personaje.es_master.is_(False))
        .all()
    )


def _filtrar_confirmables(personajes: list[Personaje]) -> list[Personaje]:
    """Todos menos quienes el máster haya marcado como ausentes, o quienes ya
    hayan muerto de forma permanente — ver `_personajes_confirmables`."""
    confirmables = []
    for p in personajes:
        if p.estado not in ("ausente", "muerto"):
            confirmables.append(p)
    return confirmables


def _personajes_confirmables(db, sala_id) -> list[Personaje]:
    """Personajes que cuentan para tiradas grupales y para el orden de
    iniciativa de un combate nuevo. Si ya tienes la lista completa de la
    sala en memoria, usa `_filtrar_confirmables` directamente en vez de
    volver a consultar la base de datos."""
    return _filtrar_confirmables(_personajes_no_master(db, sala_id))


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


async def _procesar_posible_muerte(
    db, sala: Sala, personaje: Personaje, personajes_sala: list[Personaje] | None = None
) -> bool:
    """Si `personaje` acaba de morir de forma permanente, notifica su
    desenlace personal (el resto del grupo sigue jugando) o, si era el
    último con vida, hace saltar la partida entera al epílogo de muerte
    total. Devuelve True si la partida ya se resolvió por esa vía, para
    que el llamador no siga avanzando nodos por su cuenta.

    Si el llamador ya tiene la lista de personajes de la sala en memoria
    (recién consultada en esta misma petición), pásala en `personajes_sala`
    para no repetir la consulta."""
    if personaje.estado != "muerto":
        return False

    if personajes_sala is not None:
        resto_del_equipo = personajes_sala
    else:
        resto_del_equipo = _personajes_no_master(db, sala.id)

    otros_vivos = False
    for p in resto_del_equipo:
        if p.id != personaje.id and p.estado != "muerto":
            otros_vivos = True
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


def _diario_pistas(sala: Sala, flags: dict) -> list[dict]:
    """Traduce las flags narrativas activas a un registro legible de "lo que
    sabéis", en el orden en que se fueron descubriendo (el mismo orden de
    inserción de `flags`, que Python preserva). Las flags internas (ya
    excluidas de `flags` por `_estado_publico`) y las que la historia no
    documenta en `pistas` no generan entrada — siguen existiendo como
    mecanismo de desbloqueo, pero no todas tienen por qué ser una pista
    legible para el grupo.
    """
    pistas = sala.historia.contenido.get("pistas") or {}
    diario = []
    for k, v in flags.items():
        if v and k in pistas:
            diario.append({"flag": k, "texto": pistas[k]})
    return diario


def _estado_publico(sala: Sala) -> dict:
    estado = sala.estado_sala
    nodo = sala.historia.contenido["nodos"][estado.nodo_actual_id]
    flags = {}
    for k, v in (estado.flags or {}).items():
        if not k.startswith("__"):
            flags[k] = v
    return {
        "nodo_actual_id": estado.nodo_actual_id,
        "nodo": nodo,
        "flags": flags,
        "diario": _diario_pistas(sala, flags),
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
        "arma_equipada": p.arma_equipada,
        "hechizo_equipado": p.hechizo_equipado,
        "estado": p.estado,
        "fuerza": p.fuerza,
        "astucia": p.astucia,
        "voluntad": p.voluntad,
        "agilidad": p.agilidad,
    }


async def _enviar_error(conexion: ConexionJugador, mensaje: str, **extra) -> None:
    datos_error = {"mensaje": mensaje}
    for clave, valor in extra.items():
        datos_error[clave] = valor
    await gestor.enviar_a(conexion, {"tipo": "error", "datos": datos_error})


async def _broadcast_nodo(sala: Sala) -> None:
    await gestor.broadcast(
        str(sala.id), {"tipo": "nodo_actualizado", "datos": _estado_publico(sala)}
    )


async def _avanzar_y_notificar(db, sala: Sala, nodo_id: str) -> None:
    estado = sala.estado_sala
    personajes_sala = _personajes_no_master(db, sala.id)
    resumen = avanzar_a_nodo(
        estado,
        sala.historia.contenido,
        nodo_id,
        personajes_sala=personajes_sala,
        muerte_permanente=_usa_muerte_permanente(sala),
    )

    if resumen["descanso"]:
        aplicar_descanso(estado, personajes_sala, resumen["nodo"])

    if resumen["nodo"].get("tipo") == "combate":
        combate = combate_engine.iniciar_combate(resumen["nodo"], _filtrar_confirmables(personajes_sala))
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
        algun_objeto_es_hechizo = False
        for o in resumen["objetos_otorgados"]:
            if o.get("categoria") == "hechizo":
                algun_objeto_es_hechizo = True
        if algun_objeto_es_hechizo:
            for p in personajes_sala:
                await gestor.broadcast(
                    str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(p)}
                )

    if resumen["dano_al_llegar"]:
        dano_info = resumen["dano_al_llegar"]
        await gestor.broadcast(str(sala.id), {"tipo": "dano_al_llegar", "datos": dano_info})
        afectados_ids = set(dano_info["afectados"])
        afectados = []
        for p in personajes_sala:
            if str(p.id) in afectados_ids:
                afectados.append(p)
        for p in afectados:
            await gestor.broadcast(
                str(sala.id), {"tipo": "personaje_actualizado", "datos": _personaje_publico(p)}
            )
        for p in afectados:
            if p.estado == "muerto" and await _procesar_posible_muerte(db, sala, p, personajes_sala):
                return

    await _broadcast_nodo(sala)

    if resumen["nodo"].get("tipo") == "combate":
        await _avanzar_turnos_invalidos(db, sala)


async def _avanzar_turnos_invalidos(db, sala: Sala) -> None:
    """Salta los turnos de personajes inactivos (ausentes, inconscientes o
    muertos) hasta llegar a uno que pueda actuar. Los enemigos ya no tienen
    turno propio: responden de inmediato a la acción del jugador implicado
    (ver `_reaccion_enemigo` en handlers/combate.py), así que aquí solo se
    ordena el turno entre jugadores. Si ninguno puede actuar, el combate se
    da por perdido.
    """
    estado = sala.estado_sala
    combate = estado.combate
    if not combate or combate.get("terminado"):
        return

    personajes = {}
    for p in _personajes_no_master(db, sala.id):
        personajes[str(p.id)] = p
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
