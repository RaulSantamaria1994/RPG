import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useConfigStore } from '../store/configStore';
import { PALETA_ACENTOS, type AcentoId, color, espacio, radio, tipo } from '../theme';

/** Opciones de la app en sí (no de una partida concreta). De momento solo
 * el color de acento, pensado para crecer con lo que haga falta más
 * adelante. El cambio se ve al instante en toda la app, sin reiniciar. */
export default function OpcionesScreen() {
  const acentoId = useConfigStore((s) => s.acentoId);
  const elegirAcento = useConfigStore((s) => s.elegirAcento);

  return (
    <ScrollView contentContainerStyle={styles.contenedor}>
      <Text style={styles.titulo}>Opciones</Text>
      <Text style={styles.subtitulo}>Elige el color de acento de la app.</Text>

      <View style={styles.paleta}>
        {(Object.keys(PALETA_ACENTOS) as AcentoId[]).map((id) => {
          const opcion = PALETA_ACENTOS[id];
          const elegido = id === acentoId;
          return (
            <TouchableOpacity
              key={id}
              style={[styles.fila, elegido && { borderColor: opcion.acento, backgroundColor: opcion.acentoSuave }]}
              onPress={() => elegirAcento(id)}
              activeOpacity={0.8}
            >
              <View style={[styles.muestra, { backgroundColor: opcion.acento }]} />
              <Text style={styles.nombre}>{opcion.nombre}</Text>
              {elegido && <Ionicons name="checkmark-circle" size={20} color={opcion.acento} />}
            </TouchableOpacity>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: espacio.xl, backgroundColor: color.fondo, flexGrow: 1, gap: espacio.lg },
  titulo: { ...tipo.titulo, fontSize: 26, marginBottom: 2 },
  subtitulo: { ...tipo.nota },
  paleta: { gap: espacio.sm },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.md,
    backgroundColor: color.superficie,
    borderRadius: radio.lg,
    borderWidth: 1,
    borderColor: color.borde,
    padding: espacio.md,
  },
  muestra: { width: 28, height: 28, borderRadius: radio.pill },
  nombre: { color: color.texto, fontSize: 15, fontWeight: '600', flex: 1 },
});
