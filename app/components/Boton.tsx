import type { ReactNode } from 'react';
import { ActivityIndicator, Animated, StyleSheet, Text, TouchableOpacity, View, type ViewStyle } from 'react-native';
import { color, radio, espacio } from '../theme';
import { useAcento } from '../store/configStore';
import { useEscalaPresion } from '../hooks/useEscalaPresion';

type Variante = 'primario' | 'secundario' | 'peligro' | 'fantasma';

type Props = {
  texto: string;
  subtexto?: string;
  /** Icono (de @expo/vector-icons) a mostrar a la izquierda del texto —
   * nunca un emoji suelto. */
  icono?: ReactNode;
  onPress: () => void;
  variante?: Variante;
  disabled?: boolean;
  cargando?: boolean;
  flex?: boolean;
  style?: ViewStyle;
};

/** Botón de acción consistente en toda la app: mismo tacto, mismos estados
 * de cargando/deshabilitado, cuatro variantes semánticas. */
export default function Boton({
  texto,
  subtexto,
  icono,
  onPress,
  variante = 'primario',
  disabled,
  cargando,
  flex,
  style,
}: Props) {
  const estilos = ESTILOS_VARIANTE[variante];
  const acento = useAcento();
  // Solo primario y secundario usan el acento (relleno sólido el primero,
  // borde el segundo) — los otros dos no lo tocan, así que no hace falta
  // sobrescribir nada para ellos.
  const contenedorAcento: ViewStyle | undefined =
    variante === 'primario'
      ? { backgroundColor: acento.acento, borderColor: acento.acento }
      : variante === 'secundario'
        ? { borderColor: acento.acento }
        : undefined;
  const { escala, presionar, soltar } = useEscalaPresion();
  return (
    <Animated.View style={[flex && { flex: 1 }, { transform: [{ scale: escala }] }]}>
      <TouchableOpacity
        style={[
          estiloBase.base,
          estilos.contenedor,
          contenedorAcento,
          flex && { flex: 1 },
          (disabled || cargando) && estiloBase.deshabilitado,
          style,
        ]}
        onPress={onPress}
        onPressIn={presionar}
        onPressOut={soltar}
        disabled={disabled || cargando}
        activeOpacity={0.75}
      >
        {cargando ? (
          <ActivityIndicator color={estilos.texto.color} />
        ) : (
          <View>
            <View style={estiloBase.filaTexto}>
              {icono}
              <Text style={[estiloBase.texto, estilos.texto]}>{texto}</Text>
            </View>
            {subtexto ? <Text style={[estiloBase.subtexto, estilos.subtexto]}>{subtexto}</Text> : null}
          </View>
        )}
      </TouchableOpacity>
    </Animated.View>
  );
}

const estiloBase = StyleSheet.create({
  base: {
    borderRadius: radio.md,
    paddingVertical: 13,
    paddingHorizontal: espacio.lg,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  filaTexto: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  texto: { fontSize: 15, fontWeight: '700' },
  subtexto: { fontSize: 12, marginTop: 3, textAlign: 'center' },
  deshabilitado: { opacity: 0.45 },
});

const ESTILOS_VARIANTE: Record<Variante, { contenedor: ViewStyle; texto: { color: string }; subtexto: { color: string } }> = {
  primario: {
    contenedor: { backgroundColor: color.acento, borderColor: color.acento },
    texto: { color: color.textoSobreAcento },
    subtexto: { color: 'rgba(255,255,255,0.75)' },
  },
  secundario: {
    contenedor: { backgroundColor: color.superficieAlt, borderColor: color.acento },
    texto: { color: color.texto },
    subtexto: { color: color.textoSecundario },
  },
  peligro: {
    contenedor: { backgroundColor: color.peligroFuerte, borderColor: color.peligroFuerte },
    texto: { color: color.textoSobreAcento },
    subtexto: { color: 'rgba(255,255,255,0.75)' },
  },
  fantasma: {
    contenedor: { backgroundColor: 'transparent', borderColor: 'transparent' },
    texto: { color: color.peligro },
    subtexto: { color: color.textoSecundario },
  },
};
