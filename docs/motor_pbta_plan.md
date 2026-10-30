# Reestructuración del motor: de d20+dificultad a PbtA

Este documento es el plan de reestructuración completo del motor del juego,
basado en *Powered by the Apocalypse* (PbtA), acordado con el usuario tras
investigación con fuentes reales (ver sección 11). Las historias actuales
(con el esquema viejo de `dificultad`/`atributo`/`modo_interaccion`) quedan
retiradas: no son compatibles con este motor nuevo.

## 0. Decisiones ya tomadas (no volver a discutir)

- Catálogo cerrado de 8 "movidas" con nombre, no un sistema libre de
  "elige atributo y tira".
- El combate se rediseña también en PbtA, no se queda como está.
- El resultado 7-9 reutiliza el mismo `nodo_exito` que el 10+, aplicando un
  coste automático (no un tercer nodo de destino).
- Se elimina la tirada grupal y la votación del sistema: toda movida la
  hace un personaje concreto. Las bifurcaciones narrativas sin tirada se
  deciden hablando (el máster o quien el grupo señale elige la opción); el
  motor no cuenta votos.
- Características: se mantienen **fuerza, astucia, voluntad, agilidad**
  (genéricas, válidas para cualquier ambientación).
- Barra de daño: **7 puntos**, estado "inestable" a partir de 4 de daño
  acumulado (cifra real de *Monster of the Week*).
- Puntos de Suerte: **7 al crear personaje**, mecánica nueva adoptada.
- Objetos: arma con bono de daño fijo (ya existe) + armadura nueva con
  reducción de daño fija, mismo patrón que *Monster of the Week*.

## 1. Núcleo de resolución (dados)

- Se sustituye `d20 + modificador vs dificultad` por **2d6 + modificador de
  característica**, leído en tres bandas fijas, iguales para toda tirada
  del juego:
  - **10+** → éxito limpio.
  - **7-9** → éxito con coste (ver más abajo).
  - **6-** → fallo; el máster complica la escena.
- Ya no existe un campo `dificultad` por palabra clave: los umbrales son
  siempre los mismos, así que el autor de una historia deja de tener que
  inventar un número cada vez.

### Conversión de característica a modificador (propuesta, no viene de ninguna fuente)

El punto de partida (reparto de 1 a 5 por característica, 12 puntos en
total entre las 4) se mantiene tal cual para no rehacer la creación de
personaje desde cero. Lo que cambia es que ese valor deja de sumarse
directo al d20 y pasa a convertirse en modificador de 2d6 con:

```
modificador = valor_caracteristica - 3
```

| Valor (1-5) | Modificador |
|---|---|
| 1 | -2 |
| 2 | -1 |
| 3 | 0 |
| 4 | +1 |
| 5 | +2 |

Esto da un rango de -2 a +2, cercano al -1/+3 habitual en PbtA, sin tocar
el sistema de reparto de puntos que ya existe. **Esta fórmula es una
propuesta de ingeniería mía, no un dato verificado de ningún manual — a
confirmar contigo** (pregunta en la sección 10).

## 2. Las 8 movidas básicas

| id | Nombre | Característica | Disparador |
|---|---|---|---|
| `actuar_bajo_presion` | Actuar bajo presión | Voluntad | Cajón de sastre: te arriesgas en algo que ninguna otra movida cubre |
| `convencer` | Convencer o manipular | Voluntad | Intentas que alguien haga lo que quieres con palabras |
| `investigar` | Investigar | Astucia | Examinas algo con atención para sacar información |
| `leer_el_peligro` | Leer el peligro | Astucia | Evalúas una situación peligrosa antes de actuar |
| `golpear` | Golpear | Fuerza | Combate cuerpo a cuerpo (ataque) |
| `proteger` | Proteger a alguien | Fuerza | Te interpones para evitar que un compañero sufra daño |
| `escabullirse` | Escabullirse | Agilidad | Huyes, te escondes o esquivas un peligro inmediato |
| `ayudar` | Ayudar a otro | — (tirada aparte, sin característica) | Asistes a un compañero; si aciertas, le das ventaja en su tirada |

Cada palabra clave de un nodo interactivo referencia el **id de una
movida**, no un atributo+dificultad sueltos. El campo `modo_interaccion`
desaparece del todo: ya no hace falta distinguir individual/apoyo/grupal,
porque "ayudar" es una movida más de la lista, no un modificador de otra.

### Coste automático del 7-9

Cada movida, al definirse en el catálogo del motor (no por historia), lleva
asociado qué tipo de coste aplica en 7-9. Por defecto:

- Movidas de riesgo físico (`golpear`, `escabullirse`, `actuar_bajo_presion`,
  `leer_el_peligro` en combate): 1 punto de daño.
