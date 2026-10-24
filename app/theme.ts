/**
 * Sistema de diseño compartido por toda la app. Un solo sitio para los
 * colores/espaciados/tipos — así una pantalla nueva encaja visualmente sin
 * tener que copiar valores hex de otra.
 */

/** Paleta de acentos que se puede elegir en Opciones. Cada entrada define
 * las tres variantes que ya usaba `color.acento*` (sólido, fuerte para
 * estados activos, suave para fondos tenues), elegidas para mantener el
 * mismo nivel de contraste sobre el fondo oscuro de la app. "Latón" es el
 * acento de marca por defecto, a tono con el resto de la identidad
 * (archivo de expedientes antiguo); los demás se mantienen como opciones
 * elegibles por quien juegue. */
export const PALETA_ACENTOS = {
  laton: { nombre: 'Latón', acento: '#b08a4e', acentoFuerte: '#d1a868', acentoSuave: '#3a2f1a' },
  morado: { nombre: 'Morado', acento: '#8a5fd0', acentoFuerte: '#a97fe0', acentoSuave: '#3d2360' },
  carmesi: { nombre: 'Carmesí', acento: '#c2555f', acentoFuerte: '#d97b83', acentoSuave: '#3a2228' },
  esmeralda: { nombre: 'Esmeralda', acento: '#4fa876', acentoFuerte: '#6fc292', acentoSuave: '#1f3a2c' },
  azul: { nombre: 'Azul noche', acento: '#4f7fc2', acentoFuerte: '#74a0e0', acentoSuave: '#1f2d4a' },
  grafito: { nombre: 'Grafito', acento: '#6f6a80', acentoFuerte: '#8f89a0', acentoSuave: '#2a2735' },
} as const;

export type AcentoId = keyof typeof PALETA_ACENTOS;
export const ACENTO_POR_DEFECTO: AcentoId = 'laton';

export const color = {
  // Capas de fondo, de más oscura a más clara. Tinta y papel envejecido
  // en vez del morado-sobre-negro genérico que tenía la app antes.
  fondo: '#110f0c',
  fondoElevado: '#19160f',
  superficie: '#221d14',
  superficieAlt: '#2a2318',
  borde: '#4a3d28',
  bordeSutil: '#3a3020',

  // Acento principal (marca) y su variante fuerte para estados activos.
  // Valores iniciales = paleta por defecto; un componente que quiera
  // reaccionar a un cambio de acento elegido en Opciones debe leerlo del
  // hook `useAcento` (en store/configStore.ts) en vez de esta copia
  // estática — estos tres solo sirven de valor de arranque/fallback.
  acento: PALETA_ACENTOS[ACENTO_POR_DEFECTO].acento,
  acentoFuerte: PALETA_ACENTOS[ACENTO_POR_DEFECTO].acentoFuerte,
  acentoSuave: PALETA_ACENTOS[ACENTO_POR_DEFECTO].acentoSuave,

  // Texto.
  texto: '#e8dcc0',
  textoSecundario: '#b9ac8a',
  textoTenue: '#7d735a',
  // El texto que va encima de una superficie pintada con el color de
  // acento (p. ej. una insignia de voto en latón) necesita ser oscuro
  // para seguir siendo legible — blanco puro casi no contrasta sobre un
  // acento claro como el latón.
  textoSobreAcento: '#1d1708',

  // Semánticos.
  exito: '#6fd08f',
  exitoSuave: '#1f3328',
  peligro: '#a4544f',
  peligroFuerte: '#c2726d',
  peligroSuave: '#3a2420',
  aviso: '#d1a868',
  avisoSuave: '#3a2f1a',

  // El maná siempre es azul, nunca el acento elegible en Opciones — si
  // alguien elige un acento rojo, el maná no debe teñirse de rojo.
  mana: '#4f7fc2',

  // Un color por tipo de nodo, para que el jugador reconozca de un
  // vistazo si está ante narrativa, una decisión o un combate.
  narrativo: '#5c8a74',
  interactivo: '#c2975f',
  combate: '#a4544f',
} as const;

export const fuente = {
  // Serif de época para títulos — da aire "de libro antiguo" de verdad,
  // en vez de depender de una serif de sistema genérica.
  display: 'Spectral-Medium',
  displaySemiNegrita: 'Spectral-SemiBold',
  displayCursiva: 'Spectral-MediumItalic',
  // Sans humanista para texto de cuerpo — legible en pantallas pequeñas,
  // sin caer en el Inter/fuente-de-sistema que usa todo el mundo.
  cuerpo: 'PublicSans-Regular',
  cuerpoMedia: 'PublicSans-Medium',
  cuerpoSemiNegrita: 'PublicSans-SemiBold',
  cuerpoNegrita: 'PublicSans-Bold',
  // Máquina de escribir — solo para sellos, códigos y etiquetas cortas,
  // nunca para párrafos (ver AGENTS.md de cada pantalla que la usa).
  sello: 'SpecialElite-Regular',
} as const;

export const espacio = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

// El redondeo suave (sm..pill) se reserva para lo que se toca (botones,
// insignias). Las superficies de "papel" (tarjetas, fichas) usan `papel`,
// casi angular — antes todo compartía el mismo radio, sin distinción.
export const radio = { papel: 3, sm: 6, md: 10, lg: 14, xl: 20, pill: 999 } as const;

export const tipo = {
  titulo: { fontFamily: fuente.displaySemiNegrita, fontSize: 28, color: color.texto },
  subtitulo: { fontFamily: fuente.display, fontSize: 20, color: color.texto },
  seccion: { fontFamily: fuente.cuerpoSemiNegrita, fontSize: 13, color: color.textoSecundario, letterSpacing: 0.6 },
  cuerpo: { fontFamily: fuente.cuerpo, fontSize: 15, color: color.texto, lineHeight: 21 },
  nota: { fontFamily: fuente.cuerpo, fontSize: 13, color: color.textoSecundario, lineHeight: 18 },
  diminuta: { fontFamily: fuente.cuerpo, fontSize: 11, color: color.textoTenue },
} as const;
