import { Platform } from 'react-native';

/**
 * Sistema de diseño compartido por toda la app. Un solo sitio para los
 * colores/espaciados/tipos — así una pantalla nueva encaja visualmente sin
 * tener que copiar valores hex de otra.
 */

/** Paleta de acentos que se puede elegir en Opciones — el morado es el
 * original de toda la vida. Cada entrada define las tres variantes que ya
 * usaba `color.acento*` (sólido, fuerte para estados activos, suave para
 * fondos tenues), elegidas para mantener el mismo nivel de contraste sobre
 * el fondo oscuro de la app que tenía el morado original. */
export const PALETA_ACENTOS = {
  morado: { nombre: 'Morado', acento: '#8a5fd0', acentoFuerte: '#a97fe0', acentoSuave: '#3d2360' },
  carmesi: { nombre: 'Carmesí', acento: '#c2555f', acentoFuerte: '#d97b83', acentoSuave: '#3a2228' },
  esmeralda: { nombre: 'Esmeralda', acento: '#4fa876', acentoFuerte: '#6fc292', acentoSuave: '#1f3a2c' },
  azul: { nombre: 'Azul noche', acento: '#4f7fc2', acentoFuerte: '#74a0e0', acentoSuave: '#1f2d4a' },
  ambar: { nombre: 'Ámbar', acento: '#c2975f', acentoFuerte: '#e0b87f', acentoSuave: '#3a2c1a' },
  grafito: { nombre: 'Grafito', acento: '#6f6a80', acentoFuerte: '#8f89a0', acentoSuave: '#2a2735' },
} as const;

export type AcentoId = keyof typeof PALETA_ACENTOS;
export const ACENTO_POR_DEFECTO: AcentoId = 'morado';

export const color = {
  // Capas de fondo, de más oscura a más clara.
  fondo: '#140f1e',
  fondoElevado: '#1c1529',
  superficie: '#241b33',
  superficieAlt: '#2c2242',
  borde: '#3d2f57',
  bordeSutil: '#453a5c',

  // Acento principal (marca) y su variante fuerte para estados activos.
  // Valores iniciales = paleta por defecto; un componente que quiera
  // reaccionar a un cambio de acento elegido en Opciones debe leerlo del
  // hook `useAcento` (en store/configStore.ts) en vez de esta copia
  // estática — estos tres solo sirven de valor de arranque/fallback.
  acento: PALETA_ACENTOS[ACENTO_POR_DEFECTO].acento,
  acentoFuerte: PALETA_ACENTOS[ACENTO_POR_DEFECTO].acentoFuerte,
  acentoSuave: PALETA_ACENTOS[ACENTO_POR_DEFECTO].acentoSuave,

  // Texto.
  texto: '#f3e9ff',
  textoSecundario: '#c9b8e0',
  textoTenue: '#8a7aa3',
  textoSobreAcento: '#ffffff',

  // Semánticos.
  exito: '#6fd08f',
  exitoSuave: '#1f3328',
  peligro: '#e0696f',
  peligroFuerte: '#c23f47',
  peligroSuave: '#3a2228',
  aviso: '#d0b86f',
  avisoSuave: '#332c1c',

  // Un color por tipo de nodo, para que el jugador reconozca de un
  // vistazo si está ante narrativa, una decisión o un combate.
  narrativo: '#8a6fd0',
  interactivo: '#d0b86f',
  combate: '#d0696f',
} as const;

export const fuente = {
  // Una serif del sistema para títulos: da aire "de libro antiguo" sin
  // depender de ninguna fuente externa que haya que empaquetar.
  display: Platform.select({ ios: 'Georgia', android: 'serif', default: 'Georgia, "Times New Roman", serif' }),
} as const;

export const espacio = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radio = { sm: 6, md: 10, lg: 14, xl: 20, pill: 999 } as const;

export const tipo = {
  titulo: { fontFamily: fuente.display, fontSize: 28, color: color.texto, fontWeight: '700' as const },
  subtitulo: { fontFamily: fuente.display, fontSize: 20, color: color.texto, fontWeight: '600' as const },
  seccion: { fontSize: 13, color: color.textoSecundario, fontWeight: '700' as const, letterSpacing: 0.6 },
  cuerpo: { fontSize: 15, color: color.texto, lineHeight: 21 },
  nota: { fontSize: 13, color: color.textoSecundario, lineHeight: 18 },
  diminuta: { fontSize: 11, color: color.textoTenue },
} as const;
