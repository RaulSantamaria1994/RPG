# El ala norte — RPG narrativo cooperativo

Un juego de rol narrativo cooperativo, de ambientación lovecraftiana, para jugar en grupo desde el móvil o el navegador. Un jugador hace de **máster** (narra, ajusta la partida, fuerza saltos de nodo si hace falta) y el resto son **jugadores**, cada uno con su propio personaje, mientras la historia avanza en tiempo real para todos a la vez por WebSocket.

No hay dados físicos ni fichas de papel: las tiradas, el combate, el inventario compartido, los hechizos y el equipo se resuelven en el servidor y se reflejan al instante en la pantalla de cada participante.

## Características

- **Historias por nodos**: cada historia es un grafo de nodos narrativos, interactivos y de combate, con palabras clave, tiradas de atributo, flags narrativas y finales múltiples.
- **Combate por turnos**: atacar, huir, negociar, usar objetos o lanzar hechizos, con reacción automática del enemigo y animaciones propias para cada tipo de acción.
- **Equipo**: cada jugador puede llevar un arma (bono de daño) y un hechizo/grimorio equipados desde el inventario común de la sala.
- **Inventario personal y de grupo**, con intercambio de objetos entre jugadores.
- **Herramientas de máster**: ajustar vida/maná, marcar jugadores ausentes, expulsar, forzar el salto a cualquier nodo, forzar el resultado de una tirada, cerrar la sala o regenerar su código.
- **Reconexión robusta**: el cliente detecta la caída de la conexión, reintenta solo y recupera el estado de la partida al volver — nadie pierde su sitio por un corte de red.
- **Tres historias de ejemplo** incluidas: *El ala norte*, *El Cuervo Negro* y *Frecuencia Negra*.

## Arquitectura

| | |
|---|---|
| **Backend** | FastAPI + PostgreSQL, WebSocket para el estado de partida en vivo, REST para sesión/autenticación |
| **Frontend** | Expo / React Native (Android, iOS y Web desde el mismo código), Zustand para el estado de cliente |

```
backend/   API FastAPI, motor del juego, modelos SQLAlchemy, migraciones Alembic, historias de ejemplo
app/       Cliente Expo / React Native (pantallas de jugador, de máster, y componentes compartidos)
```

## Cómo se juega

1. El máster crea una sala eligiendo una historia; recibe un código de 6 caracteres para compartir.
2. Cada jugador se une con ese código y elige un personaje (pregenerado o personalizado).
3. La partida arranca en cuanto se une el mínimo de jugadores configurado. A partir de ahí, el máster puede dejar que la historia avance sola (palabras clave, tiradas) o intervenir cuando haga falta.

## Puesta en marcha

### Requisitos

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Variables de entorno (o un .env en backend/) — estos son los valores por defecto de desarrollo:
export DATABASE_URL="postgresql+psycopg://rpg:rpg@localhost:5432/rpg"
export JWT_SECRET="cambia-esto-en-produccion"

# Crea la base de datos y aplica las migraciones
createdb rpg  # o: psql -c "CREATE DATABASE rpg;"
alembic upgrade head

# Carga las historias de ejemplo
python -m app.seeds.load_seed

# Arranca el servidor
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` (comprobable en `/salud`).

### Frontend

```bash
cd app
npm install
npx expo start --web   # o --android / --ios, o sin flag para elegir desde el menú de Expo
```

Por defecto el cliente apunta al backend de desarrollo en `localhost:8000` (`10.0.2.2` automáticamente en el emulador de Android). Para apuntar a otro backend, define `EXPO_PUBLIC_API_URL` y `EXPO_PUBLIC_API_WS_URL` antes de arrancar o compilar.

### Tests

```bash
# Backend (usa una base de datos separada, rpg_test, por defecto)
cd backend && python -m pytest

# Frontend (comprobación de tipos)
cd app && npx tsc --noEmit --noUnusedLocals --noUnusedParameters
```

## Desplegar el backend en un servidor externo

Para dejar de depender de tu propio ordenador, el backend ya trae un `Dockerfile` listo para desplegar en un PaaS como Railway. Guía paso a paso en [`DEPLOY.md`](./DEPLOY.md).

## Compilar un APK

El workflow `.github/workflows/build-apk.yml` compila un APK de depuración de Android bajo demanda (`Actions → Build Android APK → Run workflow`), apuntando al backend que se le indique, y lo publica como release de GitHub.

## Diseño de historias

Las historias viven como JSON en `backend/app/seeds/` y se validan contra el esquema del motor antes de poder usarse (`app/engine/validator.py`). Para diseñar una historia de forma visual existe un editor de mapas narrativos (nodos, palabras clave, catálogo de hechizos/armas/grimorios) que exporta directamente a este formato.
