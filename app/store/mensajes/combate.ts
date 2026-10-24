/** Mensaje `combate_resultado`: el texto de log y la animación a disparar
 * para cada acción de combate (atacar, huir, negociar, objeto, hechizo),
 * venga del jugador o de la reacción inmediata del enemigo.
 */
import type { AccionCombateTipo, Personaje } from '../../types';
import type { FijarEstado } from './comun';
import { nuevoEvento } from './comun';

export function combate_resultado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as {
    origen: string;
    dano_aplicado?: number;
    accion?: string;
    enemigo_id?: string;
    personaje_id?: string;
    personaje_nombre?: string;
    objeto?: { nombre: string };
    hechizo?: string;
    efecto?: { tipo: string; dano?: number; cantidad?: number; enemigo_id?: string } | null;
    tirada?: { exito?: boolean; dado?: number; total?: number };
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
    let texto: string;
    let tipoAnim: AccionCombateTipo;
    let exitoAnim: boolean | undefined;
    if (d.origen === 'enemigo' && d.accion === 'aturdido') {
      texto = 'Un enemigo aturdido pierde su turno';
      tipoAnim = 'enemigo_aturdido';
    } else if (d.accion === 'objeto') {
      const nombreObjeto = d.objeto?.nombre ?? 'un objeto';
      texto =
        d.efecto?.tipo === 'dano'
          ? `${quien} usa "${nombreObjeto}": ${d.efecto.cantidad ?? 0} de daño`
          : `${quien} usa "${nombreObjeto}"`;
      tipoAnim = 'objeto';
    } else if (d.accion === 'hechizo') {
      const exito = d.tirada?.exito;
      if (exito) {
        let descripcionEfecto: string;
        if (d.efecto?.tipo === 'dano') {
          descripcionEfecto = `${d.efecto.dano} de daño`;
        } else if (d.efecto?.tipo === 'aturdido') {
          descripcionEfecto = 'enemigo aturdido';
        } else if (d.efecto?.tipo === 'curacion') {
          descripcionEfecto = `${d.efecto.cantidad} de curación`;
        } else {
          descripcionEfecto = 'efecto aplicado';
        }
        texto = `${quien} lanza ${d.hechizo}: ${descripcionEfecto}`;
      } else {
        texto = `${quien} falla al lanzar ${d.hechizo}`;
      }
      tipoAnim = 'hechizo';
      exitoAnim = exito;
    } else if (d.accion === 'huir') {
      texto = d.tirada?.exito ? `${quien} consigue huir` : `${quien} no logra huir`;
      tipoAnim = 'huir';
      exitoAnim = d.tirada?.exito;
    } else if (d.accion === 'negociar') {
      texto = d.tirada?.exito ? `${quien} consigue negociar` : `${quien} no logra negociar`;
      tipoAnim = 'negociar';
      exitoAnim = d.tirada?.exito;
    } else if (d.origen === 'jugador') {
      texto = `${quien} ataca: ${d.dano_aplicado ?? 0} de daño`;
      tipoAnim = 'atacar';
      exitoAnim = d.tirada?.exito;
    } else {
      texto = `Un enemigo ataca: ${d.dano_aplicado ?? 0} de daño`;
      tipoAnim = 'enemigo_ataca';
    }
    return {
      log: [nuevoEvento(texto), ...s.log],
      ultimaTirada:
        d.origen === 'jugador' && d.tirada
          ? { dado: d.tirada.dado, total: d.tirada.total, exito: !!d.tirada.exito, quien }
          : s.ultimaTirada,
      ultimaAccionCombate: { tipo: tipoAnim, exito: exitoAnim, en: Date.now() },
    };
  });
}
