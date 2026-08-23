import { useEffect, useRef } from 'react';
import { Animated, FlatList, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { useSalaStore } from '../../store/salaStore';

type Props = NativeStackScreenProps<RootStackParamList, 'JugadorJuego'>;

function formatearId(id: string): string {
  return id.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

export default function JuegoScreen({ navigation }: Props) {
  const sala = useSalaStore((s) => s.sala);
  const personaje = useSalaStore((s) => s.personaje);
  const estado = useSalaStore((s) => s.estado);
  const log = useSalaStore((s) => s.log);
  const palabrasBloqueadas = useSalaStore((s) => s.palabrasBloqueadas);
  const ultimaTirada = useSalaStore((s) => s.ultimaTirada);
  const conectar = useSalaStore((s) => s.conectar);
  const desconectar = useSalaStore((s) => s.desconectar);
  const enviar = useSalaStore((s) => s.enviar);
  const reiniciar = useSalaStore((s) => s.reiniciar);

  const opacidadDado = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    conectar();
    return () => desconectar();
  }, []);

  useEffect(() => {
    if (!ultimaTirada) return;
    opacidadDado.setValue(1);
    Animated.timing(opacidadDado, { toValue: 0, duration: 2500, useNativeDriver: true }).start();
  }, [ultimaTirada]);

  if (!sala || !personaje) return null;

  const nodo = estado?.nodo;
  const enCombate = estado?.fase === 'combate' && estado.combate;
  const esMiTurno =
    enCombate && estado!.combate!.orden_iniciativa[estado!.combate!.turno_index] === `personaje:${personaje.id}`;

  function salir() {
    reiniciar();
    navigation.popToTop();
  }

  return (
    <View style={styles.contenedor}>
      <View style={styles.cabecera}>
        <View>
          <Text style={styles.nombrePersonaje}>{personaje.nombre}</Text>
          <Text style={styles.ficha}>
            PV {personaje.vida_actual}/{personaje.vida_max} · Maná {personaje.mana_actual}/
            {personaje.mana_max}
          </Text>
        </View>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>

      <Animated.View style={[styles.dadoFlotante, { opacity: opacidadDado }]} pointerEvents="none">
        {ultimaTirada && (
          <>
            <Text style={styles.dadoValor}>🎲 {ultimaTirada.dado ?? '?'}</Text>
            <Text style={[styles.dadoResultado, ultimaTirada.exito ? styles.exito : styles.fallo]}>
              {ultimaTirada.exito ? 'ÉXITO' : 'FALLO'} (total {ultimaTirada.total ?? '?'})
            </Text>
          </>
        )}
      </Animated.View>

      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
        {estado?.finalizada && (
          <View style={styles.finalBanner}>
            <Text style={styles.finalBannerTexto}>
              Fin de la historia — final: {estado.tipo_final}
            </Text>
          </View>
        )}

        <Text style={styles.nodoTexto}>{nodo?.texto}</Text>

        {nodo?.tipo === 'interactivo' && !enCombate && (
          <View style={{ gap: 8 }}>
            {nodo.palabras_clave?.map((p) => {
              const clave = `${estado?.nodo_actual_id}:${p.texto}`;
              const usada = estado?.palabras_clave_usadas.includes(clave);
              const bloqueada = !!palabrasBloqueadas[clave];
              const deshabilitada = usada || bloqueada;

              const hechizosDisponibles = personaje.hechizos_conocidos.filter(
                (h) => h === p.hechizo_id_alternativo
              );

              return (
                <View key={p.texto} style={styles.tarjetaPalabra}>
                  <TouchableOpacity
                    disabled={deshabilitada}
                    style={[styles.botonPalabra, deshabilitada && styles.botonPalabraDeshabilitado]}
                    onPress={() => enviar('interactuar', { palabra_clave: p.texto })}
                  >
                    <Text
                      style={[
                        styles.botonPalabraTexto,
                        deshabilitada && styles.botonPalabraTextoDeshabilitado,
                      ]}
                    >
                      {p.texto}
                    </Text>
                    {usada && <Text style={styles.etiquetaEstado}>agotada</Text>}
                    {bloqueada && !usada && <Text style={styles.etiquetaEstado}>en curso…</Text>}
                  </TouchableOpacity>

                  {!deshabilitada &&
                    hechizosDisponibles.map((h) => (
                      <TouchableOpacity
                        key={h}
                        style={styles.botonHechizo}
                        onPress={() =>
                          enviar('interactuar', {
                            palabra_clave: p.texto,
                            via: 'hechizo',
                            hechizo_id: h,
                          })
                        }
                      >
                        <Text style={styles.botonHechizoTexto}>
                          Lanzar {formatearId(h)} (vía mágica)
                        </Text>
                      </TouchableOpacity>
                    ))}
                </View>
              );
            })}
          </View>
        )}

        {nodo?.tipo === 'narrativo' && (
          <TouchableOpacity style={styles.botonContinuar} onPress={() => enviar('continuar')}>
            <Text style={styles.botonContinuarTexto}>Continuar</Text>
          </TouchableOpacity>
        )}

        {enCombate && (
          <View style={{ gap: 8 }}>
            <Text style={styles.seccionTitulo}>
              Combate — ronda {estado!.combate!.ronda} {esMiTurno ? '(tu turno)' : '(esperando…)'}
            </Text>
            {estado!.combate!.enemigos.map((en) => (
              <View key={en.enemigo_id} style={styles.tarjetaEnemigo}>
                <Text style={styles.enemigoNombre}>
                  {en.nombre} — {en.vida}/{en.vida_max} PV {en.derrotado ? '☠' : ''}
                </Text>
                {esMiTurno && !en.derrotado && (
                  <TouchableOpacity
                    style={styles.botonAtacar}
                    onPress={() =>
                      enviar('combate_accion', { accion: 'atacar', enemigo_id: en.enemigo_id })
                    }
                  >
                    <Text style={styles.botonAtacarTexto}>Atacar</Text>
                  </TouchableOpacity>
                )}
              </View>
            ))}
            {esMiTurno && (
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <TouchableOpacity
                  style={styles.botonSecundario}
                  onPress={() => enviar('combate_accion', { accion: 'huir' })}
                >
                  <Text style={styles.botonSecundarioTexto}>Huir</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.botonSecundario}
                  onPress={() => enviar('combate_accion', { accion: 'negociar' })}
                >
                  <Text style={styles.botonSecundarioTexto}>Negociar</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        )}

        {personaje.inventario.length > 0 && (
          <View>
            <Text style={styles.seccionTitulo}>Inventario</Text>
            <Text style={styles.inventarioTexto}>
              {personaje.inventario.map((o) => o.nombre).join(', ')}
            </Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.panelLog}>
        <FlatList
          data={log.slice(0, 20)}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <Text style={styles.logTexto}>{item.texto}</Text>}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: '#1a1523' },
  cabecera: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#3d2f57',
  },
  nombrePersonaje: { color: '#fff', fontSize: 18, fontWeight: '700' },
  ficha: { color: '#c9b8e0', fontSize: 12 },
  salir: { color: '#ff8a8a' },
  dadoFlotante: {
    position: 'absolute',
    top: 90,
    alignSelf: 'center',
    backgroundColor: '#241b33',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    zIndex: 10,
    borderWidth: 1,
    borderColor: '#6b3fa0',
  },
  dadoValor: { fontSize: 28, color: '#fff' },
  dadoResultado: { fontSize: 13, marginTop: 4, fontWeight: '700' },
  exito: { color: '#7fe0a3' },
  fallo: { color: '#e07f7f' },
  finalBanner: { backgroundColor: '#4a2f6b', padding: 12, borderRadius: 8 },
  finalBannerTexto: { color: '#fff', fontWeight: '600' },
  nodoTexto: { color: '#f3e9ff', fontSize: 16, lineHeight: 22 },
  tarjetaPalabra: { gap: 4 },
  botonPalabra: {
    backgroundColor: '#2f2540',
    borderRadius: 10,
    padding: 14,
    borderWidth: 1,
    borderColor: '#6b3fa0',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  botonPalabraDeshabilitado: { borderColor: '#453a5c', opacity: 0.5 },
  botonPalabraTexto: { color: '#fff', fontSize: 15 },
  botonPalabraTextoDeshabilitado: { textDecorationLine: 'line-through' },
  etiquetaEstado: { color: '#e0c27f', fontSize: 11 },
  botonHechizo: {
    backgroundColor: '#2b1f45',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#8a6fd0',
    marginLeft: 12,
  },
  botonHechizoTexto: { color: '#c9b8ff', fontSize: 13 },
  botonContinuar: {
    backgroundColor: '#6b3fa0',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
  },
  botonContinuarTexto: { color: '#fff', fontWeight: '600' },
  seccionTitulo: { color: '#c9b8e0', fontWeight: '700' },
  tarjetaEnemigo: {
    backgroundColor: '#2f1f1f',
    borderRadius: 8,
    padding: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  enemigoNombre: { color: '#f3d9d9' },
  botonAtacar: { backgroundColor: '#8a3f3f', borderRadius: 6, paddingHorizontal: 12, paddingVertical: 6 },
  botonAtacarTexto: { color: '#fff', fontWeight: '600' },
  botonSecundario: {
    flex: 1,
    backgroundColor: '#2f2540',
    borderWidth: 1,
    borderColor: '#6b3fa0',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  botonSecundarioTexto: { color: '#fff', fontWeight: '600' },
  inventarioTexto: { color: '#d8cbe8' },
  panelLog: {
    height: 100,
    borderTopWidth: 1,
    borderTopColor: '#3d2f57',
    padding: 10,
  },
  logTexto: { color: '#a390bd', fontSize: 11, marginBottom: 2 },
});
