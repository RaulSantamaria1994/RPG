"""Motor de resolución de nodos: aplica el resultado de una movida (o de un
hechizo) sobre el estado de una sala y decide el nodo destino, siguiendo
flags, agotamiento de palabras clave, coste de maná, coste de un 7-9,
consecuencias de fallo, etc.

Estas funciones operan sobre instancias ORM (EstadoSala, Personaje) y las
mutan in-place; quien las llama es responsable de hacer commit.
"""

from sqlalchemy.orm.attributes import flag_modified

from app.engine.dice import Banda, ResultadoTirada, resolver_tirada
from app.engine.hechizos_base import hechizos_disponibles
from app.engine.movidas import MOVIDAS, modificador_de
from app.models.estado_sala import EstadoSala
from app.models.personaje import Personaje


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
        tiene_el_objeto = False
        for obj in personaje.inventario or []:
            if obj.get("objeto_id") == objeto_requerido:
                tiene_el_objeto = True
        for obj in estado.inventario_grupo or []:
            if obj.get("objeto_id") == objeto_requerido:
                tiene_el_objeto = True
        if not tiene_el_objeto:
            raise ErrorInteraccion(f"Falta el objeto requerido '{objeto_requerido}'.")


def resolver_via_movida(
    palabra_clave: dict, personaje: Personaje, usar_suerte: bool = False, bono: int = 0
) -> ResultadoTirada:
    """Resuelve la movida referenciada por la palabra clave: 2d6 +
    modificador de la característica de esa movida (+ `bono`, p. ej. el +1
    de que te haya ayudado otro personaje). Si `usar_suerte` y el resultado
    sale fallo, y al personaje le quedan Puntos de Suerte, gasta uno y
    convierte el fallo en éxito limpio (ver docs/motor_pbta_plan.md, sección
    4). Si el resultado ya era éxito, el punto no se gasta."""
    movida_id = palabra_clave.get("movida")
    movida = MOVIDAS.get(movida_id)
    if movida is None:
        raise ErrorInteraccion(f"La movida '{movida_id}' no existe.")
    caracteristica = movida["caracteristica"]
    if caracteristica is None:
        raise ErrorInteraccion(f"La movida '{movida_id}' no se resuelve con una tirada normal.")

    resultado = resolver_tirada(modificador_de(personaje, caracteristica) + bono)

    if usar_suerte and resultado.banda == Banda.FALLO and personaje.puntos_suerte_actual > 0:
        personaje.puntos_suerte_actual -= 1
        resultado = ResultadoTirada(
            dados=resultado.dados,
            modificador=resultado.modificador,
            total=resultado.total,
            banda=Banda.EXITO,
        )
    return resultado


def resolver_ayudar(personaje: Personaje) -> ResultadoTirada:
    """Movida 'ayudar a otro': tirada aparte, sin característica propia. Si
    no sale fallo, quien ayuda da +1 a la tirada de quien actúa (ver
    `interaccion.py`, que consume ese bono)."""
    return resolver_tirada(modificador=0)


def resolver_via_hechizo(
    palabra_clave: dict,
    personaje: Personaje,
    hechizo_id: str,
    historia_contenido: dict,
) -> tuple[ResultadoTirada, dict]:
    """Los hechizos quedan fuera del alcance de la reestructuración a PbtA
    (ver docs/motor_pbta_plan.md, sección 7): se adaptan lo mínimo para
    seguir funcionando con el dado nuevo (2d6 + voluntad, mismas bandas que
    cualquier otra movida), sin rediseñar el subsistema."""
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

    resultado = resolver_tirada(modificador_de(personaje, "voluntad"))
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
        if personajes_sala is not None:
            aprendices = personajes_sala
        elif personaje:
            aprendices = [personaje]
        else:
            aprendices = []
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
    # Solo relevantes para lo equipable (ver `_manejar_equipar_objeto` en
    # websockets/handlers/intercambio.py): sin copiarlos aquí, un arma, una
    # armadura o un grimorio otorgados por la propia historia llegarían al
    # inventario sin su bono de daño, su reducción de daño, o sin saber qué
    # hechizo prestan.
    if "bono_dano" in objeto:
        item["bono_dano"] = objeto["bono_dano"]
    if "reduccion_dano" in objeto:
        item["reduccion_dano"] = objeto["reduccion_dano"]
    if "hechizo_id" in objeto:
        item["hechizo_id"] = objeto["hechizo_id"]

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


