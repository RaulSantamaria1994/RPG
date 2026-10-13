import { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import HomeScreen from './screens/HomeScreen';
import AyudaScreen from './screens/AyudaScreen';
import CrearSalaScreen from './screens/master/CrearSalaScreen';
import MasterSalaScreen from './screens/master/MasterSalaScreen';
import UnirseSalaScreen from './screens/player/UnirseSalaScreen';
import SeleccionPersonajeScreen from './screens/player/SeleccionPersonajeScreen';
import JuegoScreen from './screens/player/JuegoScreen';
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

export default function App() {
  const persistenciaLista = usePersistenciaLista();

  if (!persistenciaLista) {
    return (
      <View style={styles.cargando}>
        <ActivityIndicator color="#fff" size="large" />
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