- Movidas sociales (`convencer`): una `flag` que el máster puede usar más
  adelante (p. ej. "le debes algo", "ha quedado resentido"), sin daño.
- `investigar`: información incompleta o con un detalle falso, sin daño.
- `proteger`: el daño que ibas a evitarle a tu compañero recae parcialmente
  sobre ti.
- `ayudar`: no aplica coste propio (si fallas ayudando, simplemente no das
  ventaja).

Una historia puede sobreescribir este coste por defecto en una palabra
clave concreta si hace falta (campo opcional `coste_parcial`), pero no
hace falta especificarlo en el caso normal.

## 3. Barra de daño (sustituye a "vida")

- `vida_max` deja de variar por personaje: **fijo en 7 para todos**.
- Nuevo estado `inestable` cuando el daño acumulado llega a 4+: el
  personaje sigue jugando pero queda marcado (visible para el grupo), y es
  la señal narrativa de que un golpe más es grave.
- Heridas de 1-3 se curan con descanso o primeros auxilios (coherente con
  el botiquín que ya existe — `efecto: curar_vida`).
- Al llegar a 7/7 se dispara el mismo mecanismo que hoy a 0 de vida
  (inconsciente, o muerto si `muerte_permanente`).

## 4. Puntos de Suerte (mecánica nueva)

- 7 al crear el personaje (pregenerado o personalizado).
- Gastar 1 punto permite, en el momento de resolver una movida:
  - convertir un 6- en 10+ (éxito automático), o
  - anular por completo el daño de una única fuente (un golpe, una trampa).
- No se recuperan solos entre nodos ni entre sesiones.
- Cuando llegan a 0, es una señal narrativa para el máster (no hay un
  disparador automático de código para esto — no tiene un nodo claro al
  que saltar, así que queda como guía de juego, igual que hoy el máster ya
  tiene herramientas de moderación para "complicar" la partida a mano).

## 5. Objetos: armas y armadura

- **Arma**: igual que ahora (`arma_equipada`, campo `bono_dano`), sin
  cambios.
- **Armadura (nueva)**: mismo patrón — `armadura_equipada` en el personaje,
  categoría de objeto `armadura`, campo `reduccion_dano`. Se resta del daño
  recibido antes de descontar de la barra de 7. Reutiliza el mecanismo de
  equipar/desequipar que ya existe para armas, con una ranura nueva.

## 6. Combate rediseñado

Se sustituye el combate actual (ronda, turno_index, iniciativa, enemigo con
`atributos{fuerza,agilidad,defensa}` y `ataques[]` con su propio
modificador) por resolución vía movidas:

- **Golpear**: atacas a un enemigo concreto.
  - 10+: golpeas limpio, aplicas tu daño (bono de arma incluido) y el
    enemigo no responde.
  - 7-9: golpeas, pero el enemigo contraataca — coste automático: recibes
    el daño de ese enemigo (ver ficha de enemigo, abajo).
  - 6-: fallas, y el enemigo actúa contra ti con su daño completo.
- **Proteger a alguien**: te interpones en el golpe que iba a recibir un
  compañero.
- **Escabullirse**: para huir de un combate o evitar quedar expuesto.
- **Actuar bajo presión**: cualquier otra acción arriesgada en pleno
  combate que no sea atacar/proteger/huir.

Esto elimina la reacción automática del enemigo tras cada acción del
jugador (hoy `_reaccion_enemigo` contraataca siempre): el contraataque pasa
a estar **dentro** de la banda 7-9 de Golpear, que es más fiel a cómo
funciona una movida PbtA (la complicación es parte del mismo resultado, no
un paso aparte).

**Ficha de enemigo simplificada**: vida propia (un número, se acaba la
pelea cuando llega a 0) + un valor de daño fijo que inflige cuando
contraataca o actúa — ya no necesita `atributos{fuerza,agilidad,defensa}`
ni una lista de `ataques[]` con su propio modificador, porque el enemigo ya
no tira: reacciona de forma determinista a la banda del jugador.

## 7. Esquema JSON de historia v2

Cambios respecto al esquema actual:

- Nuevo campo de nivel superior `motor_version: "pbta-1"` — permite que el
  validador distinga sin ambigüedad una historia del esquema nuevo de una
  del viejo, y rechace esta última con un error claro en vez de un
  comportamiento indefinido.
- `palabras_clave`: se sustituyen `modo_interaccion` + `atributo` +
  `dificultad` por un único campo `movida` (uno de los 8 ids). Se
  mantienen `requiere_objeto`, `requiere_flag`, `flags_set_exito`,
  `objeto_otorga_exito`, `repetible`. Nuevo campo opcional
  `coste_parcial` (solo si se quiere un coste distinto al que trae la
  movida por defecto).
