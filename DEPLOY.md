# Desplegar el backend en Railway

Guía para dejar el backend corriendo en un servidor externo (Railway) en vez de en tu propio ordenador, para que la partida no dependa de que tengas el PC encendido.

El repo ya trae lo necesario para esto: `backend/Dockerfile` construye la imagen, y el arranque del contenedor aplica las migraciones y carga las historias de ejemplo solo si hace falta — no hay ningún paso manual aparte la primera vez.

## 1. Crear el proyecto en Railway

1. Entra en [railway.app](https://railway.app) y conecta tu cuenta de GitHub.
2. **New Project → Deploy from GitHub repo** → elige este repositorio.
3. Railway crea un servicio para todo el repo. Como es un monorepo (backend + app), dile dónde está el backend: en el servicio, **Settings → Root Directory** → `backend`. En cuanto detecte el `Dockerfile` ahí, lo usará para construir en vez de intentar adivinar el stack.

## 2. Añadir la base de datos

1. En el mismo proyecto, **+ New → Database → Add PostgreSQL**.
2. En el servicio del backend, **Variables** → añade `DATABASE_URL` referenciando la del plugin: `${{Postgres.DATABASE_URL}}` (Railway te la sugiere al escribir `$`). No hace falta tocar nada más: el backend normaliza automáticamente el esquema `postgres://`/`postgresql://` que da Railway al formato que necesita internamente.

## 3. Variables de entorno del backend

En **Variables** del servicio backend:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (paso anterior) |
| `JWT_SECRET` | Un valor propio y largo — **nunca** el `dev-secret-change-me` del repo. Genera uno con `openssl rand -hex 32`, por ejemplo. |

El resto de variables (`codigo_sala_longitud`, `sala_expiracion_dias`, etc.) tienen valores por defecto razonables; solo hace falta tocarlas si quieres cambiar ese comportamiento.

## 4. Desplegar y obtener la URL pública

1. Railway despliega en cuanto guardas las variables. Sigue el log de build/deploy desde la pestaña **Deployments**.
2. Si no te asigna dominio público solo, **Settings → Networking → Generate Domain**. Te da algo como `tu-proyecto.up.railway.app`, con HTTPS ya incluido.
3. Comprueba que responde: `https://tu-proyecto.up.railway.app/salud` debe devolver `{"estado":"ok"}`.

## 5. Apuntar la app ahí

- **Web** (`expo start --web` o una build web): define `EXPO_PUBLIC_API_URL=https://tu-proyecto.up.railway.app` y `EXPO_PUBLIC_API_WS_URL=wss://tu-proyecto.up.railway.app` antes de arrancar/compilar. Importante: `wss://`, no `ws://` — el dominio de Railway sirve HTTPS, así que el WebSocket tiene que ser seguro también.
- **APK**: usa el workflow ya existente (`Actions → Build Android APK → Run workflow`) rellenando esos mismos dos valores en `api_url` y `api_ws_url`.

## Notas

- El nivel gratuito de Railway es limitado y a partir de ahí se paga por uso — de sobra para una partida entre amigos, pero conviene revisar los precios actuales en su web antes de dejarlo corriendo de forma indefinida.
- Cada redeploy vuelve a ejecutar migraciones y carga de historias; ambas son seguras de repetir (no duplican ni rompen nada si ya están al día).
- Si alguna vez quieres mover esto a un VPS propio en vez de Railway, el mismo `backend/Dockerfile` sirve de base — solo cambia cómo le das la URL pública y el TLS (ahí sí hace falta nginx/Caddy + certificado, que Railway resuelve solo).
