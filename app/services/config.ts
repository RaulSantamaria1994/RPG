import { Platform } from 'react-native';

// En desarrollo local, Android emulator no puede usar "localhost" (se refiere
// al propio emulador), así que se mapea a la IP especial del host.
const HOST_DESARROLLO = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';

export const API_BASE_URL = `http://${HOST_DESARROLLO}:8000`;
export const WS_BASE_URL = `ws://${HOST_DESARROLLO}:8000`;
