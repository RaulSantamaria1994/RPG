/** Mensajes de intercambio de objetos entre jugadores, y el error genérico
 * del servidor — que también limpia una propuesta de intercambio que haya
 * quedado obsoleta (el objeto ya no estaba disponible).
 */
import { actualizarInventario, nuevoEvento, type FijarEstado, type PropuestaIntercambio } from './comun';

export function intercambio_propuesto(datos: Record<string, unknown>, set: FijarEstado): void {
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
}

export function intercambio_completado(datos: Record<string, unknown>, set: FijarEstado): void {
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
}

export function error(datos: Record<string, unknown>, set: FijarEstado): void {
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
}
