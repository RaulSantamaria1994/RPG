import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Tarjeta } from '../components';
import { useSalaStore } from '../store/salaStore';
import { color, espacio, tipo } from '../theme';

export default function DiarioScreen() {
  const diario = useSalaStore((s) => s.estado?.diario) ?? [];

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
        diario.map((entrada, i) => (
          <Tarjeta key={entrada.flag} acento={color.narrativo} style={styles.tarjeta}>
            <View style={styles.cabeceraEntrada}>
              <Ionicons name="bookmark" size={14} color={color.narrativo} />
              <Text style={styles.numeroEntrada}>Pista {i + 1}</Text>
            </View>
            <Text style={styles.textoEntrada}>{entrada.texto}</Text>
          </Tarjeta>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: espacio.xl, backgroundColor: color.fondo, flexGrow: 1, gap: espacio.md },
  titulo: { ...tipo.titulo, fontSize: 26 },
  subtitulo: { ...tipo.nota, marginBottom: espacio.sm },
  vacio: { alignItems: 'center', gap: espacio.sm, paddingVertical: espacio.xxl },
  vacioTexto: { ...tipo.nota, textAlign: 'center' },
  tarjeta: { gap: espacio.xs },
  cabeceraEntrada: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  numeroEntrada: { color: color.narrativo, fontSize: 11, fontWeight: '700', letterSpacing: 0.4 },
  textoEntrada: { color: color.texto, fontSize: 14, lineHeight: 20 },
});
