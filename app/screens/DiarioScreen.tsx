import { useRef } from 'react';
import { Animated, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { GlifoNodo } from '../components';
import { useSalaStore } from '../store/salaStore';
import { color, espacio, fuente, radio, tipo } from '../theme';

// Un papel algo más claro y cálido que las superficies normales de la
// app — para que las pistas lean como hojas sueltas de un cuaderno, no
// como una tarjeta más de la interfaz.
const PAPEL_NOTA = '#d8c9a3';
const TINTA_NOTA = '#2a2318';
const TINTA_NOTA_TENUE = '#5c4a2a';

// Cada entrada se inclina un poco distinto, como páginas sueltas — nada
// de rotación real al azar (eso cambiaría en cada repintado), solo un
// puñado de valores fijos que se repiten en ciclo.
const GIROS = ['-1.2deg', '0.8deg', '-0.5deg', '1deg', '-0.9deg', '0.6deg'];

export default function DiarioScreen() {
  const diario = useSalaStore((s) => s.estado?.diario) ?? [];
  const animaciones = useRef(new Map<string, Animated.Value>()).current;

  function animacionDe(flag: string): Animated.Value {
    let valor = animaciones.get(flag);
    if (!valor) {
      valor = new Animated.Value(0);
      animaciones.set(flag, valor);
      Animated.timing(valor, { toValue: 1, duration: 450, useNativeDriver: true }).start();
    }
    return valor;
  }

  return (
    <ScrollView contentContainerStyle={styles.contenedor}>
      <Text style={styles.titulo}>Diario de pistas</Text>
      <Text style={styles.subtitulo}>
        {diario.length > 0
          ? `Lo que sabéis hasta ahora, en el orden en que lo fuisteis descubriendo.`
          : 'Aún no habéis descubierto ninguna pista — irán apareciendo aquí según avancéis en la historia.'}
      </Text>

      {diario.length === 0 ? (
        <View style={styles.vacio}>
          <Ionicons name="bookmark-outline" size={28} color={color.textoTenue} />
          <Text style={styles.vacioTexto}>El diario está en blanco, de momento.</Text>
        </View>
      ) : (
        diario.map((entrada, i) => {
          const progreso = animacionDe(entrada.flag);
          return (
            <Animated.View
              key={entrada.flag}
              style={[
                styles.nota,
                {
                  transform: [
                    { translateY: progreso.interpolate({ inputRange: [0, 1], outputRange: [14, 0] }) },
                    { rotate: GIROS[i % GIROS.length] },
                  ],
                  opacity: progreso,
                },
              ]}
            >
              <View style={styles.cabeceraEntrada}>
                <GlifoNodo tipo="narrativo" color={TINTA_NOTA_TENUE} tamano={13} />
                <Text style={styles.numeroEntrada}>PISTA {i + 1}</Text>
              </View>
              <Text style={styles.textoEntrada}>{entrada.texto}</Text>
            </Animated.View>
          );
        })
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: espacio.xl, backgroundColor: color.fondo, flexGrow: 1, gap: espacio.lg },
  titulo: { ...tipo.titulo, fontSize: 26 },
  subtitulo: { ...tipo.nota, marginBottom: espacio.sm },
  vacio: { alignItems: 'center', gap: espacio.sm, paddingVertical: espacio.xxl },
  vacioTexto: { ...tipo.nota, textAlign: 'center' },
  nota: {
    backgroundColor: PAPEL_NOTA,
    borderRadius: radio.papel,
    borderWidth: 1,
    borderColor: 'rgba(42,35,24,0.25)',
    padding: espacio.lg,
    gap: espacio.xs,
  },
  cabeceraEntrada: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  numeroEntrada: { fontFamily: fuente.sello, color: TINTA_NOTA_TENUE, fontSize: 11, letterSpacing: 1 },
  textoEntrada: { fontFamily: fuente.display, color: TINTA_NOTA, fontSize: 14.5, lineHeight: 21 },
});
