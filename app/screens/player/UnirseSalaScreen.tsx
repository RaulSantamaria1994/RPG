import { useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { api, ErrorApi } from '../../services/api';

type Props = NativeStackScreenProps<RootStackParamList, 'JugadorUnirseSala'>;

export default function UnirseSalaScreen({ navigation }: Props) {
  const [codigo, setCodigo] = useState('');
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function unirse() {
    const codigoLimpio = codigo.trim().toUpperCase();
    if (codigoLimpio.length !== 6) {
      setError('El código de sala tiene 6 caracteres.');
      return;
    }
    setCargando(true);
    setError(null);
    try {
      await api.obtenerSala(codigoLimpio);
      navigation.navigate('JugadorSeleccionPersonaje', { codigo: codigoLimpio });
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : 'No se pudo encontrar esa sala.');
    } finally {
      setCargando(false);
    }
  }

  return (
    <View style={styles.contenedor}>
      <Text style={styles.titulo}>Unirse a una sala</Text>
      <Text style={styles.etiqueta}>Código de sala (6 caracteres)</Text>
      <TextInput
        style={styles.input}
        value={codigo}
        onChangeText={setCodigo}
        autoCapitalize="characters"
        maxLength={6}
        placeholder="A1B2C3"
        placeholderTextColor="#7a6c8f"
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <TouchableOpacity style={styles.boton} onPress={unirse} disabled={cargando}>
        {cargando ? <ActivityIndicator color="#fff" /> : <Text style={styles.botonTexto}>Continuar</Text>}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: '#1a1523', padding: 24, justifyContent: 'center', gap: 8 },
  titulo: { fontSize: 26, fontWeight: '700', color: '#f3e9ff', marginBottom: 12 },
  etiqueta: { color: '#c9b8e0', fontSize: 13, marginBottom: 4 },
  input: {
    backgroundColor: '#2f2540',
    borderRadius: 8,
    padding: 14,
    color: '#fff',
    fontSize: 20,
    letterSpacing: 4,
    textAlign: 'center',
    borderWidth: 1,
    borderColor: '#453a5c',
  },
  error: { color: '#ff8a8a', marginTop: 12 },
  boton: {
    backgroundColor: '#6b3fa0',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 24,
  },
  botonTexto: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