- Nodos de combate: `enemigos` pasa a `[{"enemigo_id", "nombre", "vida",
  "dano"}]` — sin `atributos` ni `ataques[]`.
- `personajes_pregenerados`: ya no llevan `vida_max` (fijo en 7, lo pone el
  motor) ni un `puntos_suerte` inicial (fijo en 7). Sus `atributos` se
  siguen repartiendo 1-5 como hasta ahora.
- `hechizos`: pendiente de decidir si se adaptan a movidas o se retiran —
  no hay ninguna historia actual que los use de forma central, así que lo
  dejo fuera de este plan salvo que me digas lo contrario.

## 8. Retirada de las historias actuales

Las 4 historias existentes (`cuervo_negro`, `ala_norte`, `frecuencia_negra`,
`lo_que_duerme_en_la_orilla`) usan el esquema viejo y no van a pasar el
validador nuevo (que exigirá `movida` en vez de `dificultad`/`atributo`).

Acción por defecto que propongo (reversible, de bajo riesgo): marcarlas
`publicada=false` las 4 en cuanto el motor nuevo esté desplegado, para que
dejen de verse en el selector del máster, sin borrar ni los archivos del
repo ni las filas de la base de datos — así queda la opción de revisarlas
o reescribirlas más adelante sin haber perdido nada. Borrarlas del todo es
irreversible, así que lo dejo como pregunta explícita abierta (sección 10),
no como algo que decida por mi cuenta.

## 9. Plan de ejecución por fases

1. **Motor base**: `dice.py` (2d6, bandas), `resolver.py` (movidas en vez
   de atributo+dificultad, coste del 7-9), modelo de daño/suerte/armadura,
   migraciones de `Personaje` (puntos_suerte, armadura_equipada, estado
   `inestable`) y de `EstadoSala` si hiciera falta. Tests.
2. **Combate rediseñado**: `combate.py`, `handlers/combate.py`, ficha de
   enemigo simplificada. Tests.
3. **Esquema y validador**: `validator.py` exige `motor_version: "pbta-1"`
   y rechaza el esquema viejo con un error claro; retirada de las 4
   historias actuales (según lo que respondas en la sección 10).
4. **Frontend**: tirada de 2d6 en vez de d20, ficha de personaje con barra
   de 7 + Puntos de Suerte + ranura de armadura, paneles de
   interacción/combate mostrando el catálogo de 8 movidas en vez de
   "tirar dado" genérico.
5. **(Aparte, después de este plan)**: rediseñar el artefacto/proceso de
   creación de historias basándome en estas reglas — es el siguiente
   encargo, pendiente de que cerremos este plan primero.

## 10. Decisiones finales (confirmadas por el usuario)

1. Las 4 historias actuales se **despublican** (`publicada=false`), no se
   borran — archivos y filas de base de datos se quedan donde están.
2. La fórmula de conversión `modificador = valor - 3` queda confirmada.
3. Ficha de enemigo **simplificada**: vida + un daño fijo, sin atributos
   propios ni lista de ataques.
4. Implementación **fase por fase**: cada fase se revisa y prueba antes de
   pasar a la siguiente.

## 11. Fuentes usadas en el diseño

- [Using Apocalypse World to Outline and Draft Your Own RPG](https://lumpley.games/2024/04/29/powered-by-the-apocalypse-part-11-dice/)
- [Powered by the Apocalypse (2d6 + stat) — tutorial](https://dice-playground.stevecooperorg.workers.dev/tutorial/13-pbta-2d6-move.html)
- [What is Powered by the Apocalypse](https://startplaying.games/blog/posts/what-is-powered-by-the-apocalypse)
- [Lasers and Feelings (wiki)](https://2d4chan.org/wiki/Lasers_and_feelings)
- [Lasers and Feelings: Commentary](https://ttrpgfactory.com/2021/11/01/lasers-and-feelings-commentary)
- Apocalypse World 3rd Ed Preview — Moves Ref (lumpley.games, PDF)
- Apocalypse World Moves Index (apocalypse-world.com, PDF)
- Monster of the Week — listados de movidas básicas, barra de daño (7
  puntos / inestable a 4+) y Puntos de Suerte (7, no se recuperan solos),
  recogidos de varias fichas de referencia y reseñas (Evil Hat / fan
  reference sheets) vía búsqueda web — no se pudo acceder al manual
  oficial completo (WebFetch bloqueado en este entorno de red), así que
  los números de armas/armadura concretos no están verificados letra por
  letra, solo el patrón (arma = bono fijo, armadura = reducción fija).
