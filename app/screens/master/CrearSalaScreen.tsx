import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { api, ErrorApi } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { HistoriaResumen } from '../../types';

type Props = NativeStackScreenProps<RootStackParamList, 'MasterCrearSala'>;

export default function CrearSalaScreen({ navigation }: Props) {
  const iniciarComoMaster = useSalaStore((s) => s.iniciarComoMaster);

  const [historias, setHistorias] = useState<HistoriaResumen[]>([]);
  const [historiaId, setHistoriaId] = useState<string | null>(null);
  const [nombreMaster, setNombreMaster] = useState('');
  const [maxJugadores, setMaxJugadores] = useState('6');
  const [muertePermanente, setMuertePermanente] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listarHistorias()
      .then((lista) => {
        const validas = lista.filter((h) => h.validada);
        setHistorias(validas);
        if (validas.length > 0) setHistoriaId(validas[0].historia_id);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function crear() {
    if (!historiaId || !nombreMaster.trim()) {
      setError('Completa tu nombre y elige una historia.');
      return;
    }
    setCargando(true);
    setError(null);
    try {
      const { sala, master_token } = await api.crearSala({
        master_nombre: nombreMaster.trim(),
        historia_id: historiaId,
        max_jugadores: Number(maxJugadores) || 6,
        muerte_permanente: muertePermanente,
      });
      iniciarComoMaster(sala, master_token);
      navigation.replace('MasterSala');
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : 'No se pudo crear la sala.');
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.contenedor}>
      <Text style={styles.titulo}>Crear sala</Text>

      <Text style={styles.etiqueta}>Tu nombre (máster)</Text>
      <TextInput
        style={styles.input}
        value={nombreMaster}
        onChangeText={setNombreMaster}
        placeholder="Nombre del máster"
        placeholderTextColor="#7a6c8f"
      />

      <Text style={styles.etiqueta}>Historia</Text>
      {historias.length === 0 ? (
        <Text style={styles.aviso}>No hay historias validadas disponibles todavía.</Text>
      ) : (
        historias.map((h) => (
          <TouchableOpacity
            key={h.historia_id}
            style={[
              styles.opcionHistoria,
              historiaId === h.historia_id && styles.opcionHistoriaSeleccionada,
            ]}
            onPress={() => setHistoriaId(h.historia_id)}
          >
            <Text style={styles.opcionHistoriaTexto}>{h.titulo}</Text>
            <Text style={styles.opcionHistoriaVersion}>v{h.version}</Text>
          </TouchableOpacity>
        ))
      )}

      <Text style={styles.etiqueta}>Máximo de jugadores (2-6)</Text>
      <TextInput
        style={styles.input}
        value={maxJugadores}
        onChangeText={setMaxJugadores}
        keyboardType="number-pad"
      />

      <View style={styles.filaSwitch}>
        <Text style={styles.etiqueta}>Muerte permanente</Text>
        <Switch value={muertePermanente} onValueChange={setMuertePermanente} />
      </View>

      {error && <Text style={styles.error}>{error}</Text>}

      <TouchableOpacity style={styles.boton} onPress={crear} disabled={cargando}>
        {cargando ? <ActivityIndicator color="#fff" /> : <Text style={styles.botonTexto}>Crear sala</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: 24, backgroundColor: '#1a1523', flexGrow: 1, gap: 8 },
  titulo: { fontSize: 26, fontWeight: '700', color: '#f3e9ff', marginBottom: 12 },
  etiqueta: { color: '#c9b8e0', fontSize: 13, marginTop: 12, marginBottom: 4 },
  input: {
    backgroundColor: '#2f2540',
    borderRadius: 8,
    padding: 12,
    color: '#fff',
    borderWidth: 1,
    borderColor: '#453a5c',
  },
  opcionHistoria: {
    backgroundColor: '#2f2540',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#453a5c',
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  opcionHistoriaSeleccionada: { borderColor: '#a97fe0', backgroundColor: '#3d2f57' },
  opcionHistoriaTexto: { color: '#fff', fontWeight: '600' },
  opcionHistoriaVersion: { color: '#a390bd' },
  filaSwitch: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
  aviso: { color: '#e0a97f' },
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
