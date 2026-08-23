import { create } from 'zustand';
import { ClienteSala, type MensajeWs } from '../services/websocket';
import type { EstadoPublico, EventoLog, Personaje, Sala } from '../types';

export interface PropuestaIntercambio {
  clave: string;
  origen_personaje_id: string;
  origen_personaje_nombre: string;
  objeto_id: string;
  objeto_nombre: string;
  destino_personaje_id: string;
}

interface SalaState {
  rol: 'master' | 'jugador' | null;
  sala: Sala | null;
  token: string | null;
  personaje: Personaje | null;
  estado: EstadoPublico | null;
  personajes: Personaje[];
  log: EventoLog[];
  palabrasBloqueadas: Record<string, string>;
  confirmacionesGrupales: Record<string, { confirmados: number; total: number }>;
  propuestasIntercambio: PropuestaIntercambio[];
  conectado: boolean;
  cliente: ClienteSala | null;
  ultimaTirada: { dado?: number; total?: number; exito: boolean; quien: string } | null;

  iniciarComoMaster: (sala: Sala, token: string) => void;
  iniciarComoJugador: (sala: Sala, token: string, personaje: Personaje) => void;
  conectar: () => void;
  desconectar: () => void;
  enviar: (tipo: string, datos?: Record<string, unknown>) => void;
  reiniciar: () => void;
}

function nuevoEvento(texto: string): EventoLog {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    hora: new Date().toLocaleTimeString(),
    texto,
  };
}

export const useSalaStore = create<SalaState>((set, get) => ({
  rol: null,
  sala: null,
  token: null,
  personaje: null,
  estado: null,
  personajes: [],
  log: [],
  palabrasBloqueadas: {},
  confirmacionesGrupales: {},
  propuestasIntercambio: [],
  conectado: false,
  cliente: null,
  ultimaTirada: null,

  iniciarComoMaster: (sala, token) => set({ rol: 'master', sala, token }),
  iniciarComoJugador: (sala, token, personaje) =>
    set({ rol: 'jugador', sala, token, personaje }),

  conectar: () => {
    const { sala, token, cliente } = get();
    if (!sala || !token || cliente) return;

    const nuevoCliente = new ClienteSala(sala.codigo, token);
    nuevoCliente.suscribir((mensaje) => procesarMensaje(mensaje, set, get));
    nuevoCliente.conectar();
    set({ cliente: nuevoCliente, conectado: true });
  },

  desconectar: () => {
    get().cliente?.desconectar();
    set({ cliente: null, conectado: false });
  },

  enviar: (tipo, datos = {}) => get().cliente?.enviar(tipo, datos),

  reiniciar: () => {
    get().cliente?.desconectar();
    set({
      rol: null,
      sala: null,
      token: null,
      personaje: null,
      estado: null,
      personajes: [],
      log: [],
      palabrasBloqueadas: {},
      confirmacionesGrupales: {},
      propuestasIntercambio: [],
      conectado: false,
      cliente: null,
      ultimaTirada: null,
    });
  },
}));

function actualizarInventario(
  personajes: Personaje[],
  personajeId: string,
  actualizar: (inventario: Personaje['inventario']) => Personaje['inventario']
): Personaje[] {
  return personajes.map((p) =>
    p.id === personajeId ? { ...p, inventario: actualizar(p.inventario) } : p
  );
}

