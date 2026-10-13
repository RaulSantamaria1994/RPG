import type { ComponentProps } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { color, radio } from '../theme';

type Tono = 'neutro' | 'aviso' | 'peligro' | 'exito' | 'acento';

const TONOS: Record<Tono, { fondo: string; texto: string }> = {
  neutro: { fondo: color.superficieAlt, texto: color.textoSecundario },
  aviso: { fondo: color.avisoSuave, texto: color.aviso },
  peligro: { fondo: color.peligroSuave, texto: color.peligro },
  exito: { fondo: color.exitoSuave, texto: color.exito },
  acento: { fondo: color.acentoSuave, texto: color.acentoFuerte },
};

type Props = {
  texto: string;
  tono?: Tono;
  /** Nombre de un icono de Ionicons a mostrar antes del texto, en vez de
   * un emoji incrustado en la cadena. */
  icono?: ComponentProps<typeof Ionicons>['name'];
};

/** Etiqueta corta de estado (p. ej. "agotada", "en curso…", "3/4
 * confirmados"). Sustituye al texto de color suelto que antes llevaba
 * cada pantalla por su cuenta. */
export default function Insignia({ texto, tono = 'neutro', icono }: Props) {
  const t = TONOS[tono];
  return (
    <View style={[estilos.base, { backgroundColor: t.fondo }]}>
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
    borderRadius: radio.pill,
    paddingHorizontal: 9,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  texto: { fontSize: 11, fontWeight: '700' },
});
