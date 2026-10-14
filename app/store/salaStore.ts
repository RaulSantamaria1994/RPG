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
  actualizarCodigoSala: (nuevoCodigo: string) => void;
}

const MAX_LOG_PERSISTIDO = 200;

function nuevoEvento(texto: string, icono?: EventoLog['icono']): EventoLog {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    hora: new Date().toLocaleTimeString(),
    texto,
    icono,
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

      actualizarCodigoSala: (nuevoCodigo) => {
        const { sala, token, cliente } = get();
        if (!sala || !token) return;
        // El `ClienteSala` activo guarda el código con el que se construyó
        // y lo reutiliza si la conexión se cae y reintenta por su cuenta —
        // si no lo reconectamos ahora con el código nuevo, ese reintento
        // automático (o recargar la página, que relee esto del
        // almacenamiento persistido) fallaría con el código ya inválido.
        cliente?.desconectar();
        const nuevoCliente = new ClienteSala(nuevoCodigo, token);
        nuevoCliente.suscribir((mensaje) => procesarMensaje(mensaje, set, get));
        nuevoCliente.conectar();
        set({ sala: { ...sala, codigo: nuevoCodigo }, cliente: nuevoCliente, conectado: true });
      },
    }),
    {
      name: 'rpg-sesion',
      storage: createJSONStorage(() => AsyncStorage),
      // El estado de la partida (nodo, flags, personajes...) no hace falta
      // persistirlo: el servidor lo manda entero en `estado_inicial` en
      // cuanto reconecta. El registro de actividad es distinto — vive solo
      // en el cliente, el servidor no lo recuerda — así que sin esto,
      // recargar la página borraba de un plumazo todo lo que acababa de
      // pasar. Se recorta a las últimas entradas para no acumular un blob
      // cada vez más grande en el almacenamiento del dispositivo.
      partialize: (state) => ({
        rol: state.rol,
        sala: state.sala,
        token: state.token,
        personaje: state.personaje,
        log: state.log.slice(0, MAX_LOG_PERSISTIDO),
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
      break;
    }
    case 'estado_inicial': {
      const { personajes, sala: _s, ...estado } = datos as any;
      const listaPersonajes: Personaje[] = personajes ?? [];
      set((s) => {
        const propio = listaPersonajes.find((p) => p.id === s.personaje?.id);
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
      break;
    }
    case 'nodo_actualizado': {
      const nuevoEstado = datos as unknown as EstadoPublico;
      set((s) => {
        const flagsAnteriores = new Set((s.estado?.diario ?? []).map((e) => e.flag));
        const pistasNuevas = (nuevoEstado.diario ?? []).filter((e) => !flagsAnteriores.has(e.flag));
        const eventosPistas = pistasNuevas.map((p) => nuevoEvento(`Nueva pista: ${p.texto}`, 'pista')).reverse();
        return {
          estado: nuevoEstado,
          confirmacionesGrupales: {},
          votosGrupales: null,
          log: [...eventosPistas, ...s.log],
        };
      });
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
        const quien =
          d.personaje_nombre ?? s.personajes.find((p) => p.id === d.personaje_id)?.nombre ?? 'Un jugador';
        let texto: string;
        if (d.origen === 'enemigo' && d.accion === 'aturdido') {
          texto = 'Un enemigo aturdido pierde su turno';
        } else if (d.accion === 'objeto') {
          const nombreObjeto = d.objeto?.nombre ?? 'un objeto';
          texto =
            d.efecto?.tipo === 'dano'
              ? `${quien} usa "${nombreObjeto}": ${d.efecto.cantidad ?? 0} de daño`
              : `${quien} usa "${nombreObjeto}"`;
        } else if (d.accion === 'hechizo') {
          const exito = d.tirada?.exito;
          texto = exito
            ? `${quien} lanza ${d.hechizo}: ${d.efecto?.tipo === 'dano' ? `${d.efecto.dano} de daño` : d.efecto?.tipo === 'aturdido' ? 'enemigo aturdido' : d.efecto?.tipo === 'curacion' ? `${d.efecto.cantidad} de curación` : 'efecto aplicado'}`
            : `${quien} falla al lanzar ${d.hechizo}`;
        } else if (d.accion === 'huir') {
          texto = d.tirada?.exito ? `${quien} consigue huir` : `${quien} no logra huir`;
        } else if (d.accion === 'negociar') {
          texto = d.tirada?.exito ? `${quien} consigue negociar` : `${quien} no logra negociar`;
        } else if (d.origen === 'jugador') {
          texto = `${quien} ataca: ${d.dano_aplicado ?? 0} de daño`;
        } else {
          texto = `Un enemigo ataca: ${d.dano_aplicado ?? 0} de daño`;
        }
        return {
          log: [nuevoEvento(texto), ...s.log],
          ultimaTirada:
            d.origen === 'jugador' && d.tirada
              ? { dado: d.tirada.dado, total: d.tirada.total, exito: !!d.tirada.exito, quien }
              : s.ultimaTirada,
        };
      });
      break;
    }
    case 'personaje_ajustado': {
      const d = datos as { personaje_id: string; nombre: string; delta_vida: number; delta_mana: number };
      const partes = [
        d.delta_vida ? `${d.delta_vida > 0 ? '+' : ''}${d.delta_vida} PV` : null,
        d.delta_mana ? `${d.delta_mana > 0 ? '+' : ''}${d.delta_mana} maná` : null,
      ].filter(Boolean);
      if (partes.length) {
        set((s) => ({
          log: [nuevoEvento(`El máster ajusta a ${d.nombre}: ${partes.join(', ')}`), ...s.log],
        }));
      }
      break;
    }
    case 'personaje_actualizado': {
      const d = datos as unknown as Personaje;
      set((s) => {
        // Este mensaje llega por cualquier cambio del personaje (vida,
        // maná, estado…), no solo por pasar a ausente/activo — así que el
        // texto de "ha cambiado de estado" solo se añade al log si el
        // estado es justo lo que cambió, comparando con lo que ya sabíamos.
        const anterior = s.personajes.find((p) => p.id === d.id) ?? s.personaje ?? undefined;
        const estadoCambio = anterior ? anterior.estado !== d.estado : false;
        const textoEstado = !estadoCambio
          ? null
          : d.estado === 'ausente'
            ? `${d.nombre} ha sido marcado ausente`
            : d.estado === 'muerto'
              ? null // el evento 'personaje_muerto' ya deja constancia en el log
              : d.estado === 'inconsciente'
                ? `${d.nombre} ha quedado inconsciente`
                : d.estado === 'activo'
                  ? `${d.nombre} vuelve a estar activo`
                  : null;
        return {
          personajes: s.personajes.some((p) => p.id === d.id)
            ? s.personajes.map((p) => (p.id === d.id ? { ...p, ...d } : p))
            : [...s.personajes, d],
          personaje: s.personaje?.id === d.id ? { ...s.personaje, ...d } : s.personaje,
          log: textoEstado ? [nuevoEvento(textoEstado), ...s.log] : s.log,
        };
      });
      break;
    }
    case 'personaje_muerto': {
      const d = datos as { personaje_id: string; personaje_nombre: string; epilogo: string };
      set((s) => ({
        log: [nuevoEvento(`${d.personaje_nombre} ha caído`, 'muerte'), ...s.log],
        epilogoPersonal:
          s.personaje?.id === d.personaje_id
            ? { personaje_id: d.personaje_id, personaje_nombre: d.personaje_nombre, texto: d.epilogo }
            : s.epilogoPersonal,
      }));
      break;
    }
    case 'jugador_expulsado': {
      const d = datos as { personaje_id: string; nombre: string; jugador_nombre: string };
      set((s) => ({
        personajes: s.personajes.filter((p) => p.id !== d.personaje_id),
        log: [nuevoEvento(`${d.nombre} (${d.jugador_nombre}) ha sido expulsado de la sala`), ...s.log],
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
        log: [...partes.map((texto) => nuevoEvento(texto)), ...s.log],
      }));
      break;
    }
    case 'dano_al_llegar': {
      const d = datos as { cantidad: number; afectados: string[] };
      set((s) => ({
        log: [nuevoEvento(`El grupo sufre ${d.cantidad} de daño (-${d.cantidad} PV)`, 'aviso'), ...s.log],
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
      const d = datos as { mensaje: string; origen_personaje_id?: string; objeto_id?: string };
      set((s) => ({
        log: [nuevoEvento(d.mensaje, 'aviso'), ...s.log],
        // Un intercambio_confirmar fallido (el objeto ya no está, o el
        // personaje de origen no es válido) trae de vuelta qué propuesta
        // concreta ha quedado obsoleta — si no la quitáramos aquí, la
        // tarjeta de "te ofrece X" seguiría mostrándose como si todavía se
        // pudiera aceptar.
        propuestasIntercambio:
          d.origen_personaje_id && d.objeto_id
            ? s.propuestasIntercambio.filter(
                (p) => !(p.origen_personaje_id === d.origen_personaje_id && p.objeto_id === d.objeto_id)
              )
            : s.propuestasIntercambio,
      }));
      break;
    }
    default:
      break;
  }
}