function procesarMensaje(
  mensaje: MensajeWs,
  set: (parcial: Partial<SalaState> | ((s: SalaState) => Partial<SalaState>)) => void,
  get: () => SalaState
): void {
  const { tipo, datos } = mensaje;

  switch (tipo) {
    case 'estado_inicial': {
      const { personajes, sala: _s, ...estado } = datos as any;
      const listaPersonajes: Personaje[] = personajes ?? [];
      set((s) => {
        const propio = listaPersonajes.find((p) => p.id === s.personaje?.id);
        return {
          estado: estado as EstadoPublico,
          personajes: listaPersonajes,
          personaje: propio ? { ...s.personaje, ...propio } : s.personaje,
        };
      });
      break;
    }
    case 'nodo_actualizado': {
      set({ estado: datos as unknown as EstadoPublico, confirmacionesGrupales: {} });
      break;
    }
    case 'palabra_clave_bloqueada': {
      const { clave, jugador } = datos as { clave: string; jugador: string };
      set((s) => ({ palabrasBloqueadas: { ...s.palabrasBloqueadas, [clave]: jugador } }));
      break;
    }
    case 'palabra_clave_liberada': {
      const { clave } = datos as { clave: string };
      set((s) => {
        const copia = { ...s.palabrasBloqueadas };
        delete copia[clave];
        return { palabrasBloqueadas: copia };
      });
      break;
    }
    case 'tirada_resultado': {
      const d = datos as {
        personaje_nombre?: string;
        palabra_clave?: string;
        exito: boolean;
        tirada?: { dado?: number; total?: number };
      };
      const quien = d.personaje_nombre ?? 'El grupo';
      const resultado = d.exito ? 'ÉXITO' : 'FALLO';
      set((s) => ({
        log: [nuevoEvento(`${quien} intenta "${d.palabra_clave}" → ${resultado}`), ...s.log],
        ultimaTirada: {
          dado: d.tirada?.dado,
          total: d.tirada?.total,
          exito: d.exito,
          quien,
        },
      }));
      break;
    }
    case 'combate_resultado': {
      const d = datos as { origen: string; dano_aplicado?: number; accion?: string };
      const texto =
        d.origen === 'jugador'
          ? `Ataque de jugador: ${d.dano_aplicado ?? 0} de daño`
          : `Un enemigo ataca: ${d.dano_aplicado ?? 0} de daño`;
      set((s) => ({ log: [nuevoEvento(texto), ...s.log] }));
      break;
    }
    case 'jugador_conectado': {
      const d = datos as { nombre: string; personaje?: Personaje | null };
      set((s) => {
        let personajes = s.personajes;
        if (d.personaje) {
          const yaExiste = personajes.some((p) => p.id === d.personaje!.id);
          personajes = yaExiste
            ? personajes.map((p) => (p.id === d.personaje!.id ? d.personaje! : p))
            : [...personajes, d.personaje];
        }
        return { log: [nuevoEvento(`${d.nombre} se ha conectado`), ...s.log], personajes };
      });
      break;
    }
    case 'jugador_desconectado': {
      const d = datos as { nombre: string };
      set((s) => ({ log: [nuevoEvento(`${d.nombre} se ha desconectado`), ...s.log] }));
      break;
    }
    case 'confirmacion_registrada': {
      const d = datos as { clave: string; confirmados: number; total: number };
      set((s) => ({
        confirmacionesGrupales: {
          ...s.confirmacionesGrupales,
          [d.clave]: { confirmados: d.confirmados, total: d.total },
        },
        log: [nuevoEvento(`Confirmaciones: ${d.confirmados}/${d.total}`), ...s.log],
      }));
      break;
    }
    case 'apoyo_resuelto': {
      const d = datos as { personaje_nombre: string; tirada: { exito: boolean } };
      const resultado = d.tirada.exito ? 'consigue ayudar' : 'no logra ayudar';
      set((s) => ({ log: [nuevoEvento(`${d.personaje_nombre} ${resultado}`), ...s.log] }));
      break;
    }
    case 'intercambio_propuesto': {
      const d = datos as {
        origen_personaje_id: string;
        origen_personaje_nombre: string;
        objeto_id: string;
        objeto_nombre: string;
        destino_personaje_id: string;
      };
      const clave = `${d.origen_personaje_id}:${d.objeto_id}:${d.destino_personaje_id}`;
      set((s) => ({
        propuestasIntercambio: [
          ...s.propuestasIntercambio.filter((p) => p.clave !== clave),
          { clave, ...d },
        ],
        log: [
          nuevoEvento(`${d.origen_personaje_nombre} ofrece "${d.objeto_nombre}"`),
          ...s.log,
        ],
      }));
      break;
    }
    case 'intercambio_completado': {
      const d = datos as {
        origen_personaje_id: string;
        destino_personaje_id: string;
        objeto: { objeto_id: string; nombre: string };
      };
      set((s) => {
        let personajes = actualizarInventario(s.personajes, d.origen_personaje_id, (inv) =>
          inv.filter((o) => o.objeto_id !== d.objeto.objeto_id)
        );
        personajes = actualizarInventario(personajes, d.destino_personaje_id, (inv) => [
          ...inv,
          d.objeto,
        ]);

        let personaje = s.personaje;
        if (personaje?.id === d.origen_personaje_id) {
          personaje = { ...personaje, inventario: personaje.inventario.filter((o) => o.objeto_id !== d.objeto.objeto_id) };
        } else if (personaje?.id === d.destino_personaje_id) {
          personaje = { ...personaje, inventario: [...personaje.inventario, d.objeto] };
        }

        return {
          personajes,
          personaje,
          propuestasIntercambio: s.propuestasIntercambio.filter(
            (p) => !(p.origen_personaje_id === d.origen_personaje_id && p.objeto_id === d.objeto.objeto_id)
          ),
          log: [nuevoEvento(`Intercambio completado: "${d.objeto.nombre}"`), ...s.log],
        };
      });
      break;
    }
    case 'error': {
      const d = datos as { mensaje: string };
      set((s) => ({ log: [nuevoEvento(`⚠ ${d.mensaje}`), ...s.log] }));
      break;
    }
    default:
      break;
  }
}
