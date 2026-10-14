import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { color, espacio } from '../theme';

type Props = {
  /** true mientras no hay conexión abierta con el servidor — tanto en el
   * primer intento como recuperándose de una caída. */
  conectado: boolean;
  /** Distingue "todavía no se ha logrado la primera conexión" de "se tenía
   * y se acaba de perder, reintentando sola". */
  reintentando: boolean;
};

/** Franja fina y discreta en lo alto de la pantalla mientras el WebSocket
 * no está abierto — sin esto, una caída de conexión se veía igual que una
 * partida al día: nada se actualizaba y no había ninguna pista de por qué. */
export default function IndicadorConexion({ conectado, reintentando }: Props) {
  if (conectado) return null;

  return (
    <View style={estilos.base}>
      <ActivityIndicator size="small" color={color.aviso} />
      <Text style={estilos.texto}>{reintentando ? 'Reconectando…' : 'Conectando…'}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: espacio.sm,
    backgroundColor: color.avisoSuave,
    paddingVertical: 6,
  },
  texto: { color: color.aviso, fontSize: 12, fontWeight: '700' },
});
