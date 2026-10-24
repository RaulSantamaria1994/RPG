import type { Atributo } from '../../../types';

export const ETIQUETA_ATRIBUTO: Record<Atributo, string> = {
  fuerza: 'Fuerza',
  astucia: 'Astucia',
  voluntad: 'Voluntad',
  agilidad: 'Agilidad',
};

export function formatearId(id: string): string {
  return id.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

/** Texto de resumen de la tirada que pide una palabra clave, según cómo esté
 * configurada (tirada enfrentada, con dificultad normal, votación sin tirada,
 * o decisión directa sin tirada). */
export function resumenDeLaTirada(
  p: { modo_interaccion?: string; atributo?: Atributo; dificultad?: number },
  esVotacion: boolean
): string {
  const nombreAtributo = p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?';
  if (p.modo_interaccion === 'opuesta') {
    return `${nombreAtributo} contra un rival`;
  }
  if (p.dificultad) {
    return `${nombreAtributo} · dificultad ${p.dificultad}`;
  }
  if (esVotacion) {
    return 'Sin tirada — gana la opción más votada por el grupo';
  }
  return 'Sin tirada — se resuelve al confirmar';
}

/** Texto que acompaña al enunciado de una palabra clave cuando se vota en
 * grupo, o cuando el grupo entero tiene que confirmarla para resolverse. */
export function sufijoModoGrupal(esVotacion: boolean, modoInteraccion?: string): string {
  if (esVotacion) return ' (vota el grupo)';
  if (modoInteraccion === 'grupal') return ' (confirma todo el grupo)';
  return '';
}
