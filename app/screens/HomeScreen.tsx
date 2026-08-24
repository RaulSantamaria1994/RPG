import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../navigation/types';
import { useSalaStore } from '../store/salaStore';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export default function HomeScreen({ navigation }: Props) {
  const mensajeSesion = useSalaStore((s) => s.mensajeSesion);
  const limpiarMensajeSesion = useSalaStore((s) => s.limpiarMensajeSesion);

  return (
    <View style={styles.contenedor}>
      <Text style={styles.titulo}>RPG Narrativo</Text>
      <Text style={styles.subtitulo}>¿Cómo quieres jugar?</Text>

      {mensajeSesion && (
        <TouchableOpacity style={styles.avisoSesion} onPress={limpiarMensajeSesion}>
          <Text style={styles.avisoSesionTexto}>{mensajeSesion}</Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity
        style={styles.boton}
        onPress={() => navigation.navigate('MasterCrearSala')}
      >
        <Text style={styles.botonTexto}>Soy el Máster</Text>
        <Text style={styles.botonDescripcion}>Crear una sala y narrar la historia</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.boton, styles.botonSecundario]}
        onPress={() => navigation.navigate('JugadorUnirseSala')}
      >
        <Text style={styles.botonTexto}>Soy Jugador</Text>
        <Text style={styles.botonDescripcion}>Unirme a una sala con un código</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    flex: 1,
    backgroundColor: '#1a1523',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    gap: 16,
  },
  titulo: { fontSize: 32, fontWeight: '700', color: '#f3e9ff', marginBottom: 4 },
  subtitulo: { fontSize: 16, color: '#c9b8e0', marginBottom: 24 },
  avisoSesion: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#2b2a1f',
    borderWidth: 1,
    borderColor: '#d0b86f',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  avisoSesionTexto: { color: '#f0e6c9', fontSize: 13, textAlign: 'center' },
  boton: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#6b3fa0',
    borderRadius: 12,
    paddingVertical: 18,
    paddingHorizontal: 20,
  },
  botonSecundario: { backgroundColor: '#2f2540', borderWidth: 1, borderColor: '#6b3fa0' },
  botonTexto: { color: '#fff', fontSize: 18, fontWeight: '600' },
  botonDescripcion: { color: '#d8cbe8', fontSize: 13, marginTop: 4 },
});