def aplicar_dano(personaje: Personaje, cantidad: int, muerte_permanente: bool = False) -> int:
    """Resta `cantidad` de la barra de daño de 7 puntos, descontando antes
    la reducción de la armadura equipada (nunca por debajo de 0). Devuelve
    el daño realmente aplicado, ya con la armadura descontada."""
    reduccion = (personaje.armadura_equipada or {}).get("reduccion_dano", 0)
    cantidad_real = max(0, cantidad - reduccion)
    personaje.vida_actual = max(0, personaje.vida_actual - cantidad_real)
    if personaje.vida_actual == 0:
        personaje.estado = "muerto" if muerte_permanente else "inconsciente"
    return cantidad_real


def aplicar_resultado(
    nodo_id: str,
    palabra_clave: dict,
    resultado: ResultadoTirada,
    estado: EstadoSala,
    personaje: Personaje,
    muerte_permanente: bool = False,
    personajes_sala: list[Personaje] | None = None,
) -> dict:
    """Aplica el coste de un 7-9, flags/objetos/agotamiento, y determina el
    nodo destino. El 10+ y el 7-9 llevan los dos a `nodo_exito` (un 7-9 es
    éxito, solo que con coste); únicamente el 6- lleva a `nodo_fallo`.
    Devuelve un resumen de los cambios aplicados."""
    cambios: dict = {"flags_aplicados": {}, "objeto_otorgado": None, "dano_aplicado": 0}
    exito = resultado.exito

    if resultado.banda == Banda.EXITO_CON_COSTE:
        movida = MOVIDAS.get(palabra_clave.get("movida"), {})
        coste = palabra_clave.get("coste_parcial", movida.get("coste_parcial_defecto"))
        if coste and coste.get("tipo") == "dano":
            cambios["dano_aplicado"] += aplicar_dano(
                personaje, coste.get("cantidad", 1), muerte_permanente
            )

    if resultado.banda == Banda.FALLO:
        dano_fallo = palabra_clave.get("dano_fallo")
        if dano_fallo:
            cambios["dano_aplicado"] += aplicar_dano(
                personaje, dano_fallo.get("cantidad", 1), muerte_permanente
            )

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
    cambios["banda"] = resultado.banda.value
    return cambios


def aplicar_dano_al_llegar(
    nodo: dict, personajes_sala: list[Personaje] | None, muerte_permanente: bool = False
) -> dict | None:
    """Si el nodo define `dano_al_llegar`, resta esa cantidad de la barra de
    daño de todo el grupo con solo llegar a él — una trampa, una caída, un
    peligro narrativo — sin que medie ninguna tirada. A diferencia del coste
    de un 7-9 o de `dano_fallo` (ligados al resultado de una palabra clave
    concreta de un nodo interactivo), esto puede darse en cualquier tipo de
    nodo. Devuelve quién resultó afectado, o None si no hay nada que aplicar.
    """
    dano = nodo.get("dano_al_llegar")
    if not dano or not personajes_sala:
        return None
    cantidad = dano.get("cantidad", 0)
    afectados = []
    for p in personajes_sala:
        if p.estado == "muerto":
            continue
        aplicar_dano(p, cantidad, muerte_permanente)
        afectados.append(str(p.id))
    if not afectados:
        return None
    return {"cantidad": cantidad, "afectados": afectados}


def avanzar_a_nodo(
    estado: EstadoSala,
    historia_contenido: dict,
    nodo_id: str,
    personajes_sala: list[Personaje] | None = None,
    muerte_permanente: bool = False,
) -> dict:
    """Mueve el estado de sala al nodo indicado, aplicando descanso narrativo
    y marcando la partida como finalizada si corresponde. Devuelve un resumen.
    """
    nodo = encontrar_nodo(historia_contenido, nodo_id)
    estado.nodo_actual_id = nodo_id

    resumen = {
        "nodo": nodo,
        "descanso": False,
        "final": False,
        "tipo_final": None,
        "objetos_otorgados": [],
        "dano_al_llegar": None,
    }

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

    resumen["dano_al_llegar"] = aplicar_dano_al_llegar(nodo, personajes_sala, muerte_permanente)

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
