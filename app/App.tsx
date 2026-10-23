import { useEffect, useRef, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { Animated, StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import {
  Spectral_500Medium,
  Spectral_500Medium_Italic,
  Spectral_600SemiBold,
} from '@expo-google-fonts/spectral';
import {
  PublicSans_400Regular,
  PublicSans_500Medium,
  PublicSans_600SemiBold,
  PublicSans_700Bold,
} from '@expo-google-fonts/public-sans';
import { SpecialElite_400Regular } from '@expo-google-fonts/special-elite';

import { Sello } from './components';
import HomeScreen from './screens/HomeScreen';
import AyudaScreen from './screens/AyudaScreen';
import DiarioScreen from './screens/DiarioScreen';
import OpcionesScreen from './screens/OpcionesScreen';
import CrearSalaScreen from './screens/master/CrearSalaScreen';
import MasterSalaScreen from './screens/master/MasterSalaScreen';
import UnirseSalaScreen from './screens/player/UnirseSalaScreen';
import SeleccionPersonajeScreen from './screens/player/SeleccionPersonajeScreen';
import JuegoScreen from './screens/player/JuegoScreen';
import EquipoScreen from './screens/player/EquipoScreen';
import type { RootStackParamList } from './navigation/types';
import { useSalaStore } from './store/salaStore';
import { color } from './theme';

const Stack = createNativeStackNavigator<RootStackParamList>();

function usePersistenciaLista(): boolean {
  const [lista, setLista] = useState(() => useSalaStore.persist.hasHydrated());

  useEffect(() => {
    if (useSalaStore.persist.hasHydrated()) {
      setLista(true);
      return;
    }
    return useSalaStore.persist.onFinishHydration(() => setLista(true));
  }, []);

  return lista;
}

function rutaInicialDesdeSesion(): keyof RootStackParamList {
  const { rol, sala, token, personaje } = useSalaStore.getState();
  if (rol === 'master' && sala && token) return 'MasterSala';
  if (rol === 'jugador' && sala && token && personaje) return 'JugadorJuego';
  return 'Home';
}

/** Sello que respira despacio, usado como indicador de carga en vez del
 * spinner por defecto de la librería — el mismo símbolo de toda la
 * identidad, no un componente sin vestir. */
function SelloDeCarga() {
  const pulso = useRef(new Animated.Value(0.96)).current;

  useEffect(() => {
    const animacion = Animated.loop(
      Animated.sequence([
        Animated.timing(pulso, { toValue: 1.04, duration: 900, useNativeDriver: true }),
        Animated.timing(pulso, { toValue: 0.96, duration: 900, useNativeDriver: true }),
      ])
    );
    animacion.start();
    return () => animacion.stop();
  }, [pulso]);

  return (
    <Animated.View style={{ transform: [{ scale: pulso }] }}>
      <Sello tamano={64} />
    </Animated.View>
  );
}

export default function App() {
  const persistenciaLista = usePersistenciaLista();
  const [fuentesListas] = useFonts({
    'Spectral-Medium': Spectral_500Medium,
    'Spectral-MediumItalic': Spectral_500Medium_Italic,
    'Spectral-SemiBold': Spectral_600SemiBold,
    'PublicSans-Regular': PublicSans_400Regular,
    'PublicSans-Medium': PublicSans_500Medium,
    'PublicSans-SemiBold': PublicSans_600SemiBold,
    'PublicSans-Bold': PublicSans_700Bold,
    'SpecialElite-Regular': SpecialElite_400Regular,
  });

  if (!persistenciaLista || !fuentesListas) {
    return (
      <View style={styles.cargando}>
        <SelloDeCarga />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <Stack.Navigator
          initialRouteName={rutaInicialDesdeSesion()}
          screenOptions={{
            headerStyle: { backgroundColor: color.fondo },
            headerTintColor: color.texto,
            headerShadowVisible: false,
            contentStyle: { backgroundColor: color.fondo },
          }}
        >
          <Stack.Screen name="Home" component={HomeScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Ayuda" component={AyudaScreen} options={{ title: 'Cómo se juega' }} />
          <Stack.Screen name="Diario" component={DiarioScreen} options={{ title: 'Diario de pistas' }} />
          <Stack.Screen name="Equipo" component={EquipoScreen} options={{ title: 'Equipo' }} />
          <Stack.Screen name="Opciones" component={OpcionesScreen} options={{ title: 'Opciones' }} />
          <Stack.Screen
            name="MasterCrearSala"
            component={CrearSalaScreen}
            options={{ title: 'Crear sala' }}
          />
          <Stack.Screen
            name="MasterSala"
            component={MasterSalaScreen}
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="JugadorUnirseSala"
            component={UnirseSalaScreen}
            options={{ title: 'Unirse a sala' }}
          />
          <Stack.Screen
            name="JugadorSeleccionPersonaje"
            component={SeleccionPersonajeScreen}
            options={{ title: 'Tu personaje' }}
          />
          <Stack.Screen
            name="JugadorJuego"
            component={JuegoScreen}
            options={{ headerShown: false }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  cargando: { flex: 1, backgroundColor: color.fondo, alignItems: 'center', justifyContent: 'center' },
});
