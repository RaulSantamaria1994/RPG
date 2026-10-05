import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
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

export interface EpilogoPersonal {
  personaje_id: string;
  personaje_nombre: string;
  texto: string;
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
  votosGrupales: { votados: number; total: number } | null;
  propuestasIntercambio: PropuestaIntercambio[];
  conectado: boolean;
  cliente: ClienteSala | null;
  ultimaTirada: { dado?: number; total?: number; exito: boolean; quien: string } | null;
  mensajeSesion: string | null;
  epilogoPersonal: EpilogoPersonal | null;

  iniciarComoMaster: (sala: Sala, token: string) => void;
  iniciarComoJugador: (sala: Sala, token: string, personaje: Personaje) => void;
  conectar: () => void;
  desconectar: () => void;
  enviar: (tipo: string, datos?: Record<string, unknown>) => void;
  reiniciar: () => void;
  limpiarMensajeSesion: () => void;
}

function nuevoEvento(texto: string): EventoLog {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    hora: new Date().toLocaleTimeString(),
    texto,
  };
}

const ESTADO_INICIAL_TRANSITORIO = {
  estado: null,
  personajes: [] as Personaje[],
  log: [] as EventoLog[],
  palabrasBloqueadas: {} as Record<string, string>,
  confirmacionesGrupales: {} as Record<string, { confirmados: number; total: number }>,
  votosGrupales: null as { votados: number; total: number } | null,
  propuestasIntercambio: [] as PropuestaIntercambio[],
  conectado: false,
  cliente: null,
  ultimaTirada: null,
  epilogoPersonal: null as EpilogoPersonal | null,
};

