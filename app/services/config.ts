import { Platform } from 'react-native';

// En desarrollo local, Android emulator no puede usar "localhost" (se refiere
// al propio emulador), así que se mapea a la IP especial del host.
const HOST_DESARROLLO = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';

// EXPO_PUBLIC_API_URL / EXPO_PUBLIC_API_WS_URL se inlinean en tiempo de build
// (prefijo EXPO_PUBLIC_ requerido por Expo). Sin ellas, se usa el backend
// local de desarrollo — imprescindible para un APK instalado en un móvil
// real, que no puede alcanzar "localhost" del ordenador de desarrollo.
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || `http://${HOST_DESARROLLO}:8000`;
export const WS_BASE_URL = process.env.EXPO_PUBLIC_API_WS_URL || `ws://${HOST_DESARROLLO}:8000`;
