import type { AccionCombateTipo, EventoLog, Personaje } from '../../types';
import type { SalaState } from '../salaStore';

export interface PropuestaIntercambio {
  clave: string;
  origen_personaje_id: string;
  origen_personaje_nombre: string;
  objeto_id: string;
  objeto_nombre: string;
  destino_personaje_id: string;
}

export interface EpilogoPersonal {
  personaje_id: string;
  personaje_nombre: string;
  texto: string;
}

/** Los manejadores de cada tipo de mensaje reciben exactamente lo mismo que
 * recibía cada `case` del switch original: el `set`/`get` del store de
 * Zustand, sin envoltorios nuevos. */
export type FijarEstado = (parcial: Partial<SalaState> | ((s: SalaState) => Partial<SalaState>)) => void;
export type ObtenerEstado = () => SalaState;

// Estado de "lo que depende de estar conectado a una sala", al que vuelve
// la sesión al reiniciarse por completo o al quedar invalidada por el
// servidor (expulsión, sala borrada/expirada). Vive aquí, no en
// salaStore.ts, porque tanto el store como el manejador de `_sesion_invalida`
// (en conexion.ts) lo necesitan, y salaStore.ts importa a su vez los
// manejadores — ponerlo en el store crearía un ciclo de imports en tiempo
// de ejecución.
export const ESTADO_INICIAL_TRANSITORIO = {
  estado: null,
  personajes: [] as Personaje[],
  log: [] as EventoLog[],
  palabrasBloqueadas: {} as Record<string, string>,
  confirmacionesGrupales: {} as Record<string, { confirmados: number; total: number }>,
  votosGrupales: null as { votados: number; total: number; recuento: Record<string, number> } | null,
  propuestasIntercambio: [] as PropuestaIntercambio[],
  conectado: false,
  reintentandoConexion: false,
  cliente: null,
  ultimaTirada: null,
  ultimaAccionCombate: null as { tipo: AccionCombateTipo; exito?: boolean; en: number } | null,
  epilogoPersonal: null as EpilogoPersonal | null,
};

export function nuevoEvento(texto: string, icono?: EventoLog['icono']): EventoLog {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    hora: new Date().toLocaleTimeString(),
    texto,
    icono,
  };
}

export function actualizarInventario(
  personajes: Personaje[],
  personajeId: string,
  actualizar: (inventario: Personaje['inventario']) => Personaje['inventario']
): Personaje[] {
  const resultado: Personaje[] = [];
  for (const p of personajes) {
    if (p.id === personajeId) {
      resultado.push({ ...p, inventario: actualizar(p.inventario) });
    } else {
      resultado.push(p);
    }
  }
  return resultado;
}
