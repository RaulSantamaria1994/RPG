import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
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

  // El valor ya llega cambiado desde el servidor (sube o baja de golpe),
  // así que sin esto la barra saltaba en seco de un ancho a otro; animar
  // la transición deja claro de un vistazo cuánto se acaba de perder o
  // recuperar en vez de solo el número final.
  const progreso = useRef(new Animated.Value(proporcion)).current;
  useEffect(() => {
    Animated.timing(progreso, { toValue: proporcion, duration: 450, useNativeDriver: false }).start();
  }, [proporcion]);

  return (
    <View style={estilos.fila}>
      <Text style={estilos.etiqueta}>{etiqueta}</Text>
      <View style={estilos.pista}>
        <Animated.View
          style={[
            estilos.relleno,
            {
              width: progreso.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] }),
              backgroundColor: colorBarra,
            },
          ]}
        />
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
