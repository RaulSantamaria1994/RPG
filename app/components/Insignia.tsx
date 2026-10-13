import { StyleSheet, Text, View } from 'react-native';
import { color, radio } from '../theme';

type Tono = 'neutro' | 'aviso' | 'peligro' | 'exito' | 'acento';

const TONOS: Record<Tono, { fondo: string; texto: string }> = {
  neutro: { fondo: color.superficieAlt, texto: color.textoSecundario },
  aviso: { fondo: color.avisoSuave, texto: color.aviso },
  peligro: { fondo: color.peligroSuave, texto: color.peligro },
  exito: { fondo: color.exitoSuave, texto: color.exito },
  acento: { fondo: color.acentoSuave, texto: color.acentoFuerte },
};

/** Etiqueta corta de estado (p. ej. "agotada", "en curso…", "3/4
 * confirmados"). Sustituye al texto de color suelto que antes llevaba
 * cada pantalla por su cuenta. */
export default function Insignia({ texto, tono = 'neutro' }: { texto: string; tono?: Tono }) {
  const t = TONOS[tono];
  return (
    <View style={[estilos.base, { backgroundColor: t.fondo }]}>
      <Text style={[estilos.texto, { color: t.texto }]}>{texto}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  base: { borderRadius: radio.pill, paddingHorizontal: 9, paddingVertical: 3, alignSelf: 'flex-start' },
  texto: { fontSize: 11, fontWeight: '700' },
});
