import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { Boton } from '../../components';
import { api, ErrorApi } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { HistoriaResumen } from '../../types';
import { color, espacio, radio, tipo } from '../../theme';

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
      <Text style={styles.ayuda}>
        Al crearla recibirás un código de 6 caracteres para compartir con tu grupo.
      </Text>

      <Text style={styles.etiqueta}>Tu nombre (máster)</Text>
      <TextInput
        style={styles.input}
        value={nombreMaster}
        onChangeText={setNombreMaster}
        placeholder="Nombre del máster"
        placeholderTextColor={color.textoTenue}
      />

      <Text style={styles.etiqueta}>Historia</Text>
      {historias.length === 0 ? (
        <Text style={styles.aviso}>No hay historias validadas disponibles todavía.</Text>
      ) : (
        historias.map((h) => (
          <TouchableOpacity
            key={h.historia_id}
            style={[styles.opcionHistoria, historiaId === h.historia_id && styles.opcionHistoriaSeleccionada]}
            onPress={() => setHistoriaId(h.historia_id)}
            activeOpacity={0.85}
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
        <View style={{ flex: 1 }}>
          <Text style={styles.etiqueta}>Muerte permanente</Text>
          <Text style={styles.ayudaCorta}>Si un personaje llega a 0 de vida, puede morir para siempre.</Text>
        </View>
        <Switch
          value={muertePermanente}
          onValueChange={setMuertePermanente}
          trackColor={{ true: color.acento, false: color.bordeSutil }}
          thumbColor="#fff"
        />
      </View>

      {error && <Text style={styles.error}>{error}</Text>}

      <Boton texto="Crear sala" onPress={crear} cargando={cargando} style={{ marginTop: espacio.xl }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: espacio.xl, backgroundColor: color.fondo, flexGrow: 1, gap: espacio.sm },
  titulo: { ...tipo.titulo, fontSize: 26, marginBottom: 2 },
  ayuda: { ...tipo.nota, marginBottom: espacio.sm },
  ayudaCorta: { color: color.textoTenue, fontSize: 12, marginTop: 2 },
  etiqueta: { color: color.textoSecundario, fontSize: 13, marginTop: espacio.md, marginBottom: 4 },
  input: {
    backgroundColor: color.superficieAlt,
    borderRadius: radio.md,
    padding: 12,
    color: color.texto,
    borderWidth: 1,
    borderColor: color.bordeSutil,
  },
  opcionHistoria: {
    backgroundColor: color.superficieAlt,
    borderRadius: radio.md,
    padding: 12,
    borderWidth: 1,
    borderColor: color.bordeSutil,
    marginBottom: espacio.sm,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  opcionHistoriaSeleccionada: { borderColor: color.acentoFuerte, backgroundColor: color.acentoSuave },
  opcionHistoriaTexto: { color: color.texto, fontWeight: '600' },
  opcionHistoriaVersion: { color: color.textoTenue },
  filaSwitch: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: espacio.md, gap: espacio.md },
  aviso: { color: color.aviso },
  error: { color: color.peligro, marginTop: espacio.md },
});