export const useSalaStore = create<SalaState>()(
  persist(
    (set, get) => ({
      rol: null,
      sala: null,
      token: null,
      personaje: null,
      mensajeSesion: null,
      ...ESTADO_INICIAL_TRANSITORIO,

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
          mensajeSesion: null,
          ...ESTADO_INICIAL_TRANSITORIO,
        });
      },

      limpiarMensajeSesion: () => set({ mensajeSesion: null }),
    }),
    {
      name: 'rpg-sesion',
      storage: createJSONStorage(() => AsyncStorage),
      // Solo persistimos lo necesario para retomar la sesión al reabrir la
      // app; todo lo demás (log, estado de la partida, cliente WS...) se
      // vuelve a pedir al servidor al reconectar.
      partialize: (state) => ({
        rol: state.rol,
        sala: state.sala,
        token: state.token,
        personaje: state.personaje,
      }),
    }
  )
);

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
    case '_sesion_invalida': {
      get().cliente?.desconectar();
      set({
        rol: null,
        sala: null,
        token: null,
        personaje: null,
        mensajeSesion: 'Tu sesión anterior ya no es válida (la sala pudo cerrarse o expirar).',
        ...ESTADO_INICIAL_TRANSITORIO,
      });
      break;
    }
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
      set({ estado: datos as unknown as EstadoPublico, confirmacionesGrupales: {}, votosGrupales: null });
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
        cambios?: {
          dano_aplicado?: number;
          objeto_otorgado?: { nombre: string; categoria?: string } | null;
        };
      };
      const quien = d.personaje_nombre ?? 'El grupo';
      const resultado = d.exito ? 'ÉXITO' : 'FALLO';
      const dano = d.cambios?.dano_aplicado ? ` (-${d.cambios.dano_aplicado} PV)` : '';
      const objeto = d.cambios?.objeto_otorgado
        ? d.cambios.objeto_otorgado.categoria === 'hechizo'
          ? ` — el grupo aprende el hechizo "${d.cambios.objeto_otorgado.nombre}"`
          : ` — obtenéis "${d.cambios.objeto_otorgado.nombre}"`
        : '';
      set((s) => ({
        log: [nuevoEvento(`${quien} intenta "${d.palabra_clave}" → ${resultado}${dano}${objeto}`), ...s.log],
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
      const d = datos as {
        origen: string;
        dano_aplicado?: number;
        accion?: string;
        enemigo_id?: string;
        objeto?: { nombre: string };
        hechizo?: string;
        efecto?: { tipo: string; dano?: number; cantidad?: number; enemigo_id?: string } | null;
        tirada?: { exito?: boolean; dado?: number; total?: number };
      };
      let texto: string;
      if (d.origen === 'enemigo' && d.accion === 'aturdido') {
        texto = 'Un enemigo aturdido pierde su turno';
      } else if (d.accion === 'objeto') {
        const nombreObjeto = d.objeto?.nombre ?? 'un objeto';
        texto =
          d.efecto?.tipo === 'dano'
            ? `Usa "${nombreObjeto}": ${d.efecto.cantidad ?? 0} de daño`
            : `Usa "${nombreObjeto}"`;
      } else if (d.accion === 'hechizo') {
        const exito = d.tirada?.exito;
        texto = exito
          ? `Lanza ${d.hechizo}: ${d.efecto?.tipo === 'dano' ? `${d.efecto.dano} de daño` : d.efecto?.tipo === 'aturdido' ? 'enemigo aturdido' : d.efecto?.tipo === 'curacion' ? `${d.efecto.cantidad} de curación` : 'efecto aplicado'}`
          : `Falla al lanzar ${d.hechizo}`;
      } else if (d.accion === 'huir') {
        texto = d.tirada?.exito ? 'Consigue huir' : 'No logra huir';
      } else if (d.accion === 'negociar') {
        texto = d.tirada?.exito ? 'Consigue negociar' : 'No logra negociar';
      } else if (d.origen === 'jugador') {
        texto = `Ataque de jugador: ${d.dano_aplicado ?? 0} de daño`;
      } else {
        texto = `Un enemigo ataca: ${d.dano_aplicado ?? 0} de daño`;
      }
      set((s) => ({
        log: [nuevoEvento(texto), ...s.log],
        ultimaTirada:
          d.origen === 'jugador' && d.tirada
            ? {
                dado: d.tirada.dado,
                total: d.tirada.total,
                exito: !!d.tirada.exito,
                quien: s.personaje?.nombre ?? 'Tú',
              }
            : s.ultimaTirada,
      }));
      break;
    }
    case 'personaje_actualizado': {
      const d = datos as unknown as Personaje;
      const textoEstado =
        d.estado === 'ausente'
          ? `${d.nombre} ha sido marcado ausente`
          : d.estado === 'muerto'
            ? null // el evento 'personaje_muerto' ya deja constancia en el log
            : `${d.nombre} vuelve a estar activo`;
      set((s) => ({
        personajes: s.personajes.some((p) => p.id === d.id)
          ? s.personajes.map((p) => (p.id === d.id ? { ...p, ...d } : p))
          : [...s.personajes, d],
        personaje: s.personaje?.id === d.id ? { ...s.personaje, ...d } : s.personaje,
        log: textoEstado ? [nuevoEvento(textoEstado), ...s.log] : s.log,
      }));
      break;
    }
    case 'personaje_muerto': {
      const d = datos as { personaje_id: string; personaje_nombre: string; epilogo: string };
      set((s) => ({
        log: [nuevoEvento(`💀 ${d.personaje_nombre} ha caído`), ...s.log],
        epilogoPersonal:
          s.personaje?.id === d.personaje_id
            ? { personaje_id: d.personaje_id, personaje_nombre: d.personaje_nombre, texto: d.epilogo }
            : s.epilogoPersonal,
      }));
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
    case 'objetos_otorgados': {
      const d = datos as {
        objetos: { objeto_id: string; nombre: string; categoria?: string }[];
        destino: string;
      };
      const hechizos = d.objetos.filter((o) => o.categoria === 'hechizo').map((o) => o.nombre);
      const objetos = d.objetos.filter((o) => o.categoria !== 'hechizo').map((o) => o.nombre);
      const partes = [
        objetos.length ? `El grupo encuentra: ${objetos.join(', ')}` : null,
        hechizos.length ? `El grupo aprende: ${hechizos.join(', ')}` : null,
      ].filter(Boolean) as string[];
      set((s) => ({
        log: [...partes.map(nuevoEvento), ...s.log],
      }));
      break;
    }
    case 'voto_registrado': {
      const d = datos as { personaje_nombre: string; opcion: string; votados: number; total: number };
      set((s) => ({
        votosGrupales: { votados: d.votados, total: d.total },
        log: [nuevoEvento(`${d.personaje_nombre} vota: "${d.opcion}" (${d.votados}/${d.total})`), ...s.log],
      }));
      break;
    }
    case 'votacion_resuelta': {
      const d = datos as { recuento: Record<string, number>; empate: boolean; opcion_ganadora: string };
      const sufijo = d.empate ? ' (empate resuelto al azar)' : '';
      set((s) => ({
        votosGrupales: null,
        log: [nuevoEvento(`El grupo decide: "${d.opcion_ganadora}"${sufijo}`), ...s.log],
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
