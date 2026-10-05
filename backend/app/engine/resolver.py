"""Motor de resolución de nodos: aplica el resultado de una interacción
(tirada de atributo o de hechizo) sobre el estado de una sala y decide el
nodo destino, siguiendo flags, agotamiento de palabras clave, coste de maná,
consecuencias de fallo, etc.

Estas funciones operan sobre instancias ORM (EstadoSala, Personaje) y las
mutan in-place; quien las llama es responsable de hacer commit.
"""

from sqlalchemy.orm.attributes import flag_modified

from app.engine.dice import ResultadoTirada, resolver_tirada
from app.engine.hechizos_base import hechizos_disponibles
from app.models.estado_sala import EstadoSala
from app.models.personaje import Personaje

ATRIBUTOS_VALIDOS = {"fuerza", "astucia", "voluntad", "agilidad"}


class ErrorInteraccion(Exception):
    """Interacción no permitida (requisitos no cumplidos, ya agotada, etc.)."""


class ManaInsuficiente(ErrorInteraccion):
    pass


def encontrar_nodo(historia_contenido: dict, nodo_id: str) -> dict:
    nodo = historia_contenido.get("nodos", {}).get(nodo_id)
    if nodo is None:
        raise ErrorInteraccion(f"El nodo '{nodo_id}' no existe en la historia.")
    return nodo


def encontrar_palabra_clave(nodo: dict, texto: str) -> dict:
    for palabra in nodo.get("palabras_clave", []) or []:
        if palabra["texto"] == texto:
            return palabra
    raise ErrorInteraccion(f"La palabra clave '{texto}' no existe en este nodo.")


def _clave_palabra(nodo_id: str, palabra_clave: dict) -> str:
    return f"{nodo_id}:{palabra_clave['texto']}"


def verificar_requisitos(
    nodo_id: str, palabra_clave: dict, estado: EstadoSala, personaje: Personaje
) -> None:
    clave = _clave_palabra(nodo_id, palabra_clave)
    if clave in (estado.palabras_clave_usadas or []) and not palabra_clave.get("repetible", False):
        raise ErrorInteraccion("Esta palabra clave ya se ha resuelto y no es repetible.")

    flag_requerido = palabra_clave.get("requiere_flag")
    if flag_requerido and not (estado.flags or {}).get(flag_requerido):
        raise ErrorInteraccion(f"Falta el flag requerido '{flag_requerido}'.")

    objeto_requerido = palabra_clave.get("requiere_objeto")
    if objeto_requerido:
        ids_inventario = {obj.get("objeto_id") for obj in (personaje.inventario or [])}
        ids_grupo = {obj.get("objeto_id") for obj in (estado.inventario_grupo or [])}
        if objeto_requerido not in ids_inventario | ids_grupo:
            raise ErrorInteraccion(f"Falta el objeto requerido '{objeto_requerido}'.")


def _tiene_ventaja(palabra_clave: dict, personaje: Personaje, estado: EstadoSala) -> bool:
    objeto_ventaja = palabra_clave.get("ventaja_si_objeto")
    if not objeto_ventaja:
        return False
    # Igual que verificar_requisitos con requiere_objeto: un objeto de grupo
    # (destino "grupo") también debe contar, no solo el inventario personal.
    ids_inventario = {obj.get("objeto_id") for obj in (personaje.inventario or [])}
    ids_grupo = {obj.get("objeto_id") for obj in (estado.inventario_grupo or [])}
    return objeto_ventaja in ids_inventario | ids_grupo


def resolver_via_atributo(
    palabra_clave: dict,
    personaje: Personaje,
    estado: EstadoSala,
    desventaja: bool = False,
) -> ResultadoTirada:
    atributo = palabra_clave.get("atributo")
    if atributo not in ATRIBUTOS_VALIDOS:
        raise ErrorInteraccion(f"Atributo '{atributo}' no es válido.")
    if not palabra_clave.get("dificultad"):
        raise ErrorInteraccion("Esta palabra clave no admite tirada de atributo.")

    modificador = getattr(personaje, atributo)
    ventaja = _tiene_ventaja(palabra_clave, personaje, estado)
    return resolver_tirada(
        modificador=modificador,
        dificultad=palabra_clave["dificultad"],
        ventaja=ventaja,
        desventaja=desventaja,
    )


