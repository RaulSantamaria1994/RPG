import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { ClienteSala, type MensajeWs } from '../services/websocket';
import type { AccionCombateTipo, EstadoPublico, EventoLog, Personaje, Sala } from '../types';

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
  votosGrupales: { votados: number; total: number; recuento: Record<string, number> } | null;
  propuestasIntercambio: PropuestaIntercambio[];
  conectado: boolean;
  /** Solo tiene sentido cuando `conectado` es false: distingue "todavía no
   * se ha logrado la primera conexión" de "se tenía y se acaba de perder,
   * reintentando sola". Así la pantalla puede decir "Conectando…" o
   * "Reconectando…" según toque. */
  reintentandoConexion: boolean;
  cliente: ClienteSala | null;
  ultimaTirada: { dado?: number; total?: number; exito: boolean; quien: string } | null;
  /** La última acción de combate resuelta — solo para disparar el icono y
   * la animación específicos de atacar/huir/negociar/hechizo/etc. en la
   * pantalla; el texto legible de lo ocurrido va siempre al `log`. `en` es
   * una marca de tiempo que cambia en cada acción, incluso si se repite el
   * mismo tipo, para que la animación se reinicie cada vez. */
  ultimaAccionCombate: { tipo: AccionCombateTipo; exito?: boolean; en: number } | null;
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
  votosGrupales: null as { votados: number; total: number; recuento: Record<string, number> } | null,
  propuestasIntercambio: [] as PropuestaIntercambio[],
  conectado: false,
  reintentandoConexion: false,
  cliente: null,
  ultimaTirada: null,
  ultimaAccionCombate: null as { tipo: AccionCombateTipo; exito?: boolean; en: number } | null,
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
        set({ cliente: nuevoCliente });
      },

      desconectar: () => {
        get().cliente?.desconectar();
        set({ cliente: null, conectado: false, reintentandoConexion: false });
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
        set({ sala: { ...sala, codigo: nuevoCodigo }, cliente: nuevoCliente });
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

function procesarMensaje(
  mensaje: MensajeWs,
  set: (parcial: Partial<SalaState> | ((s: SalaState) => Partial<SalaState>)) => void,
  get: () => SalaState
): void {
  const { tipo, datos } = mensaje;

  switch (tipo) {
    case '_estado_conexion': {
      const d = datos as { conectado: boolean; reintentando: boolean };
      set({ conectado: d.conectado, reintentandoConexion: d.reintentando });
      break;
    }
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
      break;
    }
    case 'nodo_actualizado': {
      const nuevoEstado = datos as unknown as EstadoPublico;
      set((s) => {
        const flagsAnteriores = new Set<string>();
        for (const e of s.estado?.diario ?? []) {
          flagsAnteriores.add(e.flag);
        }
        const pistasNuevas = [];
        for (const e of nuevoEstado.diario ?? []) {
          if (!flagsAnteriores.has(e.flag)) {
            pistasNuevas.push(e);
          }
        }
        const eventosPistas = [];
        for (const p of pistasNuevas) {
          eventosPistas.push(nuevoEvento(`Nueva pista: ${p.texto}`, 'pista'));
        }
        eventosPistas.reverse();
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
      let objeto = '';
      if (d.cambios?.objeto_otorgado) {
        if (d.cambios.objeto_otorgado.categoria === 'hechizo') {
          objeto = ` — el grupo aprende el hechizo "${d.cambios.objeto_otorgado.nombre}"`;
        } else {
          objeto = ` — obtenéis "${d.cambios.objeto_otorgado.nombre}"`;
        }
      }
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
      break;
    }
    case 'personaje_ajustado': {
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
      break;
    }
    case 'equipo_cambiado': {
      // El cambio de estado en sí (arma_equipada/hechizo_equipado,
      // inventario_grupo) ya llega por personaje_actualizado/nodo_actualizado;
      // esto es solo para que quede constancia en el registro de la partida.
      const d = datos as {
        personaje_nombre: string;
        objeto_nombre: string;
        ranura: 'arma' | 'hechizo';
        accion: 'equipar' | 'desequipar';
      };
      const texto =
        d.accion === 'equipar'
          ? `${d.personaje_nombre} equipa "${d.objeto_nombre}" como ${d.ranura}`
          : `${d.personaje_nombre} desequipa "${d.objeto_nombre}"`;
      set((s) => ({ log: [nuevoEvento(texto), ...s.log] }));
      break;
    }
    case 'personaje_actualizado': {
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
      break;
    }
    case 'jugador_conectado': {
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
      const hechizos: string[] = [];
      const objetos: string[] = [];
      for (const o of d.objetos) {
        if (o.categoria === 'hechizo') {
          hechizos.push(o.nombre);
        } else {
          objetos.push(o.nombre);
        }
      }
      const partes: string[] = [];
      if (objetos.length) {
        partes.push(`El grupo encuentra: ${objetos.join(', ')}`);
      }
      if (hechizos.length) {
        partes.push(`El grupo aprende: ${hechizos.join(', ')}`);
      }
      const eventosNuevos: EventoLog[] = [];
      for (const texto of partes) {
        eventosNuevos.push(nuevoEvento(texto));
      }
      set((s) => ({
        log: [...eventosNuevos, ...s.log],
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
      set((s) => {
        const recuentoAnterior = s.votosGrupales?.recuento ?? {};
        const votosDeEstaOpcion = (recuentoAnterior[d.opcion] ?? 0) + 1;
        return {
          votosGrupales: {
            votados: d.votados,
            total: d.total,
            recuento: { ...recuentoAnterior, [d.opcion]: votosDeEstaOpcion },
          },
          log: [nuevoEvento(`${d.personaje_nombre} vota: "${d.opcion}" (${d.votados}/${d.total})`), ...s.log],
        };
      });
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
      set((s) => {
        const propuestasSinEstaClave: PropuestaIntercambio[] = [];
        for (const p of s.propuestasIntercambio) {
          if (p.clave !== clave) {
            propuestasSinEstaClave.push(p);
          }
        }
        return {
          propuestasIntercambio: [...propuestasSinEstaClave, { clave, ...d }],
          log: [
            nuevoEvento(`${d.origen_personaje_nombre} ofrece "${d.objeto_nombre}"`),
            ...s.log,
          ],
        };
      });
      break;
    }
    case 'intercambio_completado': {
      const d = datos as {
        origen_personaje_id: string;
        destino_personaje_id: string;
        objeto: { objeto_id: string; nombre: string };
      };
      set((s) => {
        let personajes = actualizarInventario(s.personajes, d.origen_personaje_id, (inv) => {
          const inventarioSinElObjeto = [];
          for (const o of inv) {
            if (o.objeto_id !== d.objeto.objeto_id) {
              inventarioSinElObjeto.push(o);
            }
          }
          return inventarioSinElObjeto;
        });
        personajes = actualizarInventario(personajes, d.destino_personaje_id, (inv) => [
          ...inv,
          d.objeto,
        ]);

        let personaje = s.personaje;
        if (personaje?.id === d.origen_personaje_id) {
          const inventarioSinElObjeto = [];
          for (const o of personaje.inventario) {
            if (o.objeto_id !== d.objeto.objeto_id) {
              inventarioSinElObjeto.push(o);
            }
          }
          personaje = { ...personaje, inventario: inventarioSinElObjeto };
        } else if (personaje?.id === d.destino_personaje_id) {
          personaje = { ...personaje, inventario: [...personaje.inventario, d.objeto] };
        }

        const propuestasRestantes: PropuestaIntercambio[] = [];
        for (const p of s.propuestasIntercambio) {
          const esLaQueSeCompleto =
            p.origen_personaje_id === d.origen_personaje_id && p.objeto_id === d.objeto.objeto_id;
          if (!esLaQueSeCompleto) {
            propuestasRestantes.push(p);
          }
        }

        return {
          personajes,
          personaje,
          propuestasIntercambio: propuestasRestantes,
          log: [nuevoEvento(`Intercambio completado: "${d.objeto.nombre}"`), ...s.log],
        };
      });
      break;
    }
    case 'error': {
      const d = datos as { mensaje: string; origen_personaje_id?: string; objeto_id?: string };
      set((s) => {
        let propuestasIntercambio = s.propuestasIntercambio;
        // Un intercambio_confirmar fallido (el objeto ya no está, o el
        // personaje de origen no es válido) trae de vuelta qué propuesta
        // concreta ha quedado obsoleta — si no la quitáramos aquí, la
        // tarjeta de "te ofrece X" seguiría mostrándose como si todavía se
        // pudiera aceptar.
        if (d.origen_personaje_id && d.objeto_id) {
          const propuestasRestantes: PropuestaIntercambio[] = [];
          for (const p of s.propuestasIntercambio) {
            const esLaQueFallo =
              p.origen_personaje_id === d.origen_personaje_id && p.objeto_id === d.objeto_id;
            if (!esLaQueFallo) {
              propuestasRestantes.push(p);
            }
          }
          propuestasIntercambio = propuestasRestantes;
        }
        return {
          log: [nuevoEvento(d.mensaje, 'aviso'), ...s.log],
          propuestasIntercambio,
        };
      });
      break;
    }
    default:
      break;
  }
}
