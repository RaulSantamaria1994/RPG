import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import HomeScreen from './screens/HomeScreen';
import CrearSalaScreen from './screens/master/CrearSalaScreen';
import MasterSalaScreen from './screens/master/MasterSalaScreen';
import UnirseSalaScreen from './screens/player/UnirseSalaScreen';
import SeleccionPersonajeScreen from './screens/player/SeleccionPersonajeScreen';
import JuegoScreen from './screens/player/JuegoScreen';
import type { RootStackParamList } from './navigation/types';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <Stack.Navigator
          initialRouteName="Home"
          screenOptions={{
            headerStyle: { backgroundColor: '#1a1523' },
            headerTintColor: '#fff',
            headerShadowVisible: false,
            contentStyle: { backgroundColor: '#1a1523' },
          }}
        >
          <Stack.Screen name="Home" component={HomeScreen} options={{ headerShown: false }} />
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
