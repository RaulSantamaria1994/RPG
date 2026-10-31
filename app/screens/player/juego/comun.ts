import type { Atributo, MovidaId } from '../../../types';

export const ETIQUETA_ATRIBUTO: Record<Atributo, string> = {
  fuerza: 'Fuerza',
  astucia: 'Astucia',
  voluntad: 'Voluntad',
  agilidad: 'Agilidad',
};

/** Catálogo cerrado de las 8 movidas básicas (ver docs/motor_pbta_plan.md,
 * sección 2) — vive en el motor, no en la historia, así que el nombre y la
 * característica de cada una se muestran a partir de este catálogo, igual
 * que en el backend (`app/engine/movidas.py`), nunca desde el JSON de la
 * historia. `caracteristica` es null para "ayudar": se resuelve con una
 * tirada aparte, sin característica propia (ver `PanelInteraccion`). */
export const MOVIDAS: Record<MovidaId, { nombre: string; caracteristica: Atributo | null }> = {
  actuar_bajo_presion: { nombre: 'Actuar bajo presión', caracteristica: 'voluntad' },
  convencer: { nombre: 'Convencer o manipular', caracteristica: 'voluntad' },
  investigar: { nombre: 'Investigar', caracteristica: 'astucia' },
  leer_el_peligro: { nombre: 'Leer el peligro', caracteristica: 'astucia' },
  golpear: { nombre: 'Golpear', caracteristica: 'fuerza' },
  proteger: { nombre: 'Proteger a alguien', caracteristica: 'fuerza' },
  escabullirse: { nombre: 'Escabullirse', caracteristica: 'agilidad' },
  ayudar: { nombre: 'Ayudar a otro', caracteristica: null },
};

export function formatearId(id: string): string {
  return id.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}
