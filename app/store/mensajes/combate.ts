/** Mensaje `combate_resultado`: el texto de log y la animación a disparar
 * para cada movida de combate (golpear, proteger, escabullirse, actuar
 * bajo presión, objeto). El enemigo ya no tiene turno ni reacción
 * aparte: su contraataque, si lo hay, viene ya incluido en el mismo
 * mensaje de la movida del jugador (ver docs/motor_pbta_plan.md,
 * sección 6), así que aquí nunca hace falta distinguir "origen: enemigo".
 */
import type { AccionCombateTipo, Banda, Personaje } from '../../types';
import type { FijarEstado } from './comun';
import { nuevoEvento } from './comun';

export function combate_resultado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as {
    accion: AccionCombateTipo;
    personaje_id?: string;
    personaje_nombre?: string;
    tirada?: { dados?: [number, number]; total?: number; banda?: Banda; exito?: boolean };
    enemigo_id?: string;
    dano_a_enemigo?: number;
    dano_recibido?: number;
    enemigo_derrotado?: boolean;
    protegido_id?: string;
    dano_protector?: number;
    dano_protegido?: number;
    huido?: boolean;
    objeto?: { nombre: string };
    efecto?: { tipo: string; cantidad?: number; enemigo_id?: string } | null;
  };
  set((s) => {
    // El autor de la acción no tiene por qué ser quien ve la pantalla:
    // en una partida con varios jugadores, cada combate_resultado llega
    // a todo el mundo por igual, así que el nombre viene siempre del
    // propio mensaje (con el personaje local como respaldo si el
    // mensaje no lo trae), nunca de "mi" personaje.
    let personajeEmisor: Personaje | undefined;
    for (const p of s.personajes) {
      if (p.id === d.personaje_id) {
        personajeEmisor = p;
      }
    }
    const quien = d.personaje_nombre ?? personajeEmisor?.nombre ?? 'Un jugador';
    const exito = d.tirada?.exito;

    let texto: string;
    if (d.accion === 'golpear') {
      if (d.enemigo_derrotado) {
        texto = `${quien} golpea: ${d.dano_a_enemigo ?? 0} de daño — enemigo derrotado`;
      } else {
        texto = `${quien} golpea: ${d.dano_a_enemigo ?? 0} de daño`;
      }
      if (d.dano_recibido) {
        texto += ` (recibe ${d.dano_recibido} de daño)`;
      }
    } else if (d.accion === 'proteger') {
      if (d.dano_protector) {
        texto = `${quien} se interpone y recibe ${d.dano_protector} de daño`;
      } else if (d.dano_protegido) {
        texto = `${quien} no llega a tiempo: el golpe pasa igualmente`;
      } else {
        texto = `${quien} protege a su compañero sin que nadie sufra daño`;
      }
    } else if (d.accion === 'escabullirse') {
      texto = d.huido ? `${quien} consigue escabullirse` : `${quien} no logra escabullirse`;
      if (d.dano_recibido) {
        texto += ` (recibe ${d.dano_recibido} de daño)`;
      }
    } else if (d.accion === 'actuar_bajo_presion') {
      texto = exito ? `${quien} sale bien de la situación` : `${quien} sale mal de la situación`;
      if (d.dano_recibido) {
        texto += ` (recibe ${d.dano_recibido} de daño)`;
      }
    } else {
      const nombreObjeto = d.objeto?.nombre ?? 'un objeto';
      texto =
        d.efecto?.tipo === 'dano'
          ? `${quien} usa "${nombreObjeto}": ${d.efecto.cantidad ?? 0} de daño`
          : `${quien} usa "${nombreObjeto}"`;
    }

    return {
      log: [nuevoEvento(texto), ...s.log],
      ultimaTirada: d.tirada
        ? { dados: d.tirada.dados, total: d.tirada.total, banda: d.tirada.banda, exito: !!d.tirada.exito, quien }
        : s.ultimaTirada,
      ultimaAccionCombate: { tipo: d.accion, exito, en: Date.now() },
    };
  });
}
