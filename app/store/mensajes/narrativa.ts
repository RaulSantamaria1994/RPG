/** Mensajes de avance narrativo: cambio de nodo, bloqueo/liberación de
 * palabras clave mientras alguien las resuelve, resultado de una tirada
 * (2d6 + modificador de la movida), ayuda a otro, objetos otorgados y
 * daño al llegar a un nodo.
 */
import type { Banda, EstadoPublico, EventoLog } from '../../types';
import type { FijarEstado } from './comun';
import { nuevoEvento } from './comun';

export function nodo_actualizado(datos: Record<string, unknown>, set: FijarEstado): void {
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
      log: [...eventosPistas, ...s.log],
    };
  });
}

export function palabra_clave_bloqueada(datos: Record<string, unknown>, set: FijarEstado): void {
  const { clave, jugador } = datos as { clave: string; jugador: string };
  set((s) => ({ palabrasBloqueadas: { ...s.palabrasBloqueadas, [clave]: jugador } }));
}

export function palabra_clave_liberada(datos: Record<string, unknown>, set: FijarEstado): void {
  const { clave } = datos as { clave: string };
  set((s) => {
    const copia = { ...s.palabrasBloqueadas };
    delete copia[clave];
    return { palabrasBloqueadas: copia };
  });
}

const ETIQUETA_BANDA: Record<Banda, string> = {
  exito: 'ÉXITO',
  exito_con_coste: 'ÉXITO CON COSTE',
  fallo: 'FALLO',
};

export function tirada_resultado(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as {
    personaje_nombre?: string;
    palabra_clave?: string;
    exito: boolean;
    tirada?: { dados?: [number, number]; total?: number; banda?: Banda };
    cambios?: {
      dano_aplicado?: number;
      objeto_otorgado?: { nombre: string; categoria?: string } | null;
    };
  };
  const quien = d.personaje_nombre ?? 'El grupo';
  const resultado = d.tirada?.banda ? ETIQUETA_BANDA[d.tirada.banda] : d.exito ? 'ÉXITO' : 'FALLO';
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
      dados: d.tirada?.dados,
      total: d.tirada?.total,
      banda: d.tirada?.banda,
      exito: d.exito,
      quien,
    },
  }));
}

export function objetos_otorgados(datos: Record<string, unknown>, set: FijarEstado): void {
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
}

export function dano_al_llegar(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as { cantidad: number; afectados: string[] };
  set((s) => ({
    log: [nuevoEvento(`El grupo sufre ${d.cantidad} de daño (-${d.cantidad} PV)`, 'aviso'), ...s.log],
  }));
}

export function ayuda_resuelta(datos: Record<string, unknown>, set: FijarEstado): void {
  const d = datos as {
    personaje_nombre: string;
    palabra_clave: string;
    tirada: { dados?: [number, number]; total?: number; banda?: Banda; exito: boolean };
  };
  const resultado = d.tirada.exito ? 'consigue ayudar' : 'no logra ayudar';
  set((s) => ({
    log: [nuevoEvento(`${d.personaje_nombre} ${resultado} con "${d.palabra_clave}"`), ...s.log],
    ultimaTirada: {
      dados: d.tirada.dados,
      total: d.tirada.total,
      banda: d.tirada.banda,
      exito: d.tirada.exito,
      quien: d.personaje_nombre,
    },
  }));
}
