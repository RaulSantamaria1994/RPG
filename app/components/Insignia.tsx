import type { ComponentProps } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAcento } from '../store/configStore';
import { color, fuente, radio } from '../theme';

type Tono = 'neutro' | 'aviso' | 'peligro' | 'exito' | 'acento';

const TONOS_FIJOS: Record<Exclude<Tono, 'acento'>, { fondo: string; texto: string }> = {
  neutro: { fondo: color.superficieAlt, texto: color.textoSecundario },
  aviso: { fondo: color.avisoSuave, texto: color.aviso },
  peligro: { fondo: color.peligroSuave, texto: color.peligro },
  exito: { fondo: color.exitoSuave, texto: color.exito },
};

type Props = {
  texto: string;
  tono?: Tono;
  /** Nombre de un icono de Ionicons a mostrar antes del texto, en vez de
   * un emoji incrustado en la cadena. */
  icono?: ComponentProps<typeof Ionicons>['name'];
};

/** Etiqueta corta de estado (p. ej. "agotada", "en curso…", "3/4
 * confirmados"). Con forma de talón de ticket (una perforación punteada
 * cerca del borde izquierdo) en vez de la píldora redondeada de panel de
 * control que llevaba antes. */
export default function Insignia({ texto, tono = 'neutro', icono }: Props) {
  const acento = useAcento();
  const t = tono === 'acento' ? { fondo: acento.acentoSuave, texto: acento.acentoFuerte } : TONOS_FIJOS[tono];
  return (
    <View style={[estilos.base, { backgroundColor: t.fondo, borderColor: t.texto }]}>
      <View style={[estilos.perforacion, { borderLeftColor: t.texto }]} />
      {icono && <Ionicons name={icono} size={11} color={t.texto} />}
      <Text style={[estilos.texto, { color: t.texto }]}>{texto}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: radio.sm,
    borderWidth: 1,
    paddingLeft: 14,
    paddingRight: 9,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  perforacion: {
    position: 'absolute',
    left: 7,
    top: 3,
    bottom: 3,
    borderLeftWidth: 1,
    borderStyle: 'dashed',
    opacity: 0.5,
  },
  texto: { fontFamily: fuente.sello, fontSize: 10, letterSpacing: 0.4, textTransform: 'uppercase' },
});
