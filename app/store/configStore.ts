import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { PALETA_ACENTOS, ACENTO_POR_DEFECTO, type AcentoId } from '../theme';

interface ConfigState {
  acentoId: AcentoId;
  elegirAcento: (id: AcentoId) => void;
}

/** Preferencias de la app en sí (no de una partida concreta) — de momento
 * solo el color de acento, pensado para crecer con lo que haga falta en
 * Opciones más adelante. Vive en su propio store, separado de salaStore,
 * porque no tiene nada que ver con el ciclo de vida de una sala. */
export const useConfigStore = create<ConfigState>()(
  persist(
    (set) => ({
      acentoId: ACENTO_POR_DEFECTO,
      elegirAcento: (id) => set({ acentoId: id }),
    }),
    {
      name: 'rpg-config',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);

/** Las tres variantes del acento elegido, listas para usar en estilos —
 * así un componente no tiene que resolver `PALETA_ACENTOS[id]` a mano. */
export function useAcento() {
  const id = useConfigStore((s) => s.acentoId);
  return PALETA_ACENTOS[id];
}
