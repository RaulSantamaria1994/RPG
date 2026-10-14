import { useRef } from 'react';
import { Animated } from 'react-native';

/** Pequeño "muelle" de escala para dar tacto a un botón: se encoge un poco
 * al pulsar y rebota de vuelta a su tamaño al soltar. Un solo sitio para
 * este gesto en vez de repetir la misma animación en cada botón. */
export function useEscalaPresion(hacia = 0.96) {
  const escala = useRef(new Animated.Value(1)).current;

  function presionar() {
    Animated.spring(escala, { toValue: hacia, useNativeDriver: true, speed: 50, bounciness: 6 }).start();
  }

  function soltar() {
    Animated.spring(escala, { toValue: 1, useNativeDriver: true, speed: 50, bounciness: 6 }).start();
  }

  return { escala, presionar, soltar };
}
