import { StyleSheet, Text, View } from 'react-native';
import { color, radio } from '../theme';

type Props = {
  etiqueta: string;
  actual: number;
  maximo: number;
  /** Color de la barra cuando va bien; por debajo de ciertos umbrales se
   * tiñe de aviso/peligro automáticamente (pensado para vida). Pon
   * `sinAlerta` para una barra que no deba asustar a nadie (p. ej. maná). */
  sinAlerta?: boolean;
};

/** Barra de progreso para vida/maná — mucho más legible de un vistazo que
 * el texto plano "PV 10/16" que había antes, y cambia de color si el
 * personaje está en apuros. */
export default function BarraRecurso({ etiqueta, actual, maximo, sinAlerta }: Props) {
  const proporcion = maximo > 0 ? Math.max(0, Math.min(1, actual / maximo)) : 0;
  const colorBarra = sinAlerta
    ? color.acento
    : proporcion <= 0.25
      ? color.peligro
      : proporcion <= 0.5
        ? color.aviso
        : color.exito;

  return (
    <View style={estilos.fila}>
      <Text style={estilos.etiqueta}>{etiqueta}</Text>
      <View style={estilos.pista}>
        <View style={[estilos.relleno, { width: `${proporcion * 100}%`, backgroundColor: colorBarra }]} />
      </View>
      <Text style={estilos.valor}>
        {actual}/{maximo}
      </Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  fila: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  etiqueta: { color: color.textoSecundario, fontSize: 11, fontWeight: '700', width: 38 },
  pista: {
    flex: 1,
    height: 8,
    borderRadius: radio.pill,
    backgroundColor: color.fondoElevado,
    overflow: 'hidden',
  },
  relleno: { height: '100%', borderRadius: radio.pill },
  valor: { color: color.textoSecundario, fontSize: 11, width: 46, textAlign: 'right' },
});
