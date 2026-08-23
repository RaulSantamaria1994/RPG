import { WS_BASE_URL } from './config';

export type MensajeWs = { tipo: string; datos: Record<string, unknown> };
type Escuchador = (mensaje: MensajeWs) => void;

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
    };

    this.socket.onclose = () => {
      if (this.cerradoManualmente) return;
      const espera = Math.min(1000 * 2 ** this.intentosReconexion, 10000);
      this.intentosReconexion += 1;
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
}
