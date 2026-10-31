"""Validación de historias antes de poder activarlas en una sala.

Reglas exigidas por el spec:
  0. La historia declara `motor_version: "pbta-1"` — el esquema viejo
     (dificultad/atributo/modo_interaccion) se rechaza con un error claro
     en vez de dejarlo pasar con un comportamiento indefinido (ver
     docs/motor_pbta_plan.md, secciones 7 y 8).
  1. Todas las referencias (nodo_exito, nodo_fallo, nodo_siguiente y las
     variantes de combate) apuntan a nodos existentes.
  2. No hay nodos huérfanos (inalcanzables desde el nodo inicial).
  3. Todo camino alcanzable termina en al menos un nodo con es_final: true.
  4. Cada palabra clave con `movida` referencia un id del catálogo cerrado
     de movidas del motor; cada enemigo de un nodo de combate declara
     `vida` y `dano` (ficha simplificada, sin atributos ni ataques[]).
"""

from dataclasses import dataclass, field

from app.engine.movidas import MOVIDAS

TIPOS_NODO_VALIDOS = {"interactivo", "narrativo", "combate"}
MOTOR_VERSION_SOPORTADA = "pbta-1"


@dataclass
class ResultadoValidacion:
    valida: bool
    errores: list[str] = field(default_factory=list)


def _referencias_de_nodo(nodo_id: str, nodo: dict) -> set[str]:
    """Devuelve el conjunto de ids de nodo a los que puede saltarse desde `nodo`."""
    refs: set[str] = set()

    if nodo.get("nodo_siguiente"):
        refs.add(nodo["nodo_siguiente"])

    for palabra in nodo.get("palabras_clave", []) or []:
        for campo in ("nodo_exito", "nodo_fallo"):
            if palabra.get(campo):
                refs.add(palabra[campo])

    for campo in ("nodo_victoria", "nodo_derrota", "nodo_huida", "nodo_negociacion"):
        if nodo.get(campo):
            refs.add(nodo[campo])

    return refs


