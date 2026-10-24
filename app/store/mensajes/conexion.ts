/** Mensajes de ciclo de vida de la conexión y del plantel de jugadores:
 * estado de la conexión en sí, sesión invalidada por el servidor, el
 * paquete inicial al conectar, y quién entra/sale/es expulsado de la sala.
 */
import type { EstadoPublico, Personaje } from '../../types';
import { ESTADO_INICIAL_TRANSITORIO, type FijarEstado, type ObtenerEstado, nuevoEvento } from './comun';

export function _estado_conexion(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as { conectado: boolean; reintentando: boolean };
  set({ conectado: d.conectado, reintentandoConexion: d.reintentando });
}

export function _sesion_invalida(datos: Record<string, unknown>, set: FijarEstado, get: ObtenerEstado): void {
  const d = datos as { codigo?: number };
  get().cliente?.desconectar();
  set({
    rol: null,
    sala: null,
    token: null,
    personaje: null,
    mensajeSesion:
      d.codigo === 4403
        ? 'El máster te ha expulsado de la sala.'
        : 'Tu sesión anterior ya no es válida (la sala pudo cerrarse o expirar).',
    ...ESTADO_INICIAL_TRANSITORIO,
  });
}

export function estado_inicial(datos: Record<string, unknown>, set: FijarEstado): void {
  const { personajes, sala: _s, ...estado } = datos as any;
  const listaPersonajes: Personaje[] = personajes ?? [];
  set((s) => {
    let propio: Personaje | undefined;
    for (const p of listaPersonajes) {
      if (p.id === s.personaje?.id) {
        propio = p;
      }
    }
    // Si ya había registro de actividad (restaurado del dispositivo tras
    // recargar, o de antes de que la conexión se cayera y reintentara
    // sola) marcamos dónde retoma la sesión, para no confundir "lo que
    // pasó antes" con lo que llega a partir de ahora.
    const reconectando = s.log.length > 0;
    return {
      estado: estado as EstadoPublico,
      personajes: listaPersonajes,
      personaje: propio ? { ...s.personaje, ...propio } : s.personaje,
      log: reconectando ? [nuevoEvento('Te has reconectado a la sala'), ...s.log] : s.log,
    };
  });
}

export function jugador_conectado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as { nombre: string; personaje?: Personaje | null };
  set((s) => {
    let personajes = s.personajes;
    if (d.personaje) {
      let yaExiste = false;
      for (const p of personajes) {
        if (p.id === d.personaje!.id) {
          yaExiste = true;
        }
      }
      if (yaExiste) {
        const personajesActualizados: Personaje[] = [];
        for (const p of personajes) {
          if (p.id === d.personaje!.id) {
            personajesActualizados.push(d.personaje!);
          } else {
            personajesActualizados.push(p);
          }
        }
        personajes = personajesActualizados;
      } else {
        personajes = [...personajes, d.personaje];
      }
    }
    return { log: [nuevoEvento(`${d.nombre} se ha conectado`), ...s.log], personajes };
  });
}

export function jugador_desconectado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as { nombre: string };
  set((s) => ({ log: [nuevoEvento(`${d.nombre} se ha desconectado`), ...s.log] }));
}

export function jugador_expulsado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as { personaje_id: string; nombre: string; jugador_nombre: string };
  set((s) => {
    const personajesRestantes: Personaje[] = [];
    for (const p of s.personajes) {
      if (p.id !== d.personaje_id) {
        personajesRestantes.push(p);
      }
    }
    return {
      personajes: personajesRestantes,
      log: [nuevoEvento(`${d.nombre} (${d.jugador_nombre}) ha sido expulsado de la sala`), ...s.log],
    };
  });
}
