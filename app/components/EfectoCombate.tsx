import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useAcento } from '../store/configStore';
import { color, espacio, radio } from '../theme';
import type { AccionCombateTipo } from '../types';

type Props = {
  tipo: AccionCombateTipo;
  exito?: boolean;
};

type Config = {
  libreria: 'mc' | 'ion';
  icono: string;
  colorBase: string;
  etiqueta: (exito: boolean | undefined) => string;
};

const CONFIG: Record<AccionCombateTipo, Config> = {
  atacar: {
    libreria: 'mc',
    icono: 'sword-cross',
    colorBase: color.combate,
    etiqueta: (exito) => (exito ? 'Golpe certero' : 'El golpe falla'),
  },
  huir: {
    libreria: 'mc',
    icono: 'run-fast',
    colorBase: color.aviso,
    etiqueta: (exito) => (exito ? 'Logra escapar' : 'No logra huir'),
  },
  negociar: {
    libreria: 'mc',
    icono: 'handshake-outline',
    colorBase: color.interactivo,
    etiqueta: (exito) => (exito ? 'Convence al enemigo' : 'La negociación falla'),
  },
  hechizo: {
    libreria: 'mc',
    icono: 'auto-fix',
    colorBase: color.narrativo,
    etiqueta: (exito) => (exito ? 'Hechizo lanzado' : 'El hechizo falla'),
  },
  objeto: {
    libreria: 'mc',
    icono: 'flask-outline',
    colorBase: color.acento,
    etiqueta: () => 'Usa un objeto',
  },
  enemigo_ataca: {
    libreria: 'ion',
    icono: 'flash',
    colorBase: color.peligroFuerte,
    etiqueta: () => 'Golpe recibido',
  },
  enemigo_aturdido: {
    libreria: 'mc',
    icono: 'star-four-points',
    colorBase: color.aviso,
    etiqueta: () => 'Enemigo aturdido',
  },
};

/** Icono animado y propio de cada tipo de acción de combate — una espada
 * para atacar, una figura corriendo para huir, un apretón de manos para
 * negociar, una varita para los hechizos… — para que de un vistazo se
 * note qué acaba de pasar, en vez de que todo luzca igual salvo por el
 * texto del registro. Se monta una vez por evento (quien lo usa le pasa
 * una `key` nueva cada vez) y se desvanece solo. */
export default function EfectoCombate({ tipo, exito }: Props) {
  const progreso = useRef(new Animated.Value(0)).current;
  const giro = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const entrada = Animated.sequence([
      Animated.spring(progreso, { toValue: 1, useNativeDriver: true, speed: 14, bounciness: 10 }),
      Animated.delay(550),
      Animated.timing(progreso, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]);

    let movimiento: Animated.CompositeAnimation | null = null;
    if (tipo === 'hechizo') {
      movimiento = Animated.timing(giro, { toValue: 1, duration: 900, useNativeDriver: true });
    } else if (tipo === 'atacar') {
      movimiento = Animated.sequence([
        Animated.timing(giro, { toValue: 1, duration: 110, useNativeDriver: true }),
        Animated.timing(giro, { toValue: -1, duration: 150, useNativeDriver: true }),
        Animated.timing(giro, { toValue: 0, duration: 110, useNativeDriver: true }),
      ]);
    } else if (tipo === 'enemigo_ataca') {
      movimiento = Animated.sequence([
        Animated.timing(giro, { toValue: 1, duration: 55, useNativeDriver: true }),
        Animated.timing(giro, { toValue: -1, duration: 85, useNativeDriver: true }),
        Animated.timing(giro, { toValue: 1, duration: 85, useNativeDriver: true }),
        Animated.timing(giro, { toValue: 0, duration: 55, useNativeDriver: true }),
      ]);
    }

    entrada.start();
    movimiento?.start();
    return () => {
      entrada.stop();
      movimiento?.stop();
    };
    // Se dispara una sola vez al montar: quien usa este componente le da
    // una `key` nueva en cada evento para forzar el remontaje.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const acento = useAcento();
  const cfg = CONFIG[tipo];
  const Icono = cfg.libreria === 'mc' ? MaterialCommunityIcons : Ionicons;
  // 'objeto' es el único tipo cuyo color base es el acento elegible en
  // Opciones (ver CONFIG más arriba); el resto son colores semánticos fijos.
  const colorBase = tipo === 'objeto' ? acento.acento : cfg.colorBase;
  const colorBorde = exito === true ? color.exito : exito === false ? color.peligro : colorBase;

  const escala = progreso.interpolate({ inputRange: [0, 1], outputRange: [0.4, 1] });
  const rotar =
    tipo === 'hechizo'
      ? giro.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] })
      : giro.interpolate({ inputRange: [-1, 0, 1], outputRange: ['-16deg', '0deg', '16deg'] });
  const desplazar = giro.interpolate({ inputRange: [-1, 0, 1], outputRange: [-5, 0, 5] });

  return (
    <Animated.View
      style={[estilos.base, { borderColor: colorBorde, opacity: progreso, transform: [{ scale: escala }] }]}
      pointerEvents="none"
    >
      <Animated.View
        style={{ transform: [{ rotate: rotar }, { translateX: tipo === 'enemigo_ataca' ? desplazar : 0 }] }}
      >
        <Icono name={cfg.icono as never} size={20} color={colorBase} />
      </Animated.View>
      <Text style={[estilos.texto, { color: colorBorde }]}>{cfg.etiqueta(exito)}</Text>
    </Animated.View>
  );
}

const estilos = StyleSheet.create({
  base: {
    position: 'absolute',
    top: 78,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    zIndex: 11,
    backgroundColor: color.fondoElevado,
    borderWidth: 1,
    borderRadius: radio.pill,
    paddingVertical: 6,
    paddingHorizontal: espacio.md,
    shadowColor: '#000',
    shadowOpacity: 0.35,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
  },
  texto: { fontSize: 12, fontWeight: '700' },
});
