import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../navigation/types';
import { useSalaStore } from '../store/salaStore';
import { color, espacio, radio, tipo } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export default function HomeScreen({ navigation }: Props) {
  const mensajeSesion = useSalaStore((s) => s.mensajeSesion);
  const limpiarMensajeSesion = useSalaStore((s) => s.limpiarMensajeSesion);

  return (
    <View style={styles.contenedor}>
      <View style={styles.encabezado}>
        <Text style={styles.titulo}>RPG Narrativo</Text>
        <Text style={styles.subtitulo}>Historias de terror cósmico para jugar entre amigos</Text>
      </View>

      {mensajeSesion && (
        <TouchableOpacity style={styles.avisoSesion} onPress={limpiarMensajeSesion} activeOpacity={0.8}>
          <Text style={styles.avisoSesionTexto}>{mensajeSesion}</Text>
          <Text style={styles.avisoSesionCerrar}>Toca para cerrar</Text>
        </TouchableOpacity>
      )}

      <View style={styles.opciones}>
        <TouchableOpacity
          style={[styles.opcion, styles.opcionPrimaria]}
          onPress={() => navigation.navigate('MasterCrearSala')}
          activeOpacity={0.85}
        >
          <Ionicons name="book-outline" size={28} color={color.texto} />
          <View style={{ flex: 1 }}>
            <Text style={styles.opcionTitulo}>Soy el Máster</Text>
            <Text style={styles.opcionDescripcion}>Crea una sala y narra la historia al grupo</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.opcion}
          onPress={() => navigation.navigate('JugadorUnirseSala')}
          activeOpacity={0.85}
        >
          <Ionicons name="flame-outline" size={28} color={color.texto} />
          <View style={{ flex: 1 }}>
            <Text style={styles.opcionTitulo}>Soy Jugador</Text>
            <Text style={styles.opcionDescripcion}>Únete a una sala con el código del máster</Text>
          </View>
        </TouchableOpacity>
      </View>

      <TouchableOpacity
        style={styles.enlaceAyuda}
        onPress={() => navigation.navigate('Ayuda')}
        activeOpacity={0.7}
      >
        <Ionicons name="help-circle-outline" size={16} color={color.textoSecundario} />
        <Text style={styles.enlaceAyudaTexto}>¿Cómo se juega?</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    flex: 1,
    backgroundColor: color.fondo,
    alignItems: 'center',
    justifyContent: 'center',
    padding: espacio.xl,
    gap: espacio.xl,
  },
  encabezado: { alignItems: 'center', gap: espacio.sm, maxWidth: 360 },
  titulo: { ...tipo.titulo, fontSize: 34, textAlign: 'center' },
  subtitulo: { ...tipo.nota, textAlign: 'center' },
  avisoSesion: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: color.avisoSuave,
    borderWidth: 1,
    borderColor: color.aviso,
    borderRadius: radio.lg,
    padding: espacio.md,
    gap: 2,
  },
  avisoSesionTexto: { color: '#f0e6c9', fontSize: 13, textAlign: 'center' },
  avisoSesionCerrar: { color: '#9b8a5f', fontSize: 11, textAlign: 'center' },
  opciones: { width: '100%', maxWidth: 360, gap: espacio.md },
  opcion: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.md,
    backgroundColor: color.superficieAlt,
    borderRadius: radio.xl,
    borderWidth: 1,
    borderColor: color.borde,
    paddingVertical: espacio.lg,
    paddingHorizontal: espacio.lg,
  },
  opcionPrimaria: { backgroundColor: color.acentoSuave, borderColor: color.acento },
  opcionTitulo: { color: color.texto, fontSize: 17, fontWeight: '700' },
  opcionDescripcion: { color: color.textoSecundario, fontSize: 13, marginTop: 2 },
  enlaceAyuda: { flexDirection: 'row', alignItems: 'center', gap: 6, padding: espacio.sm },
  enlaceAyudaTexto: { color: color.textoSecundario, fontSize: 13 },
});
