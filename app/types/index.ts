export type Atributo = 'fuerza' | 'astucia' | 'voluntad' | 'agilidad';

export interface Sala {
  id: string;
  codigo: string;
  nombre: string | null;
  historia_id: string;
  historia_version: number;
  min_jugadores: number;
  max_jugadores: number;
  estado: string;
  muerte_permanente: boolean;
}

export interface HistoriaResumen {
  id: string;
  historia_id: string;
  titulo: string;
  version: number;
  validada: boolean;
  publicada: boolean;
}

export interface PersonajePregenerado {
  id: string;
  nombre: string;
  trasfondo: string;
  atributos: Record<Atributo, number>;
  habilidad_pasiva: string;
  mana_max?: number;
  hechizos_conocidos?: string[];
}

export interface HabilidadPasiva {
  id: string;
  nombre: string;
  descripcion: string;
}

export interface Personaje {
  id: string;
  sala_id: string;
  jugador_nombre: string;
  nombre: string;
  origen: 'pregenerado' | 'personalizado';
  trasfondo: string | null;
  fuerza: number;
  astucia: number;
  voluntad: number;
  agilidad: number;
  habilidad_pasiva: string;
  vida_max: number;
  vida_actual: number;
  /** Puntos de Suerte: 7 al crear el personaje, no se recuperan solos
   * (ver docs/motor_pbta_plan.md, sección 4). */
  puntos_suerte_max: number;
  puntos_suerte_actual: number;
  mana_max: number;
  mana_actual: number;
  inventario: ObjetoInventario[];
  hechizos_conocidos: string[];
  rasgos: string[];
  arma_equipada?: ObjetoInventario | null;
  armadura_equipada?: ObjetoInventario | null;
  hechizo_equipado?: ObjetoInventario | null;
  estado: string;
  es_master?: boolean;
}

/** A partir de 4 de daño acumulado (barra de 7 con 3 o menos de vida
 * restante) el personaje queda "inestable": sigue jugando, pero es la
 * señal narrativa de que un golpe más es grave. */
export function esInestable(personaje: { vida_max: number; vida_actual: number }): boolean {
  return personaje.vida_max - personaje.vida_actual >= 4;
}

export interface ObjetoInventario {
  objeto_id: string;
  nombre: string;
  efecto?: { tipo: string; cantidad?: number } | null;
  consumible?: boolean;
  /** 'arma', 'armadura' y 'grimorio' son equipables desde la pestaña de
   * Equipo. El valor 'hechizo' es otra cosa, histórica: un objeto
   * otorgado con esa categoría nunca llega a ser un objeto físico —
   * enseña el hechizo a todo el grupo en el momento en que se otorga
   * (ver `otorgar_objeto` en el backend), así que jamás aparece en un
   * inventario. */
  categoria?: 'arma' | 'armadura' | 'grimorio' | 'hechizo';
  /** Solo en categoria 'arma': bono de daño que suma al atacar con ella equipada. */
  bono_dano?: number;
  /** Solo en categoria 'armadura': reducción de daño fija que resta a
   * cualquier golpe recibido antes de descontar de la barra de 7. */
  reduccion_dano?: number;
  /** Solo en categoria 'grimorio': qué hechizo del catálogo deja lanzar. */
  hechizo_id?: string;
}

export interface Hechizo {
  hechizo_id: string;
  nombre: string;
  categoria: string;
  coste_mana: number;
  descripcion: string;
  efecto?: string | null;
}

/** Id de una de las 8 movidas básicas del motor (ver
 * docs/motor_pbta_plan.md, sección 2) — vive en el motor, no en la
 * historia: una palabra clave solo referencia el id. */
export type MovidaId =
  | 'actuar_bajo_presion'
  | 'convencer'
  | 'investigar'
  | 'leer_el_peligro'
  | 'golpear'
  | 'proteger'
  | 'escabullirse'
  | 'ayudar';

export interface PalabraClave {
  texto: string;
  /** Ausente = decisión narrativa sin tirada (el grupo lo habla y
   * cualquiera confirma la opción acordada); el motor ya no cuenta votos. */
  movida?: MovidaId;
  repetible?: boolean;
  requiere_flag?: string | null;
  requiere_objeto?: string | null;
  categoria_hechizo_alternativa?: string;
  hechizo_id_alternativo?: string;
  coste_parcial?: { tipo: string; cantidad?: number } | null;
  dano_fallo?: { cantidad: number };
}

export interface Nodo {
  tipo: 'interactivo' | 'narrativo' | 'combate';
  texto: string;
  palabras_clave?: PalabraClave[];
  nodo_siguiente?: string;
  es_final?: boolean;
  tipo_final?: string | null;
  enemigos?: EnemigoCombate[];
}

/** Ficha de enemigo simplificada: solo vida y un daño fijo que inflige al
 * contraatacar — el enemigo no tira, reacciona de forma determinista a la
 * banda de la movida del jugador (ver docs/motor_pbta_plan.md, sección 6). */
export interface EnemigoCombate {
  enemigo_id: string;
  nombre: string;
  vida: number;
  vida_max: number;
  dano: number;
  derrotado: boolean;
}

export interface EstadoCombate {
  enemigos: EnemigoCombate[];
  orden_iniciativa: string[];
  turno_index: number;
  ronda: number;
  terminado: boolean;
  resultado: string | null;
}

export interface EntradaDiario {
  flag: string;
  texto: string;
}

export interface EstadoPublico {
  nodo_actual_id: string;
  nodo: Nodo;
  flags: Record<string, unknown>;
  /** Lo que el grupo ha descubierto hasta ahora, traducido a texto legible
   * — las flags narrativas en sí son opacas, esto es lo que de verdad se le
   * muestra al jugador. En el orden en que se fue descubriendo. */
  diario: EntradaDiario[];
  palabras_clave_usadas: string[];
  inventario_grupo: ObjetoInventario[];
  fase: 'exploracion' | 'combate';
  combate: EstadoCombate | null;
  finalizada: boolean;
  tipo_final: string | null;
}

/** Qué movida de combate acaba de resolverse — así la interfaz puede
 * mostrar un icono y una animación propios de cada una, en vez de un
 * aviso genérico igual para todo. El enemigo ya no tiene turno ni
 * reacción aparte: su contraataque, si lo hay, va dentro de la propia
 * resolución de la movida del jugador. */
export type AccionCombateTipo = 'golpear' | 'proteger' | 'escabullirse' | 'actuar_bajo_presion' | 'objeto';

/** Las tres bandas fijas de 2d6 + modificador (ver docs/motor_pbta_plan.md,
 * sección 1): 10+ éxito limpio, 7-9 éxito con coste, 6- fallo. */
export type Banda = 'exito' | 'exito_con_coste' | 'fallo';

export interface TiradaResultado {
  dados?: [number, number];
  modificador?: number;
  total?: number;
  banda?: Banda;
  exito: boolean;
  hechizo?: string;
}

export interface NodoResumen {
  id: string;
  tipo: 'interactivo' | 'narrativo' | 'combate';
  texto: string;
  es_final: boolean;
  tipo_final: string | null;
}

export interface EventoLog {
  id: string;
  hora: string;
  texto: string;
  /** Qué icono mostrar junto al texto, si procede — nunca un emoji
   * incrustado en el texto. Las pantallas deciden qué icono de librería
   * corresponde a cada valor. */
  icono?: 'muerte' | 'aviso' | 'pista';
}
