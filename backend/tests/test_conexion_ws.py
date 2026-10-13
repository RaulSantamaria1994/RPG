"""Los códigos de cierre propios del handshake del WebSocket de sala no
tenían ninguna prueba: token ilegible (4401), sala inexistente o token de
otra sala (4404 en sus dos variantes: código inexistente, y token válido
pero de una sala distinta).
"""

import pytest
from starlette.websockets import WebSocketDisconnect


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_token_ilegible_cierra_con_4401(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    with client.websocket_connect(f"/ws/sala/{codigo}?token=esto-no-es-un-jwt") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4401


def test_sala_inexistente_cierra_con_4404(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)

    with client.websocket_connect(f"/ws/sala/ZZZZZZ?token={sala['master_token']}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4404


def test_token_de_otra_sala_cierra_con_4404(client, historia_cuervo_negro):
    sala_a = _crear_sala(client, historia_cuervo_negro)
    sala_b = _crear_sala(client, historia_cuervo_negro)

    # El token del máster de A es válido (firma correcta) pero su sala_id
    # no es la de B: no puede colarse en la sala de otro con él.
    with client.websocket_connect(
        f"/ws/sala/{sala_b['sala']['codigo']}?token={sala_a['master_token']}"
    ) as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4404
