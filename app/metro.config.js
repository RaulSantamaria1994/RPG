const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Algunos paquetes (p. ej. zustand) publican su build "import" en ESM puro
// con `import.meta`, que el bundle web de Metro no soporta (no se carga como
// módulo). Esos mismos paquetes sí publican una condición "react-native"
// con una build CJS compatible; forzarla también en la plataforma web evita
// que Metro elija la build ESM rota al resolver esos subpaths.
config.resolver.unstable_conditionNames = ['react-native', 'require', 'import'];

module.exports = config;
