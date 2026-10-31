import type { MensajeWs } from '../../services/websocket';
import type { FijarEstado, ObtenerEstado } from './comun';
import { _estado_conexion, _sesion_invalida, estado_inicial, jugador_conectado, jugador_desconectado, jugador_expulsado } from './conexion';
import {
  ayuda_resuelta,
  dano_al_llegar,
  nodo_actualizado,
  objetos_otorgados,
  palabra_clave_bloqueada,
  palabra_clave_liberada,
  tirada_resultado,
} from './narrativa';
import { combate_resultado } from './combate';
import { equipo_cambiado, personaje_actualizado, personaje_ajustado, personaje_muerto } from './personaje';
import { error, intercambio_completado, intercambio_propuesto } from './intercambio';

type ManejadorMensaje = (datos: Record<string, unknown>, set: FijarEstado, get: ObtenerEstado) => void;

// Un manejador por tipo de mensaje que puede mandar el servidor, repartidos
// por dominio en los módulos hermanos (conexion/narrativa/combate/
// personaje/intercambio) — el mismo reparto que ya tiene el backend en
// websockets/handlers/. Los tipos que empiezan por "_" no vienen del
// servidor: los genera ClienteSala (services/websocket.ts) para que el
// store reaccione a la conexión en sí.
const MANEJADORES: Record<string, ManejadorMensaje> = {
  _estado_conexion,
  _sesion_invalida,
  estado_inicial,
  nodo_actualizado,
  palabra_clave_bloqueada,
  palabra_clave_liberada,
  tirada_resultado,
  combate_resultado,
  personaje_ajustado,
  equipo_cambiado,
  personaje_actualizado,
  personaje_muerto,
  jugador_expulsado,
  jugador_conectado,
  jugador_desconectado,
  objetos_otorgados,
  dano_al_llegar,
  ayuda_resuelta,
  intercambio_propuesto,
  intercambio_completado,
  error,
};

export function procesarMensaje(mensaje: MensajeWs, set: FijarEstado, get: ObtenerEstado): void {
  const manejador = MANEJADORES[mensaje.tipo];
  if (manejador) {
    manejador(mensaje.datos, set, get);
  }
}
