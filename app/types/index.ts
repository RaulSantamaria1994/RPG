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
}

export interface PersonajePregenerado {
  id: string;
  nombre: string;
  trasfondo: string;
  atributos: Record<Atributo, number>;
  habilidad_pasiva: string;
  vida_max?: number;
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
  mana_max: number;
  mana_actual: number;
  inventario: ObjetoInventario[];
  hechizos_conocidos: string[];
  rasgos: string[];
  estado: string;
  es_master?: boolean;
}

export interface ObjetoInventario {
  objeto_id: string;
  nombre: string;
  efecto?: { tipo: string; cantidad?: number } | null;
  consumible?: boolean;
}

export interface Hechizo {
  hechizo_id: string;
  nombre: string;
  categoria: string;
  coste_mana: number;
  dificultad: number;
  descripcion: string;
  efecto?: string | null;
}

export interface PalabraClave {
  texto: string;
  tipo_interaccion?: string;
  atributo?: Atributo;
  dificultad?: number;
  modo_interaccion?: 'individual' | 'grupal' | 'apoyo' | 'opuesta' | 'cadena';
  repetible?: boolean;
  requiere_flag?: string | null;
  requiere_objeto?: string | null;
  categoria_hechizo_alternativa?: string;
  hechizo_id_alternativo?: string;
  atributo_apoyo?: Atributo;
  dificultad_apoyo?: number;
  npc_modificador?: number;
  regla_grupal?: 'mejor_resultado' | 'todos_aciertan';
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

export interface EnemigoCombate {
  enemigo_id: string;
  nombre: string;
  vida: number;
  vida_max: number;
  derrotado: boolean;
  aturdido?: boolean;
}

export interface EstadoCombate {
  enemigos: EnemigoCombate[];
  orden_iniciativa: string[];
  turno_index: number;
  ronda: number;
  terminado: boolean;
  resultado: string | null;
  dificultad_huida?: number;
  dificultad_negociacion?: number;
}

export interface EstadoPublico {
  nodo_actual_id: string;
  nodo: Nodo;
  flags: Record<string, unknown>;
  palabras_clave_usadas: string[];
  inventario_grupo: ObjetoInventario[];
  fase: 'exploracion' | 'combate';
  combate: EstadoCombate | null;
  finalizada: boolean;
  tipo_final: string | null;
}

export interface TiradaResultado {
  dado?: number;
  modificador?: number;
  total?: number;
  dificultad?: number;
  exito: boolean;
  hechizo?: string;
  resultados?: { personaje: string; exito: boolean; total: number }[];
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
}
