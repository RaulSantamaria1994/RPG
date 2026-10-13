import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View, type ViewStyle } from 'react-native';
import { color, radio, espacio } from '../theme';

type Variante = 'primario' | 'secundario' | 'peligro' | 'fantasma';

type Props = {
  texto: string;
  subtexto?: string;
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
  onPress,
  variante = 'primario',
  disabled,
  cargando,
  flex,
  style,
}: Props) {
  const estilos = ESTILOS_VARIANTE[variante];
  return (
    <TouchableOpacity
      style={[
        estiloBase.base,
        estilos.contenedor,
        flex && { flex: 1 },
        (disabled || cargando) && estiloBase.deshabilitado,
        style,
      ]}
      onPress={onPress}
      disabled={disabled || cargando}
      activeOpacity={0.75}
    >
      {cargando ? (
        <ActivityIndicator color={estilos.texto.color} />
      ) : (
        <View>
          <Text style={[estiloBase.texto, estilos.texto]}>{texto}</Text>
          {subtexto ? <Text style={[estiloBase.subtexto, estilos.subtexto]}>{subtexto}</Text> : null}
        </View>
      )}
    </TouchableOpacity>
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
