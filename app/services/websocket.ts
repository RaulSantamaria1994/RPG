import { WS_BASE_URL } from './config';

export type MensajeWs = { tipo: string; datos: Record<string, unknown> };
type Escuchador = (mensaje: MensajeWs) => void;

// Códigos que el backend usa para cerrar el socket cuando la sesión ya no es
// válida (token caducado/incorrecto, la sala ya no existe, o el máster te ha
// expulsado): no tiene sentido reintentar reconectar en bucle, hay que avisar
// y volver al inicio.
const CODIGOS_SESION_INVALIDA = new Set([4401, 4404, 4403]);

export class ClienteSala {
  private socket: WebSocket | null = null;
  private escuchadores = new Set<Escuchador>();
  private codigo: string;
  private token: string;
  private cerradoManualmente = false;
  private intentosReconexion = 0;

  constructor(codigo: string, token: string) {
    this.codigo = codigo;
    this.token = token;
  }

  conectar(): void {
    this.cerradoManualmente = false;
    // Se avisa de que (todavía/de nuevo) no hay conexión en cuanto se
    // intenta — `reintentando` distingue el primer intento ("Conectando…")
    // de una recuperación tras perder la conexión ("Reconectando…").
    this.notificar({ tipo: '_estado_conexion', datos: { conectado: false, reintentando: this.intentosReconexion > 0 } });
    this.socket = new WebSocket(`${WS_BASE_URL}/ws/sala/${this.codigo}?token=${this.token}`);

    this.socket.onmessage = (evento) => {
      try {
        const mensaje = JSON.parse(evento.data) as MensajeWs;
        this.escuchadores.forEach((fn) => fn(mensaje));
      } catch {
        // ignora frames que no sean JSON válido
      }
    };

    this.socket.onopen = () => {
      this.intentosReconexion = 0;
      this.notificar({ tipo: '_estado_conexion', datos: { conectado: true, reintentando: false } });
    };

    this.socket.onclose = (evento) => {
      if (this.cerradoManualmente) return;

      if (CODIGOS_SESION_INVALIDA.has(evento.code)) {
        this.notificar({ tipo: '_sesion_invalida', datos: { codigo: evento.code } });
        return;
      }

      const espera = Math.min(1000 * 2 ** this.intentosReconexion, 10000);
      this.intentosReconexion += 1;
      // Se avisa ya aquí (no solo al reintentar en conectar()) para que la
      // interfaz refleje la pérdida de conexión al instante, sin esperar a
      // que termine la cuenta atrás del siguiente intento.
      this.notificar({ tipo: '_estado_conexion', datos: { conectado: false, reintentando: true } });
      setTimeout(() => this.conectar(), espera);
    };
  }

  desconectar(): void {
    this.cerradoManualmente = true;
    this.socket?.close();
    this.socket = null;
  }

  enviar(tipo: string, datos: Record<string, unknown> = {}): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ tipo, datos }));
    }
  }

  suscribir(fn: Escuchador): () => void {
    this.escuchadores.add(fn);
    return () => this.escuchadores.delete(fn);
  }

  private notificar(mensaje: MensajeWs): void {
    this.escuchadores.forEach((fn) => fn(mensaje));
  }
}
