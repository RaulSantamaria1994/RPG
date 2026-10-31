/** Mensajes sobre el estado de un personaje: ajuste manual del máster,
 * cambio de equipo, sincronización general (vida, maná, estado...) y
 * muerte permanente.
 */
import type { Personaje } from '../../types';
import type { FijarEstado } from './comun';
import { nuevoEvento } from './comun';

export function personaje_ajustado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as { personaje_id: string; nombre: string; delta_vida: number; delta_mana: number };
  const partes: string[] = [];
  if (d.delta_vida) {
    const signo = d.delta_vida > 0 ? '+' : '';
    partes.push(`${signo}${d.delta_vida} PV`);
  }
  if (d.delta_mana) {
    const signo = d.delta_mana > 0 ? '+' : '';
    partes.push(`${signo}${d.delta_mana} maná`);
  }
  if (partes.length) {
    set((s) => ({
      log: [nuevoEvento(`El máster ajusta a ${d.nombre}: ${partes.join(', ')}`), ...s.log],
    }));
  }
}

export function equipo_cambiado(datos: Record<string, unknown>, set: FijarEstado): void {
  // El cambio de estado en sí (arma_equipada/hechizo_equipado,
  // inventario_grupo) ya llega por personaje_actualizado/nodo_actualizado;
  // esto es solo para que quede constancia en el registro de la partida.
  const d = datos as {
    personaje_nombre: string;
    objeto_nombre: string;
    ranura: 'arma' | 'armadura' | 'hechizo';
    accion: 'equipar' | 'desequipar';
  };
  const texto =
    d.accion === 'equipar'
      ? `${d.personaje_nombre} equipa "${d.objeto_nombre}" como ${d.ranura}`
      : `${d.personaje_nombre} desequipa "${d.objeto_nombre}"`;
  set((s) => ({ log: [nuevoEvento(texto), ...s.log] }));
}

export function personaje_actualizado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as unknown as Personaje;
  set((s) => {
    // Este mensaje llega por cualquier cambio del personaje (vida,
    // maná, estado…), no solo por pasar a ausente/activo — así que el
    // texto de "ha cambiado de estado" solo se añade al log si el
    // estado es justo lo que cambió, comparando con lo que ya sabíamos.
    let anterior: Personaje | undefined;
    for (const p of s.personajes) {
      if (p.id === d.id) {
        anterior = p;
      }
    }
    if (!anterior) {
      anterior = s.personaje ?? undefined;
    }
    const estadoCambio = anterior ? anterior.estado !== d.estado : false;

    let textoEstado: string | null = null;
    if (estadoCambio) {
      if (d.estado === 'ausente') {
        textoEstado = `${d.nombre} ha sido marcado ausente`;
      } else if (d.estado === 'muerto') {
        textoEstado = null; // el evento 'personaje_muerto' ya deja constancia en el log
      } else if (d.estado === 'inconsciente') {
        textoEstado = `${d.nombre} ha quedado inconsciente`;
      } else if (d.estado === 'activo') {
        textoEstado = `${d.nombre} vuelve a estar activo`;
      }
    }

    let yaExisteEnLaLista = false;
    for (const p of s.personajes) {
      if (p.id === d.id) {
        yaExisteEnLaLista = true;
      }
    }
    let personajesActualizados: Personaje[];
    if (yaExisteEnLaLista) {
      personajesActualizados = [];
      for (const p of s.personajes) {
        if (p.id === d.id) {
          personajesActualizados.push({ ...p, ...d });
        } else {
          personajesActualizados.push(p);
        }
      }
    } else {
      personajesActualizados = [...s.personajes, d];
    }

    return {
      personajes: personajesActualizados,
      personaje: s.personaje?.id === d.id ? { ...s.personaje, ...d } : s.personaje,
      log: textoEstado ? [nuevoEvento(textoEstado), ...s.log] : s.log,
    };
  });
}

export function personaje_muerto(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as { personaje_id: string; personaje_nombre: string; epilogo: string };
  set((s) => ({
    log: [nuevoEvento(`${d.personaje_nombre} ha caído`, 'muerte'), ...s.log],
    epilogoPersonal:
      s.personaje?.id === d.personaje_id
        ? { personaje_id: d.personaje_id, personaje_nombre: d.personaje_nombre, texto: d.epilogo }
        : s.epilogoPersonal,
  }));
}
