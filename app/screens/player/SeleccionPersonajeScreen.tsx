import { useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { Boton, Tarjeta } from '../../components';
import { api, ErrorApi } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import { useAcento } from '../../store/configStore';
import type { Atributo, HabilidadPasiva, PersonajePregenerado, Sala } from '../../types';
import { color, espacio, radio, tipo } from '../../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'JugadorSeleccionPersonaje'>;

const ATRIBUTOS: Atributo[] = ['fuerza', 'astucia', 'voluntad', 'agilidad'];
const ETIQUETA_ATRIBUTO: Record<Atributo, string> = {
  fuerza: 'Fuerza',
  astucia: 'Astucia',
  voluntad: 'Voluntad',
  agilidad: 'Agilidad',
};
const PUNTOS_TOTALES = 12;

export default function SeleccionPersonajeScreen({ route, navigation }: Props) {
  const { codigo } = route.params;
  const iniciarComoJugador = useSalaStore((s) => s.iniciarComoJugador);
  const acento = useAcento();

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

  const puntosUsados = useMemo(() => {
    let total = 0;
    for (const a of ATRIBUTOS) {
      total += puntos[a];
    }
    return total;
  }, [puntos]);
  const puntosListos = puntosUsados === PUNTOS_TOTALES;

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
      <Text style={styles.ayuda}>Elige con quién vas a enfrentarte a lo que viene.</Text>

      <Text style={styles.etiqueta}>Tu nombre</Text>
      <TextInput
        style={styles.input}
        value={jugadorNombre}
        onChangeText={setJugadorNombre}
        placeholder="Nombre de jugador"
        placeholderTextColor={color.textoTenue}
      />

      <View style={styles.tabs}>
        <TouchableOpacity
          style={[
            styles.tab,
            modo === 'pregenerado' && { backgroundColor: acento.acentoSuave, borderColor: acento.acentoFuerte },
          ]}
          onPress={() => setModo('pregenerado')}
        >
          <Text style={[styles.tabTexto, modo === 'pregenerado' && styles.tabTextoActivo]}>Pregenerado</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.tab,
            modo === 'personalizado' && { backgroundColor: acento.acentoSuave, borderColor: acento.acentoFuerte },
          ]}
          onPress={() => setModo('personalizado')}
        >
          <Text style={[styles.tabTexto, modo === 'personalizado' && styles.tabTextoActivo]}>Personalizado</Text>
        </TouchableOpacity>
      </View>

      {error && <Text style={styles.error}>{error}</Text>}

      {modo === 'pregenerado' ? (
        <View style={{ gap: espacio.sm }}>
          {pregenerados.map((p) => (
            <TouchableOpacity key={p.id} onPress={() => elegirPregenerado(p)} disabled={cargando} activeOpacity={0.85}>
              <Tarjeta>
                <Text style={styles.tarjetaTitulo}>{p.nombre}</Text>
                <Text style={styles.tarjetaTrasfondo}>{p.trasfondo}</Text>
                <View style={styles.filaChips}>
                  {ATRIBUTOS.map((a) => (
                    <View key={a} style={styles.chip}>
                      <Text style={styles.chipTexto}>
                        {ETIQUETA_ATRIBUTO[a].slice(0, 3).toUpperCase()} {p.atributos[a]}
                      </Text>
                    </View>
                  ))}
                </View>
              </Tarjeta>
            </TouchableOpacity>
          ))}
        </View>
      ) : (
        <Tarjeta>
          <Text style={styles.etiqueta}>Nombre del personaje</Text>
          <TextInput
            style={styles.input}
            value={nombrePersonalizado}
            onChangeText={setNombrePersonalizado}
            placeholder="Nombre"
            placeholderTextColor={color.textoTenue}
          />

          <View style={styles.filaPuntosTitulo}>
            <Text style={[styles.etiqueta, { marginTop: espacio.md, marginBottom: 0 }]}>Reparte tus puntos</Text>
            <Text style={[styles.puntosContador, puntosListos && styles.puntosContadorListo]}>
              {puntosUsados}/{PUNTOS_TOTALES}
            </Text>
          </View>
          <Text style={styles.ayudaCorta}>Entre 1 y 5 por atributo.</Text>
          {ATRIBUTOS.map((a) => (
            <View key={a} style={styles.filaAtributo}>
              <Text style={styles.atributoNombre}>{ETIQUETA_ATRIBUTO[a]}</Text>
              <TouchableOpacity
                onPress={() => ajustarPunto(a, -1)}
                style={[
                  styles.botonPunto,
                  { backgroundColor: acento.acento },
                  puntos[a] <= 1 && styles.botonPuntoDeshabilitado,
                ]}
                disabled={puntos[a] <= 1}
              >
                <Text style={styles.botonPuntoTexto}>−</Text>
              </TouchableOpacity>
              <Text style={styles.atributoValor}>{puntos[a]}</Text>
              <TouchableOpacity
                onPress={() => ajustarPunto(a, 1)}
                style={[
                  styles.botonPunto,
                  { backgroundColor: acento.acento },
                  (puntos[a] >= 5 || puntosUsados >= PUNTOS_TOTALES) && styles.botonPuntoDeshabilitado,
                ]}
                disabled={puntos[a] >= 5 || puntosUsados >= PUNTOS_TOTALES}
              >
                <Text style={styles.botonPuntoTexto}>+</Text>
              </TouchableOpacity>
            </View>
          ))}

          <Text style={[styles.etiqueta, { marginTop: espacio.md }]}>Habilidad pasiva</Text>
          <View style={{ gap: espacio.xs }}>
            {habilidades.map((h) => (
              <TouchableOpacity key={h.id} onPress={() => setHabilidadElegida(h.id)} activeOpacity={0.85}>
                <Tarjeta seleccionada={habilidadElegida === h.id} style={{ paddingVertical: espacio.sm }}>
                  <Text style={styles.tarjetaTitulo}>{h.nombre}</Text>
                  <Text style={styles.tarjetaTrasfondo}>{h.descripcion}</Text>
                </Tarjeta>
              </TouchableOpacity>
            ))}
          </View>

          <Boton
            texto="Crear personaje"
            onPress={crearPersonalizado}
            cargando={cargando}
            style={{ marginTop: espacio.lg }}
          />
        </Tarjeta>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: espacio.xl, backgroundColor: color.fondo, flexGrow: 1, gap: espacio.sm },
  titulo: { ...tipo.titulo, fontSize: 24, marginBottom: 2 },
  ayuda: { ...tipo.nota, marginBottom: espacio.sm },
  ayudaCorta: { color: color.textoTenue, fontSize: 12, marginBottom: espacio.xs },
  etiqueta: { color: color.textoSecundario, fontSize: 13, marginBottom: 4 },
  input: {
    backgroundColor: color.superficieAlt,
    borderRadius: radio.md,
    padding: 12,
    color: color.texto,
    borderWidth: 1,
    borderColor: color.bordeSutil,
  },
  tabs: { flexDirection: 'row', gap: espacio.sm, marginVertical: espacio.lg },
  tab: {
    flex: 1,
    padding: 10,
    borderRadius: radio.md,
    backgroundColor: color.superficieAlt,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: color.bordeSutil,
  },
  tabTexto: { color: color.textoSecundario, fontWeight: '600' },
  tabTextoActivo: { color: color.texto },
  tarjetaTitulo: { color: color.texto, fontWeight: '700', fontSize: 16 },
  tarjetaTrasfondo: { color: color.textoSecundario, fontSize: 13, lineHeight: 18 },
  filaChips: { flexDirection: 'row', gap: 6, marginTop: 4, flexWrap: 'wrap' },
  chip: {
    backgroundColor: color.fondoElevado,
    borderRadius: radio.sm,
    paddingHorizontal: 7,
    paddingVertical: 3,
  },
  chipTexto: { color: color.textoSecundario, fontSize: 11, fontWeight: '700' },
  filaPuntosTitulo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  puntosContador: { color: color.textoSecundario, fontWeight: '700', fontSize: 13 },
  puntosContadorListo: { color: color.exito },
  filaAtributo: { flexDirection: 'row', alignItems: 'center', gap: espacio.md, marginTop: 4 },
  atributoNombre: { color: color.texto, width: 90 },
  botonPunto: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: color.acento,
    alignItems: 'center',
    justifyContent: 'center',
  },
  botonPuntoDeshabilitado: { backgroundColor: color.superficieAlt, opacity: 0.6 },
  botonPuntoTexto: { color: '#fff', fontSize: 18, fontWeight: '700' },
  atributoValor: { color: color.texto, fontSize: 16, width: 24, textAlign: 'center' },
  error: { color: color.peligro, marginBottom: espacio.sm },
});