def resolver_via_hechizo(
    palabra_clave: dict,
    personaje: Personaje,
    hechizo_id: str,
    historia_contenido: dict,
    estado: EstadoSala,
    desventaja: bool = False,
) -> tuple[ResultadoTirada, dict]:
    hechizos = hechizos_disponibles(historia_contenido)
    hechizo = hechizos.get(hechizo_id)
    if hechizo is None:
        raise ErrorInteraccion(f"El hechizo '{hechizo_id}' no existe.")

    permitido = palabra_clave.get("hechizo_id_alternativo") == hechizo_id or (
        palabra_clave.get("categoria_hechizo_alternativa") == hechizo["categoria"]
    )
    if not permitido:
        raise ErrorInteraccion("Esta palabra clave no admite ese hechizo.")

    if hechizo_id not in (personaje.hechizos_conocidos or []):
        raise ErrorInteraccion("Tu personaje no conoce ese hechizo.")

    coste = hechizo["coste_mana"]
    if personaje.mana_actual < coste:
        raise ManaInsuficiente("No tienes maná suficiente para lanzar este hechizo.")

    # El maná se gasta al lanzar, tenga éxito o no.
    personaje.mana_actual -= coste

    ventaja = _tiene_ventaja(palabra_clave, personaje, estado)
    resultado = resolver_tirada(
        modificador=personaje.voluntad,
        dificultad=hechizo["dificultad"],
        ventaja=ventaja,
        desventaja=desventaja,
    )
    return resultado, hechizo


def _aprender_hechizo(hechizo_id: str, personajes: list[Personaje]) -> None:
    for p in personajes:
        if hechizo_id not in (p.hechizos_conocidos or []):
            conocidos = list(p.hechizos_conocidos or [])
            conocidos.append(hechizo_id)
            p.hechizos_conocidos = conocidos
            flag_modified(p, "hechizos_conocidos")


def otorgar_objeto(
    objeto: dict,
    estado: EstadoSala,
    personaje: Personaje | None,
    destino_defecto: str = "personaje",
    personajes_sala: list[Personaje] | None = None,
) -> dict:
    """Añade un objeto al inventario de grupo o al de `personaje`, según
    `objeto.get("destino", destino_defecto)`. Devuelve el ítem guardado
    (nunca el dict de definición original: solo los campos que de verdad
    viajan al inventario).

    Si `objeto["categoria"] == "hechizo"`, en vez de un objeto físico esto
    otorga la capacidad de lanzar ese hechizo (su `objeto_id` es el id del
    hechizo en el catálogo): se añade a `hechizos_conocidos` de todo el
    grupo (`personajes_sala`), o solo de `personaje` si no se pasa la sala
    completa.
    """
    if objeto.get("categoria") == "hechizo":
        item = {
            "objeto_id": objeto["objeto_id"],
            "nombre": objeto.get("nombre", objeto["objeto_id"]),
            "categoria": "hechizo",
        }
        aprendices = personajes_sala if personajes_sala is not None else ([personaje] if personaje else [])
        _aprender_hechizo(objeto["objeto_id"], aprendices)
        return item

    destino = objeto.get("destino", destino_defecto)
    item = {"objeto_id": objeto["objeto_id"], "nombre": objeto.get("nombre", objeto["objeto_id"])}
    if "categoria" in objeto:
        item["categoria"] = objeto["categoria"]
    if "efecto" in objeto:
        item["efecto"] = objeto["efecto"]
    if "consumible" in objeto:
        item["consumible"] = objeto["consumible"]

    if destino == "grupo" or personaje is None:
        inventario = list(estado.inventario_grupo or [])
        inventario.append(item)
        estado.inventario_grupo = inventario
        flag_modified(estado, "inventario_grupo")
    else:
        inventario = list(personaje.inventario or [])
        inventario.append(item)
        personaje.inventario = inventario
        flag_modified(personaje, "inventario")
    return item


