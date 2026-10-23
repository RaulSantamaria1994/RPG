import type { ReactNode } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { useAcento } from '../store/configStore';
import { color, radio, espacio } from '../theme';

type Props = {
  children: ReactNode;
  acento?: string;
  seleccionada?: boolean;
  atenuada?: boolean;
  style?: ViewStyle;
};

/** Contenedor de superficie estándar: usado para secciones, opciones
 * elegibles y tarjetas de contenido. `acento` pinta una regla fina arriba
 * del color dado (p. ej. el color del tipo de nodo), útil para orientar
 * al jugador de un vistazo. Es casi angular (radio.papel) en vez de muy
 * redondeada — el redondeo suave se reserva para lo que se toca. */
export default function Tarjeta({ children, acento, seleccionada, atenuada, style }: Props) {
  const acentoElegido = useAcento();
  return (
    <View
      style={[
        estilos.base,
        acento ? { borderTopWidth: 2, borderTopColor: acento } : null,
        seleccionada ? { borderColor: acentoElegido.acentoFuerte, backgroundColor: acentoElegido.acentoSuave } : null,
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
    borderRadius: radio.papel,
    padding: espacio.md,
    borderWidth: 1,
    borderColor: color.bordeSutil,
    gap: espacio.xs,
  },
  atenuada: { opacity: 0.55 },
});
