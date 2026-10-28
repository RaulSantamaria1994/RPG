"""Sube (y opcionalmente publica) una historia contra un backend ya
desplegado, sin tocar su repositorio ni redeplegarlo, y sin que la app
necesite ninguna actualización: el máster la ve en cuanto está publicada,
porque el selector de historias ya se consulta en caliente contra el
servidor (`GET /historias`).

Uso:
    python -m app.seeds.publicar_historia archivo.json \
        --url https://tu-backend.example.com \
        --token "$ADMIN_TOKEN" \
        --publicar

Sin `--publicar`, la historia queda subida pero sin publicar (no aparece
en el selector del máster) — útil para probarla primero creando una sala
directamente contra su `historia_id` antes de hacerla visible a cualquiera.
El token de administrador también puede venir de la variable de entorno
ADMIN_TOKEN en vez de `--token`.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="Ruta al JSON de la historia.")
    parser.add_argument("--url", required=True, help="URL base del backend, p. ej. https://rpg-production.up.railway.app")
    parser.add_argument("--token", default=os.environ.get("ADMIN_TOKEN"), help="Token de administrador (o variable ADMIN_TOKEN).")
    parser.add_argument("--publicar", action="store_true", help="Publicarla de inmediato tras subirla.")
    args = parser.parse_args()

    if not args.token:
        print("Falta el token de administrador (--token o variable ADMIN_TOKEN).", file=sys.stderr)
        sys.exit(1)

    contenido = json.loads(args.archivo.read_text(encoding="utf-8"))
    historia_id = contenido.get("historia_id")
    if not historia_id:
        print("El JSON no tiene 'historia_id'.", file=sys.stderr)
        sys.exit(1)

    base_url = args.url.rstrip("/")
    headers = {"X-Admin-Token": args.token}

    respuesta_validar = httpx.post(f"{base_url}/historias/validar", json={"contenido": contenido}, timeout=30)
    respuesta_validar.raise_for_status()
    resultado_validar = respuesta_validar.json()
    if not resultado_validar["valida"]:
        print("La historia no es válida:", file=sys.stderr)
        for error in resultado_validar["errores"]:
            print(" -", error, file=sys.stderr)
        sys.exit(1)

    respuesta_subir = httpx.post(
        f"{base_url}/historias", json={"contenido": contenido}, headers=headers, timeout=30
    )
    if respuesta_subir.status_code == 401:
        print("Token de administrador rechazado por el servidor.", file=sys.stderr)
        sys.exit(1)
    respuesta_subir.raise_for_status()
    subida = respuesta_subir.json()
    print(f"Subida: {subida['titulo']} v{subida['version']} ({subida['historia_id']}), publicada={subida['publicada']}")

    if args.publicar:
        respuesta_publicar = httpx.post(
            f"{base_url}/historias/{historia_id}/publicar", headers=headers, timeout=30
        )
        respuesta_publicar.raise_for_status()
        publicada = respuesta_publicar.json()
        print(f"Publicada: {publicada['titulo']} v{publicada['version']} — ya aparece en el selector del máster.")
    else:
        print("No publicada todavía. Para probarla: crea una sala con historia_id="
              f"'{historia_id}' directamente. Para publicarla: vuelve a correr este "
              "comando con --publicar, o llama a POST /historias/"
              f"{historia_id}/publicar con el token de administrador.")


if __name__ == "__main__":
    main()
