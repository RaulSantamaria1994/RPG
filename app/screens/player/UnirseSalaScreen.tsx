import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { Boton } from '../../components';
import { api, ErrorApi } from '../../services/api';
import { API_BASE_URL } from '../../services/config';
import { color, espacio, radio, tipo } from '../../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'JugadorUnirseSala'>;

export default function UnirseSalaScreen({ navigation }: Props) {
  const [codigo, setCodigo] = useState('');
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function unirse() {
    const codigoLimpio = codigo.trim().toUpperCase();
    if (codigoLimpio.length !== 6) {
      setError('El código de sala tiene 6 caracteres. Pídeselo al máster.');
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
      <Text style={styles.ayuda}>Pide al máster el código de 6 caracteres de su sala.</Text>

      <Text style={styles.etiqueta}>Código de sala</Text>
      <TextInput
        style={styles.input}
        value={codigo}
        onChangeText={(v) => {
          setCodigo(v);
          if (error) setError(null);
        }}
        autoCapitalize="characters"
        autoCorrect={false}
        maxLength={6}
        placeholder="A1B2C3"
        placeholderTextColor={color.textoTenue}
        onSubmitEditing={unirse}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Boton texto="Continuar" onPress={unirse} cargando={cargando} style={{ marginTop: espacio.lg }} />

      <Text style={styles.servidorTexto}>Servidor: {API_BASE_URL}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: color.fondo, padding: espacio.xl, justifyContent: 'center', gap: espacio.sm },
  titulo: { ...tipo.titulo, fontSize: 26, marginBottom: 2 },
  ayuda: { ...tipo.nota, marginBottom: espacio.md },
  etiqueta: { color: color.textoSecundario, fontSize: 13, marginBottom: 4 },
  input: {
    backgroundColor: color.superficieAlt,
    borderRadius: radio.md,
    padding: 14,
    color: color.texto,
    fontSize: 22,
    letterSpacing: 5,
    textAlign: 'center',
    borderWidth: 1,
    borderColor: color.bordeSutil,
  },
  error: { color: color.peligro, marginTop: espacio.sm },
  servidorTexto: { color: color.textoTenue, fontSize: 11, textAlign: 'center', marginTop: espacio.xxl },
});
