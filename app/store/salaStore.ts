import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { ClienteSala } from '../services/websocket';
import type { AccionCombateTipo, Banda, EstadoPublico, EventoLog, Personaje, Sala } from '../types';
import { ESTADO_INICIAL_TRANSITORIO, type EpilogoPersonal, type PropuestaIntercambio } from './mensajes/comun';
import { procesarMensaje } from './mensajes';

export type { EpilogoPersonal, PropuestaIntercambio };

export interface SalaState {
  rol: 'master' | 'jugador' | null;
  sala: Sala | null;
  token: string | null;
  personaje: Personaje | null;
  estado: EstadoPublico | null;
  personajes: Personaje[];
  log: EventoLog[];
  palabrasBloqueadas: Record<string, string>;
  propuestasIntercambio: PropuestaIntercambio[];
  conectado: boolean;
  /** Solo tiene sentido cuando `conectado` es false: distingue "todavía no
   * se ha logrado la primera conexión" de "se tenía y se acaba de perder,
   * reintentando sola". Así la pantalla puede decir "Conectando…" o
   * "Reconectando…" según toque. */
  reintentandoConexion: boolean;
  cliente: ClienteSala | null;
  ultimaTirada: { dados?: [number, number]; total?: number; banda?: Banda; exito: boolean; quien: string } | null;
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

