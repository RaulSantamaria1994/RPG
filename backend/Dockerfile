FROM python:3.11-slim

WORKDIR /app

# psycopg (binario) no necesita libpq-dev en runtime, pero sí build-essential
# para alguna dependencia transitiva en ciertas arquitecturas; se instala y
# se limpia en la misma capa para no dejar el paquete de apt en la imagen.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway (y la mayoría de PaaS) inyectan el puerto real en $PORT; 8000 es
# solo el valor de respaldo para correr el contenedor en local.
ENV PORT=8000
EXPOSE 8000

# Cada arranque aplica las migraciones pendientes y carga las historias de
# ejemplo que falten antes de levantar el servidor — ambos pasos son
# seguros de repetir (alembic no hace nada si ya está al día; el loader se
# salta las historias que ya existen), así que no hace falta un paso manual
# aparte la primera vez que se despliega.
CMD alembic upgrade head && python -m app.seeds.load_seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
