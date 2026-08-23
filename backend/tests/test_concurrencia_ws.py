"""Regresión: dos conexiones WebSocket concurrentes deben ver el mismo
estado. Cada conexión abre su propia sesión de SQLAlchemy; con
expire_on_commit=False (necesario para que flag_modified sobreviva a los
commits intermedios del combate) esa sesión no se entera por sí sola de los
cambios que confirma OTRA conexión, a menos que se expire explícitamente al
principio de cada mensaje entrante — justo lo que se probó aquí tras
reproducirlo con dos jugadores reales en el navegador.
"""

import asyncio
import json

import httpx
import websockets


def test_jugador_ve_el_salto_de_nodo_forzado_por_otra_conexion(
    servidor_en_vivo, historia_cuervo_negro
):
    base_url, ws_url = servidor_en_vivo

    async def cuerpo():
        async with httpx.AsyncClient(base_url=base_url) as http:
            resp = await http.post(
                "/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"}
            )
            sala = resp.json()
            codigo = sala["sala"]["codigo"]
            master_token = sala["master_token"]

            resp = await http.post(
                f"/salas/{codigo}/personajes/pregenerado",
                json={"jugador_nombre": "Ana", "personaje_pregenerado_id": "kara_la_espadachina"},
            )
            jugador_token = resp.json()["token"]

        async with websockets.connect(
            f"{ws_url}/ws/sala/{codigo}?token={master_token}"
        ) as ws_master, websockets.connect(
            f"{ws_url}/ws/sala/{codigo}?token={jugador_token}"
        ) as ws_jugador:
            # Drena los mensajes de conexión iniciales de ambos.
            await ws_master.recv()  # estado_inicial
            await ws_master.recv()  # jugador_conectado (él mismo)
            await ws_jugador.recv()  # estado_inicial
            await ws_jugador.recv()  # jugador_conectado (él mismo)
            await ws_master.recv()  # jugador_conectado (por la conexión del jugador)

            # El máster fuerza el salto a un nodo con una palabra clave que
            # solo existe ahí, mientras la conexión del jugador sigue abierta
            # (con su sesión de BD ya cargada desde antes del salto).
            await ws_master.send(json.dumps({"tipo": "override_nodo", "datos": {"nodo_id": "n017"}}))
            await ws_master.recv()  # nodo_actualizado
            await ws_jugador.recv()  # nodo_actualizado (broadcast)

            await ws_jugador.send(json.dumps({
                "tipo": "interactuar",
                "datos": {"palabra_clave": "entregarlo todo a la guardia de la ciudad"},
            }))

            respuesta = json.loads(await ws_jugador.recv())
            assert respuesta["tipo"] != "error", respuesta

    asyncio.run(cuerpo())