def aplicar_resultado(
    nodo_id: str,
    palabra_clave: dict,
    exito: bool,
    estado: EstadoSala,
    personaje: Personaje,
    muerte_permanente: bool = False,
    personajes_sala: list[Personaje] | None = None,
) -> dict:
    """Aplica flags/objetos/agotamiento tras resolver una tirada y determina
    el nodo destino. Devuelve un resumen de los cambios aplicados.

    Si `muerte_permanente` está activo y el daño deja al personaje a 0 de
    vida, su estado pasa a "muerto" (definitivo) en vez de "inconsciente".
    """
    cambios: dict = {"flags_aplicados": {}, "objeto_otorgado": None, "dano_aplicado": 0}

    clave_dano = "dano_exito" if exito else "dano_fallo"
    dano = palabra_clave.get(clave_dano)
    if dano:
        cantidad = dano.get("cantidad", 0)
        personaje.vida_actual = max(0, personaje.vida_actual - cantidad)
        if personaje.vida_actual == 0:
            personaje.estado = "muerto" if muerte_permanente else "inconsciente"
        cambios["dano_aplicado"] = cantidad

    flags = dict(estado.flags or {})
    clave_flags = "flags_set_exito" if exito else "flags_set_fallo"
    nuevos_flags = palabra_clave.get(clave_flags) or {}
    if nuevos_flags:
        flags.update(nuevos_flags)
        estado.flags = flags
        flag_modified(estado, "flags")
        cambios["flags_aplicados"] = nuevos_flags

    if exito:
        objeto = palabra_clave.get("objeto_otorga_exito")
        if objeto:
            cambios["objeto_otorgado"] = otorgar_objeto(
                objeto, estado, personaje, personajes_sala=personajes_sala
            )

    if not palabra_clave.get("repetible", False):
        usadas = list(estado.palabras_clave_usadas or [])
        usadas.append(_clave_palabra(nodo_id, palabra_clave))
        estado.palabras_clave_usadas = usadas
        flag_modified(estado, "palabras_clave_usadas")

    nodo_destino = palabra_clave["nodo_exito"] if exito else palabra_clave["nodo_fallo"]
    cambios["nodo_destino"] = nodo_destino
    return cambios


def avanzar_a_nodo(
    estado: EstadoSala,
    historia_contenido: dict,
    nodo_id: str,
    personajes_sala: list[Personaje] | None = None,
) -> dict:
    """Mueve el estado de sala al nodo indicado, aplicando descanso narrativo
    y marcando la partida como finalizada si corresponde. Devuelve un resumen.
    """
    nodo = encontrar_nodo(historia_contenido, nodo_id)
    estado.nodo_actual_id = nodo_id

    resumen = {"nodo": nodo, "descanso": False, "final": False, "tipo_final": None, "objetos_otorgados": []}

    # Cualquier tipo de nodo (narrativo, interactivo o de combate) puede
    # otorgar objetos solo por llegar a él — a diferencia de
    # `objeto_otorga_exito` (ligado al éxito de una palabra clave concreta),
    # esto es un regalo del propio nodo al grupo entero. Si la categoría es
    # "hechizo", `otorgar_objeto` lo convierte en aprendizaje para todo el
    # grupo en vez de un objeto físico.
    for objeto in nodo.get("objetos_otorgados", []) or []:
        resumen["objetos_otorgados"].append(
            otorgar_objeto(objeto, estado, None, destino_defecto="grupo", personajes_sala=personajes_sala)
        )

    if nodo.get("punto_descanso"):
        resumen["descanso"] = True

    if nodo.get("es_final"):
        estado.finalizada = True
        estado.tipo_final = nodo.get("tipo_final")
        resumen["final"] = True
        resumen["tipo_final"] = nodo.get("tipo_final")

    if nodo.get("tipo") == "combate":
        estado.fase = "combate"
    else:
        estado.fase = "exploracion"
        estado.combate = None

    return resumen


def aplicar_descanso(estado: EstadoSala, personajes: list[Personaje], nodo: dict) -> None:
    """Restaura maná (y opcionalmente vida) de todos los personajes de la sala."""
    tipo = nodo.get("restaura", "total")
    for personaje in personajes:
        if tipo == "total":
            personaje.mana_actual = personaje.mana_max
            personaje.vida_actual = personaje.vida_max
        else:
            mitad_mana = max(0, (personaje.mana_max - personaje.mana_actual) // 2)
            personaje.mana_actual = min(personaje.mana_max, personaje.mana_actual + mitad_mana)
