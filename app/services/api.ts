import { API_BASE_URL } from './config';
import type {
  Atributo,
  HabilidadPasiva,
  HistoriaResumen,
  NodoResumen,
  Personaje,
  PersonajePregenerado,
  Sala,
} from '../types';

class ErrorApi extends Error {}

async function peticion<T>(
  ruta: string,
  opciones: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, headers, ...resto } = opciones;
  const respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
    ...resto,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({}));
    throw new ErrorApi(cuerpo.detail || `Error ${respuesta.status}`);
  }
  if (respuesta.status === 204) return undefined as T;
  return respuesta.json() as Promise<T>;
}

export const api = {
  listarHistorias: () => peticion<HistoriaResumen[]>('/historias'),

  crearSala: (datos: {
    master_nombre: string;
    historia_id: string;
    nombre?: string;
    min_jugadores?: number;
    max_jugadores?: number;
    muerte_permanente?: boolean;
  }) =>
    peticion<{ sala: Sala; master_token: string }>('/salas', {
      method: 'POST',
      body: JSON.stringify(datos),
    }),

  obtenerSala: (codigo: string) => peticion<Sala>(`/salas/${codigo}`),

  obtenerEstadoSala: (codigo: string, token: string) =>
    peticion<{ sala: Sala; estado: unknown; nodo_actual: unknown; personajes: Personaje[] }>(
      `/salas/${codigo}/estado`,
      { token }
    ),

  listarPregenerados: (codigo: string) =>
    peticion<PersonajePregenerado[]>(`/salas/${codigo}/pregenerados`),

  crearPersonajePregenerado: (
    codigo: string,
    datos: { jugador_nombre: string; personaje_pregenerado_id: string }
  ) =>
    peticion<{ personaje: Personaje; token: string }>(
      `/salas/${codigo}/personajes/pregenerado`,
      { method: 'POST', body: JSON.stringify(datos) }
    ),

  crearPersonajePersonalizado: (
    codigo: string,
    datos: {
      jugador_nombre: string;
      nombre: string;
      atributos: Record<Atributo, number>;
      habilidad_pasiva: string;
    }
  ) =>
    peticion<{ personaje: Personaje; token: string }>(
      `/salas/${codigo}/personajes/personalizado`,
      { method: 'POST', body: JSON.stringify(datos) }
    ),

  habilidadesPersonalizado: (codigo: string) =>
    peticion<HabilidadPasiva[]>(`/salas/${codigo}/habilidades-personalizado`),

  listarNodos: (codigo: string, token: string) =>
    peticion<NodoResumen[]>(`/salas/${codigo}/nodos`, { token }),

  cerrarSala: (codigo: string, token: string) =>
    peticion<Sala>(`/salas/${codigo}/cerrar`, { method: 'POST', token }),

  borrarSala: (codigo: string, token: string) =>
    peticion<void>(`/salas/${codigo}`, { method: 'DELETE', token }),
};

export { ErrorApi };
