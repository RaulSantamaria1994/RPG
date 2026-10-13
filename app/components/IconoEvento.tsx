import { Ionicons } from '@expo/vector-icons';
import { color } from '../theme';
import type { EventoLog } from '../types';

/** El icono de librería que corresponde a cada categoría de evento del
 * registro de actividad — nunca un emoji incrustado en el texto. */
export default function IconoEvento({ icono }: { icono: EventoLog['icono'] }) {
  if (icono === 'muerte') return <Ionicons name="skull-outline" size={12} color={color.textoTenue} />;
  if (icono === 'aviso') return <Ionicons name="alert-circle-outline" size={12} color={color.aviso} />;
  return null;
}
