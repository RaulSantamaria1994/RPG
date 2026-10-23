import { Image, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../navigation/types';
import { Sello, TexturaGrano } from '../components';
import { useSalaStore } from '../store/salaStore';
import { useAcento } from '../store/configStore';
import { color, espacio, fuente, radio, tipo } from '../theme';

const ALTO_ESCENA = 260;

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export default function HomeScreen({ navigation }: Props) {
  const insets = useSafeAreaInsets();
  const mensajeSesion = useSalaStore((s) => s.mensajeSesion);
  const limpiarMensajeSesion = useSalaStore((s) => s.limpiarMensajeSesion);
  const acento = useAcento();

  return (
    <View style={styles.contenedor}>
      <View style={styles.escena}>
        <Image
          source={require('../assets/fondo-archivo.jpg')}
          style={styles.escenaImagen}
          resizeMode="cover"
        />
        <View style={styles.escenaVelo} />
        <LinearGradient
          colors={['transparent', color.fondo]}
          style={styles.escenaDegradado}
        />
      </View>

      <TouchableOpacity
        style={[styles.botonOpciones, { top: espacio.xl + insets.top }]}
        onPress={() => navigation.navigate('Opciones')}
        hitSlop={8}
        testID="boton-opciones"
      >
        <Ionicons name="settings-outline" size={22} color={color.textoSecundario} />
      </TouchableOpacity>

      <View style={styles.contenido}>
        <View style={styles.sello}>
          <Sello tamano={76} />
        </View>

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
            style={[styles.opcion, styles.opcionPrimaria, { backgroundColor: acento.acentoSuave, borderColor: acento.acento }]}
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

      <Text style={styles.pie}>ARCHIVO DE EXPEDIENTES IMPOSIBLES</Text>
      <TexturaGrano />
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: color.fondo },
  escena: { width: '100%', height: ALTO_ESCENA, position: 'absolute', top: 0, left: 0 },
  escenaImagen: { width: '100%', height: '100%' },
  escenaVelo: { ...StyleSheet.absoluteFillObject, backgroundColor: color.fondo, opacity: 0.22 },
  escenaDegradado: { position: 'absolute', left: 0, right: 0, bottom: 0, height: 110 },
  botonOpciones: { position: 'absolute', right: espacio.xl, zIndex: 2 },
  contenido: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: espacio.xl,
    gap: espacio.xl,
    marginTop: ALTO_ESCENA - 90,
  },
  sello: { marginBottom: -espacio.sm },
  encabezado: { alignItems: 'center', gap: espacio.sm, maxWidth: 360 },
  titulo: { ...tipo.titulo, fontSize: 32, textAlign: 'center', letterSpacing: 0.5 },
  subtitulo: { ...tipo.nota, textAlign: 'center' },
  pie: {
    fontFamily: fuente.sello,
    fontSize: 10,
    letterSpacing: 2,
    color: color.textoTenue,
    textAlign: 'center',
    paddingBottom: espacio.lg,
  },
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