def validar_historia(contenido: dict) -> ResultadoValidacion:
    errores: list[str] = []

    motor_version = contenido.get("motor_version")
    if motor_version != MOTOR_VERSION_SOPORTADA:
        errores.append(
            "Esta historia no es compatible con el motor PbtA: falta o no coincide "
            f"'motor_version' (se esperaba '{MOTOR_VERSION_SOPORTADA}', se encontró "
            f"{motor_version!r}). El esquema viejo (dificultad/atributo/modo_interaccion) "
            "ya no es válido — ver docs/motor_pbta_plan.md."
        )
        return ResultadoValidacion(False, errores)

    nodo_inicial = contenido.get("nodo_inicial")
    nodos: dict = contenido.get("nodos", {}) or {}

    if not nodo_inicial:
        errores.append("Falta 'nodo_inicial'.")
        return ResultadoValidacion(False, errores)

    if not nodos:
        errores.append("La historia no tiene nodos.")
        return ResultadoValidacion(False, errores)

    if nodo_inicial not in nodos:
        errores.append(f"El nodo inicial '{nodo_inicial}' no existe en 'nodos'.")
        return ResultadoValidacion(False, errores)

    for nodo_id, nodo in nodos.items():
        tipo = nodo.get("tipo")
        if tipo not in TIPOS_NODO_VALIDOS:
            errores.append(f"Nodo '{nodo_id}': tipo '{tipo}' no reconocido.")
        if tipo == "interactivo" and not nodo.get("palabras_clave") and not nodo.get("es_final"):
            errores.append(f"Nodo '{nodo_id}': interactivo sin palabras_clave y no es final.")
        if nodo.get("es_final") and not nodo.get("tipo_final"):
            errores.append(f"Nodo '{nodo_id}': es_final=true sin 'tipo_final'.")

        if tipo == "interactivo":
            for palabra in nodo.get("palabras_clave", []) or []:
                movida_id = palabra.get("movida")
                if movida_id is not None and movida_id not in MOVIDAS:
                    errores.append(
                        f"Nodo '{nodo_id}': la palabra clave '{palabra.get('texto')}' "
                        f"referencia una movida desconocida '{movida_id}'."
                    )

        if tipo == "combate":
            for enemigo in nodo.get("enemigos", []) or []:
                enemigo_id = enemigo.get("enemigo_id", "?")
                if "atributos" in enemigo or "ataques" in enemigo:
                    errores.append(
                        f"Nodo '{nodo_id}': el enemigo '{enemigo_id}' usa el esquema de "
                        "combate viejo (atributos/ataques); conviértelo a {vida, dano}."
                    )
                if not isinstance(enemigo.get("vida"), int):
                    errores.append(
                        f"Nodo '{nodo_id}': el enemigo '{enemigo_id}' necesita 'vida' (entero)."
                    )
                if not isinstance(enemigo.get("dano"), int):
                    errores.append(
                        f"Nodo '{nodo_id}': el enemigo '{enemigo_id}' necesita 'dano' (entero)."
                    )

    # 1. Referencias válidas
    edges: dict[str, set[str]] = {}
    for nodo_id, nodo in nodos.items():
        refs = _referencias_de_nodo(nodo_id, nodo)
        edges[nodo_id] = refs
        for ref in refs:
            if ref not in nodos:
                errores.append(f"Nodo '{nodo_id}' referencia a nodo inexistente '{ref}'.")

    # Solo seguimos con el análisis de grafo si todas las referencias son válidas,
    # para no arrastrar errores en cascada sobre ids inventados.
    edges_validas: dict[str, set[str]] = {}
    for nid, refs in edges.items():
        refs_validas: set[str] = set()
        for r in refs:
            if r in nodos:
                refs_validas.add(r)
        edges_validas[nid] = refs_validas
    edges = edges_validas

    # 2. Nodos huérfanos (inalcanzables desde nodo_inicial)
    # 'nodo_muerte_total', si existe, es una raíz aparte: no se llega a él
    # desde ningún nodo_exito/nodo_fallo normal, sino desde el motor de
    # muerte permanente cuando el último personaje con vida muere.
    raices = [nodo_inicial]
    nodo_muerte_total = contenido.get("nodo_muerte_total")
    if nodo_muerte_total:
        if nodo_muerte_total not in nodos:
            errores.append(f"'nodo_muerte_total' referencia a nodo inexistente '{nodo_muerte_total}'.")
        else:
            raices.append(nodo_muerte_total)

    alcanzables: set[str] = set()
    pendientes = list(raices)
    while pendientes:
        actual = pendientes.pop()
        if actual in alcanzables:
            continue
        alcanzables.add(actual)
        for destino in edges.get(actual, set()):
            if destino not in alcanzables:
                pendientes.append(destino)

    huerfanos: set[str] = set()
    for nid in nodos.keys():
        if nid not in alcanzables:
            huerfanos.add(nid)
    for h in sorted(huerfanos):
        errores.append(f"Nodo '{h}' es inalcanzable desde el nodo inicial.")

    # 3. Todo camino alcanzable debe poder llegar a un nodo final
    finales: set[str] = set()
    for nid, n in nodos.items():
        if n.get("es_final"):
            finales.add(nid)
    if not finales:
        errores.append("La historia no tiene ningún nodo final (es_final: true).")

    # Grafo inverso restringido a nodos alcanzables
    inversos: dict[str, set[str]] = {}
    for nid in alcanzables:
        inversos[nid] = set()
    for nid in alcanzables:
        for dest in edges.get(nid, set()):
            if dest in alcanzables:
                inversos.setdefault(dest, set()).add(nid)

    puede_llegar_a_final: set[str] = set()
    pendientes = []
    for f in finales:
        if f in alcanzables:
            pendientes.append(f)
    while pendientes:
        actual = pendientes.pop()
        if actual in puede_llegar_a_final:
            continue
        puede_llegar_a_final.add(actual)
        for origen in inversos.get(actual, set()):
            if origen not in puede_llegar_a_final:
                pendientes.append(origen)

    sin_salida: set[str] = set()
    for nid in alcanzables:
        if nid not in puede_llegar_a_final:
            sin_salida.add(nid)
    for nid in sorted(sin_salida):
        errores.append(f"Nodo '{nid}' no tiene ningún camino hacia un nodo final.")

    return ResultadoValidacion(valida=len(errores) == 0, errores=errores)
