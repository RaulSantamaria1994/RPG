import { Image, StyleSheet } from 'react-native';

/** Textura de grano de papel, en mosaico y a muy baja opacidad, por
 * encima de toda la pantalla — rompe el look "vector plano" sin pesar
 * casi nada (24KB) y sin afectar los toques, gracias a pointerEvents
 * "none". */
export default function TexturaGrano() {
  return (
    <Image
      source={require('../assets/grano.png')}
      resizeMode="repeat"
      style={styles.textura}
    />
  );
}

const styles = StyleSheet.create({
  textura: { ...StyleSheet.absoluteFillObject, opacity: 0.035, pointerEvents: 'none' },
});
