import type { ReactNode } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { color, radio, espacio } from '../theme';

type Props = {
  children: ReactNode;
  acento?: string;
  seleccionada?: boolean;
  atenuada?: boolean;
  style?: ViewStyle;
};

/** Contenedor de superficie estándar: usado para secciones, opciones
 * elegibles y tarjetas de contenido. `acento` pinta un borde lateral del
 * color dado (p. ej. el color del tipo de nodo), útil para orientar al
 * jugador de un vistazo. */
export default function Tarjeta({ children, acento, seleccionada, atenuada, style }: Props) {
  return (
    <View
      style={[
        estilos.base,
        acento ? { borderLeftWidth: 3, borderLeftColor: acento } : null,
        seleccionada ? estilos.seleccionada : null,
        atenuada ? estilos.atenuada : null,
        style,
      ]}
    >
      {children}
    </View>
  );
}

const estilos = StyleSheet.create({
  base: {
    backgroundColor: color.superficie,
    borderRadius: radio.lg,
    padding: espacio.md,
    borderWidth: 1,
    borderColor: color.borde,
    gap: espacio.xs,
  },
  seleccionada: { borderColor: color.acentoFuerte, backgroundColor: color.acentoSuave },
  atenuada: { opacity: 0.55 },
});
