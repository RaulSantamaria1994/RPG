import { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { api, ErrorApi } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { Atributo, HabilidadPasiva, PersonajePregenerado, Sala } from '../../types';

type Props = NativeStackScreenProps<RootStackParamList, 'JugadorSeleccionPersonaje'>;

const ATRIBUTOS: Atributo[] = ['fuerza', 'astucia', 'voluntad', 'agilidad'];
const PUNTOS_TOTALES = 12;

export default function SeleccionPersonajeScreen({ route, navigation }: Props) {
  const { codigo } = route.params;
  const iniciarComoJugador = useSalaStore((s) => s.iniciarComoJugador);

  const [sala, setSala] = useState<Sala | null>(null);
  const [pregenerados, setPregenerados] = useState<PersonajePregenerado[]>([]);
  const [habilidades, setHabilidades] = useState<HabilidadPasiva[]>([]);
  const [modo, setModo] = useState<'pregenerado' | 'personalizado'>('pregenerado');
  const [jugadorNombre, setJugadorNombre] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const [nombrePersonalizado, setNombrePersonalizado] = useState('');
  const [puntos, setPuntos] = useState<Record<Atributo, number>>({
    fuerza: 3,
    astucia: 3,
    voluntad: 3,
    agilidad: 3,
  });
  const [habilidadElegida, setHabilidadElegida] = useState<string | null>(null);

  const puntosUsados = useMemo(
    () => ATRIBUTOS.reduce((acc, a) => acc + puntos[a], 0),
    [puntos]
  );

  useEffect(() => {
    Promise.all([
      api.obtenerSala(codigo),
      api.listarPregenerados(codigo),
      api.habilidadesPersonalizado(codigo),
    ])
      .then(([s, pre, hab]) => {
        setSala(s);
        setPregenerados(pre);
        setHabilidades(hab);
        if (hab.length > 0) setHabilidadElegida(hab[0].id);
      })
      .catch((e) => setError(e.message));
  }, [codigo]);

  function ajustarPunto(atributo: Atributo, delta: number) {
    setPuntos((prev) => {
      const nuevo = prev[atributo] + delta;
      if (nuevo < 1 || nuevo > 5) return prev;
      if (delta > 0 && puntosUsados >= PUNTOS_TOTALES) return prev;
      return { ...prev, [atributo]: nuevo };
    });
  }

  async function elegirPregenerado(p: PersonajePregenerado) {
    if (!jugadorNombre.trim() || !sala) {
      setError('Escribe tu nombre de jugador primero.');
      return;
    }
    setCargando(true);
    setError(null);
    try {
      const { personaje, token } = await api.crearPersonajePregenerado(codigo, {
        jugador_nombre: jugadorNombre.trim(),
        personaje_pregenerado_id: p.id,
      });
      iniciarComoJugador(sala, token, personaje);
      navigation.replace('JugadorJuego');
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : 'No se pudo crear el personaje.');
    } finally {
      setCargando(false);
    }
  }

  async function crearPersonalizado() {
    if (!jugadorNombre.trim() || !nombrePersonalizado.trim() || !habilidadElegida || !sala) {
      setError('Completa tu nombre, el del personaje y la habilidad pasiva.');
      return;
    }
    if (puntosUsados !== PUNTOS_TOTALES) {
      setError(`Debes repartir exactamente ${PUNTOS_TOTALES} puntos (llevas ${puntosUsados}).`);
      return;
    }
    setCargando(true);
    setError(null);
    try {
      const { personaje, token } = await api.crearPersonajePersonalizado(codigo, {
        jugador_nombre: jugadorNombre.trim(),
        nombre: nombrePersonalizado.trim(),
        atributos: puntos,
        habilidad_pasiva: habilidadElegida,
      });
      iniciarComoJugador(sala, token, personaje);
      navigation.replace('JugadorJuego');
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : 'No se pudo crear el personaje.');
    } finally {
      setCargando(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.contenedor}>
      <Text style={styles.titulo}>{sala?.nombre ?? `Sala ${codigo}`}</Text>

      <Text style={styles.etiqueta}>Tu nombre</Text>
      <TextInput
        style={styles.input}
        value={jugadorNombre}
        onChangeText={setJugadorNombre}
        placeholder="Nombre de jugador"
        placeholderTextColor="#7a6c8f"
      />

      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, modo === 'pregenerado' && styles.tabActivo]}
          onPress={() => setModo('pregenerado')}
        >
          <Text style={styles.tabTexto}>Pregenerado</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, modo === 'personalizado' && styles.tabActivo]}
          onPress={() => setModo('personalizado')}
        >
          <Text style={styles.tabTexto}>Personalizado</Text>
        </TouchableOpacity>
      </View>

      {error && <Text style={styles.error}>{error}</Text>}

      {modo === 'pregenerado' ? (
        pregenerados.map((p) => (
          <TouchableOpacity
            key={p.id}
            style={styles.tarjeta}
            onPress={() => elegirPregenerado(p)}
            disabled={cargando}
          >
            <Text style={styles.tarjetaTitulo}>{p.nombre}</Text>
            <Text style={styles.tarjetaTrasfondo}>{p.trasfondo}</Text>
            <Text style={styles.tarjetaAtributos}>
              F {p.atributos.fuerza} · A {p.atributos.astucia} · V {p.atributos.voluntad} · Ag{' '}
              {p.atributos.agilidad}
            </Text>
          </TouchableOpacity>
        ))
      ) : (
        <View style={styles.tarjeta}>
          <Text style={styles.etiqueta}>Nombre del personaje</Text>
          <TextInput
            style={styles.input}
            value={nombrePersonalizado}
            onChangeText={setNombrePersonalizado}
            placeholder="Nombre"
            placeholderTextColor="#7a6c8f"
          />

          <Text style={[styles.etiqueta, { marginTop: 12 }]}>
            Puntos: {puntosUsados}/{PUNTOS_TOTALES} (1-5 por atributo)
          </Text>
          {ATRIBUTOS.map((a) => (
            <View key={a} style={styles.filaAtributo}>
              <Text style={styles.atributoNombre}>{a}</Text>
              <TouchableOpacity onPress={() => ajustarPunto(a, -1)} style={styles.botonPunto}>
                <Text style={styles.botonPuntoTexto}>-</Text>
              </TouchableOpacity>
              <Text style={styles.atributoValor}>{puntos[a]}</Text>
              <TouchableOpacity onPress={() => ajustarPunto(a, 1)} style={styles.botonPunto}>
                <Text style={styles.botonPuntoTexto}>+</Text>
              </TouchableOpacity>
            </View>
          ))}

          <Text style={[styles.etiqueta, { marginTop: 12 }]}>Habilidad pasiva</Text>
          {habilidades.map((h) => (
            <TouchableOpacity
              key={h.id}
              style={[
                styles.opcionHabilidad,
                habilidadElegida === h.id && styles.opcionHabilidadSeleccionada,
              ]}
              onPress={() => setHabilidadElegida(h.id)}
            >
              <Text style={styles.tarjetaTitulo}>{h.nombre}</Text>
              <Text style={styles.tarjetaTrasfondo}>{h.descripcion}</Text>
            </TouchableOpacity>
          ))}

          <TouchableOpacity style={styles.boton} onPress={crearPersonalizado} disabled={cargando}>
            {cargando ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.botonTexto}>Crear personaje</Text>
            )}
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: 24, backgroundColor: '#1a1523', flexGrow: 1, gap: 8 },
  titulo: { fontSize: 24, fontWeight: '700', color: '#f3e9ff', marginBottom: 8 },
  etiqueta: { color: '#c9b8e0', fontSize: 13, marginBottom: 4 },
  input: {
    backgroundColor: '#2f2540',
    borderRadius: 8,
    padding: 12,
    color: '#fff',
    borderWidth: 1,
    borderColor: '#453a5c',
  },
  tabs: { flexDirection: 'row', gap: 8, marginVertical: 16 },
  tab: {
    flex: 1,
    padding: 10,
    borderRadius: 8,
    backgroundColor: '#2f2540',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#453a5c',
  },
  tabActivo: { backgroundColor: '#3d2f57', borderColor: '#a97fe0' },
  tabTexto: { color: '#fff', fontWeight: '600' },
  tarjeta: {
    backgroundColor: '#241b33',
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    gap: 6,
  },
  tarjetaTitulo: { color: '#fff', fontWeight: '700', fontSize: 16 },
  tarjetaTrasfondo: { color: '#c9b8e0', fontSize: 13 },
  tarjetaAtributos: { color: '#a390bd', fontSize: 12, marginTop: 4 },
  filaAtributo: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 4 },
  atributoNombre: { color: '#fff', width: 90, textTransform: 'capitalize' },
  botonPunto: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#6b3fa0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  botonPuntoTexto: { color: '#fff', fontSize: 18, fontWeight: '700' },
  atributoValor: { color: '#fff', fontSize: 16, width: 24, textAlign: 'center' },
  opcionHabilidad: {
    backgroundColor: '#2f2540',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#453a5c',
    marginBottom: 6,
  },
  opcionHabilidadSeleccionada: { borderColor: '#a97fe0', backgroundColor: '#3d2f57' },
  error: { color: '#ff8a8a', marginBottom: 8 },
  boton: {
    backgroundColor: '#6b3fa0',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 16,
  },
  botonTexto: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
