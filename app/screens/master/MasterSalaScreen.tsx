import { useEffect, useMemo, useState } from 'react';
import { FlatList, Modal, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { Boton, BarraRecurso, IconoEvento, Insignia, Tarjeta } from '../../components';
import { api } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { NodoResumen } from '../../types';
import { color, espacio, radio, tipo } from '../../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'MasterSala'>;

const ETIQUETA_TIPO: Record<NodoResumen['tipo'], string> = {
  interactivo: 'Interactivo',
  narrativo: 'Narrativo',
  combate: 'Combate',
};

const COLOR_TIPO: Record<NodoResumen['tipo'], string> = {
  interactivo: color.interactivo,
  narrativo: color.narrativo,
  combate: color.combate,
};

const PASOS_AJUSTE = [-5, -1, 1, 5];

export default function MasterSalaScreen({ navigation }: Props) {
  const sala = useSalaStore((s) => s.sala);
  const token = useSalaStore((s) => s.token);
  const estado = useSalaStore((s) => s.estado);
  const personajes = useSalaStore((s) => s.personajes);
  const log = useSalaStore((s) => s.log);
  const palabrasBloqueadas = useSalaStore((s) => s.palabrasBloqueadas);
  const conectar = useSalaStore((s) => s.conectar);
  const desconectar = useSalaStore((s) => s.desconectar);
  const enviar = useSalaStore((s) => s.enviar);
  const reiniciar = useSalaStore((s) => s.reiniciar);

  const [nodos, setNodos] = useState<NodoResumen[]>([]);
  const [selectorVisible, setSelectorVisible] = useState(false);
  const [filtro, setFiltro] = useState('');
  const [expulsionArmada, setExpulsionArmada] = useState<string | null>(null);
  const [ajusteAbierto, setAjusteAbierto] = useState<string | null>(null);

  useEffect(() => {
    conectar();
    return () => desconectar();
  }, []);

  useEffect(() => {
    if (sala && token) {
      api.listarNodos(sala.codigo, token).then(setNodos).catch(() => {});
    }
  }, [sala, token]);

  useEffect(() => {
    if (!sala) {
      navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
    }
  }, [sala]);

  const nodosFiltrados = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    if (!q) return nodos;
    return nodos.filter((n) => n.id.toLowerCase().includes(q) || n.texto.toLowerCase().includes(q));
  }, [nodos, filtro]);

  if (!sala) return null;

  const nodo = estado?.nodo;

  function salir() {
    reiniciar();
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  }

  function saltarA(nodoId: string) {
    enviar('override_nodo', { nodo_id: nodoId });
    setSelectorVisible(false);
    setFiltro('');
  }

  function ajustarVida(personajeId: string, delta: number) {
    enviar('ajustar_personaje', { personaje_id: personajeId, delta_vida: delta });
  }

  function ajustarMana(personajeId: string, delta: number) {
    enviar('ajustar_personaje', { personaje_id: personajeId, delta_mana: delta });
  }

  return (
    <View style={styles.contenedor}>
      <View style={styles.cabecera}>
        <View>
          <Text style={styles.codigoEtiqueta}>Código de sala</Text>
          <Text style={styles.codigo}>{sala.codigo}</Text>
        </View>
        <View style={styles.accionesCabecera}>
          <TouchableOpacity onPress={() => navigation.navigate('Ayuda')} hitSlop={8} testID="boton-ayuda-master">
            <Ionicons name="help-circle-outline" size={22} color={color.textoSecundario} />
          </TouchableOpacity>
          <TouchableOpacity onPress={salir}>
            <Text style={styles.salir}>Salir</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={styles.panelPrincipal} contentContainerStyle={{ padding: espacio.lg, gap: espacio.md }}>
        {estado?.finalizada && (
          <View style={styles.finalBanner}>
            <Text style={styles.finalBannerTexto}>Partida finalizada — final: {estado.tipo_final}</Text>
          </View>
        )}

        {nodo && (
          <View style={styles.filaNodoTitulo}>
            <Insignia texto={ETIQUETA_TIPO[nodo.tipo]} tono="acento" />
            <Text style={styles.nodoId}>{estado?.nodo_actual_id}</Text>
          </View>
        )}
        <Text style={[styles.nodoTexto, nodo && { borderLeftColor: COLOR_TIPO[nodo.tipo] }]}>{nodo?.texto}</Text>

        {nodo?.tipo === 'interactivo' && (
          <Tarjeta>
            <Text style={styles.seccionTitulo}>PALABRAS CLAVE</Text>
            {nodo.palabras_clave?.map((p) => {
              const clave = `${estado?.nodo_actual_id}:${p.texto}`;
              const usada = estado?.palabras_clave_usadas.includes(clave);
              const bloqueadaPor = palabrasBloqueadas[clave];
              return (
                <View key={p.texto} style={styles.palabraFila}>
                  <Text style={[styles.palabraTexto, usada && styles.palabraUsada]}>{p.texto}</Text>
                  {usada && <Insignia texto="agotada" />}
                  {bloqueadaPor && !usada && (
                    <Insignia texto={bloqueadaPor} tono="aviso" icono="lock-closed-outline" />
                  )}
                </View>
              );
            })}
          </Tarjeta>
        )}

        {nodo?.tipo === 'narrativo' && (
          <Boton texto="Avanzar al siguiente nodo" onPress={() => enviar('continuar')} variante="secundario" />
        )}

        {estado?.fase === 'combate' && estado.combate && (
          <Tarjeta acento={color.combate}>
            <Text style={styles.seccionTitulo}>COMBATE — RONDA {estado.combate.ronda}</Text>
            <Text style={styles.turnoTexto}>
              Turno de:{' '}
              {personajes.find(
                (p) => p.id === estado.combate!.orden_iniciativa[estado.combate!.turno_index]?.split(':')[1]
              )?.nombre ?? '—'}
            </Text>
            {estado.combate.enemigos.map((en) => (
              <View key={en.enemigo_id} style={styles.filaEnemigo}>
                <Text style={styles.enemigoNombre} numberOfLines={1}>
                  {en.nombre}{' '}
                  {en.derrotado && <Ionicons name="skull-outline" size={13} color={color.textoTenue} />}
                  {en.aturdido && <Ionicons name="sparkles-outline" size={13} color={color.aviso} />}
                </Text>
                <View style={{ flex: 1 }}>
                  <BarraRecurso etiqueta="PV" actual={en.vida} maximo={en.vida_max} />
                </View>
              </View>
            ))}
          </Tarjeta>
        )}

        <Tarjeta>
          <Text style={styles.seccionTitulo}>JUGADORES</Text>
          {personajes.map((p) => (
            <View key={p.id} style={styles.jugadorBloque}>
              <View style={styles.jugadorCabecera}>
                <Text style={styles.jugadorNombre}>
                  {p.nombre} <Text style={styles.jugadorDe}>· {p.jugador_nombre}</Text>
                </Text>
                {p.estado === 'ausente' && <Insignia texto="ausente" tono="aviso" />}
                {p.estado === 'muerto' && <Insignia texto="murió" tono="peligro" />}
              </View>
              <BarraRecurso etiqueta="PV" actual={p.vida_actual} maximo={p.vida_max} />
              <BarraRecurso etiqueta="Maná" actual={p.mana_actual} maximo={p.mana_max} sinAlerta />
              <View style={styles.filaAccionesJugador}>
                {p.estado !== 'muerto' && (
                  <TouchableOpacity
                    style={styles.botonAusente}
                    onPress={() =>
                      enviar(p.estado === 'ausente' ? 'marcar_activo' : 'marcar_ausente', { personaje_id: p.id })
                    }
                  >
                    <Text style={styles.botonAusenteTexto}>
                      {p.estado === 'ausente' ? 'Reactivar' : 'Marcar ausente'}
                    </Text>
                  </TouchableOpacity>
                )}
                {p.estado !== 'muerto' && (
                  <TouchableOpacity
                    style={styles.botonAusente}
                    onPress={() => setAjusteAbierto(ajusteAbierto === p.id ? null : p.id)}
                  >
                    <Text style={styles.botonAusenteTexto}>
                      {ajusteAbierto === p.id ? 'Cerrar ajuste' : 'Ajustar PV / maná'}
                    </Text>
                  </TouchableOpacity>
                )}
                {expulsionArmada === p.id ? (
                  <View style={styles.filaConfirmarExpulsion}>
                    <TouchableOpacity
                      style={styles.botonExpulsarConfirmar}
                      onPress={() => {
                        enviar('expulsar_jugador', { personaje_id: p.id });
                        setExpulsionArmada(null);
                      }}
                    >
                      <Text style={styles.botonExpulsarConfirmarTexto}>¿Seguro? Expulsar</Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => setExpulsionArmada(null)}>
                      <Text style={styles.cancelarExpulsion}>Cancelar</Text>
                    </TouchableOpacity>
                  </View>
                ) : (
                  <TouchableOpacity style={styles.botonExpulsar} onPress={() => setExpulsionArmada(p.id)}>
                    <Text style={styles.botonExpulsarTexto}>Expulsar</Text>
                  </TouchableOpacity>
                )}
              </View>
              {ajusteAbierto === p.id && (
                <View style={styles.panelAjuste}>
                  <View style={styles.filaAjusteRecurso}>
                    <Text style={styles.etiquetaAjuste}>PV</Text>
                    {PASOS_AJUSTE.map((paso) => (
                      <TouchableOpacity
                        key={paso}
                        style={styles.botonPaso}
                        onPress={() => ajustarVida(p.id, paso)}
                      >
                        <Text style={styles.botonPasoTexto}>{paso > 0 ? `+${paso}` : paso}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  <View style={styles.filaAjusteRecurso}>
                    <Text style={styles.etiquetaAjuste}>Maná</Text>
                    {PASOS_AJUSTE.map((paso) => (
                      <TouchableOpacity
                        key={paso}
                        style={styles.botonPaso}
                        onPress={() => ajustarMana(p.id, paso)}
                      >
                        <Text style={styles.botonPasoTexto}>{paso > 0 ? `+${paso}` : paso}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}
            </View>
          ))}
        </Tarjeta>

        <Tarjeta>
          <Text style={styles.seccionTitulo}>CONTROL DEL MÁSTER</Text>
          <Boton texto="Forzar salto de nodo…" onPress={() => setSelectorVisible(true)} variante="secundario" />
        </Tarjeta>
      </ScrollView>

      <View style={styles.panelLog}>
        <Text style={styles.seccionTitulo}>ACTIVIDAD EN VIVO</Text>
        <FlatList
          data={log}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <Text style={styles.logTexto}>
              <Text style={styles.logHora}>{item.hora} </Text>
              {item.icono && (
                <>
                  <IconoEvento icono={item.icono} />{' '}
                </>
              )}
              {item.texto}
            </Text>
          )}
        />
      </View>

      <Modal
        visible={selectorVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setSelectorVisible(false)}
      >
        <View style={styles.modalFondo}>
          <View style={styles.modalContenido}>
            <View style={styles.modalCabecera}>
              <Text style={styles.seccionTitulo}>ELEGIR NODO DESTINO</Text>
              <TouchableOpacity onPress={() => setSelectorVisible(false)}>
                <Text style={styles.salir}>Cerrar</Text>
              </TouchableOpacity>
            </View>
            <TextInput
              style={styles.input}
              placeholder="Buscar por id o texto…"
              placeholderTextColor={color.textoTenue}
              value={filtro}
              onChangeText={setFiltro}
            />
            <FlatList
              data={nodosFiltrados}
              keyExtractor={(item) => item.id}
              style={{ marginTop: espacio.sm }}
              renderItem={({ item }) => (
                <TouchableOpacity onPress={() => saltarA(item.id)} activeOpacity={0.85}>
                  <Tarjeta
                    seleccionada={item.id === estado?.nodo_actual_id}
                    acento={COLOR_TIPO[item.tipo]}
                    style={{ marginBottom: espacio.sm }}
                  >
                    <View style={styles.nodoItemCabecera}>
                      <Text style={styles.nodoItemId}>{item.id}</Text>
                      <Text style={styles.nodoItemTipo}>
                        {item.es_final ? `Final: ${item.tipo_final}` : ETIQUETA_TIPO[item.tipo]}
                      </Text>
                    </View>
                    <Text style={styles.nodoItemTexto} numberOfLines={2}>
                      {item.texto}
                    </Text>
                  </Tarjeta>
                </TouchableOpacity>
              )}
            />
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: color.fondo },
  cabecera: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: espacio.lg,
    borderBottomWidth: 1,
    borderBottomColor: color.borde,
  },
  codigoEtiqueta: { color: color.textoSecundario, fontSize: 11 },
  codigo: { ...tipo.titulo, fontSize: 24, letterSpacing: 4 },
  accionesCabecera: { flexDirection: 'row', alignItems: 'center', gap: espacio.md },
  salir: { color: color.peligro, fontWeight: '600' },
  panelPrincipal: { flex: 1 },
  finalBanner: { backgroundColor: color.acentoSuave, padding: espacio.md, borderRadius: radio.md, borderWidth: 1, borderColor: color.acento },
  finalBannerTexto: { color: color.texto, fontWeight: '600' },
  filaNodoTitulo: { flexDirection: 'row', alignItems: 'center', gap: espacio.sm },
  nodoId: { color: color.textoTenue, fontSize: 12 },
  nodoTexto: {
    color: color.texto,
    fontSize: 16,
    lineHeight: 23,
    borderLeftWidth: 3,
    borderLeftColor: color.borde,
    paddingLeft: espacio.md,
  },
  seccionTitulo: { ...tipo.seccion, marginBottom: 2 },
  palabraFila: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 4 },
  palabraTexto: { color: color.texto, flex: 1 },
  palabraUsada: { color: color.textoTenue, textDecorationLine: 'line-through' },
  turnoTexto: { color: color.texto, fontWeight: '700', marginBottom: 4 },
  filaEnemigo: { flexDirection: 'row', alignItems: 'center', gap: espacio.sm, marginTop: 4 },
  enemigoNombre: { color: color.texto, width: 100, fontSize: 12 },
  jugadorBloque: { gap: 6, paddingVertical: espacio.sm, borderTopWidth: 1, borderTopColor: color.bordeSutil },
  jugadorCabecera: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: espacio.sm },
  jugadorNombre: { color: color.texto, fontWeight: '700', flex: 1 },
  jugadorDe: { color: color.textoTenue, fontWeight: '400' },
  botonAusente: {
    backgroundColor: color.superficieAlt,
    borderWidth: 1,
    borderColor: color.acento,
    borderRadius: radio.sm,
    paddingHorizontal: 10,
    paddingVertical: 6,
    alignSelf: 'flex-start',
    marginTop: 2,
  },
  botonAusenteTexto: { color: color.texto, fontSize: 11, fontWeight: '600' },
  filaAccionesJugador: { flexDirection: 'row', alignItems: 'center', gap: espacio.sm, marginTop: 2, flexWrap: 'wrap' },
  botonExpulsar: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: color.peligro,
    borderRadius: radio.sm,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  botonExpulsarTexto: { color: color.peligro, fontSize: 11, fontWeight: '600' },
  filaConfirmarExpulsion: { flexDirection: 'row', alignItems: 'center', gap: espacio.sm },
  botonExpulsarConfirmar: {
    backgroundColor: color.peligroFuerte,
    borderRadius: radio.sm,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  botonExpulsarConfirmarTexto: { color: '#fff', fontSize: 11, fontWeight: '700' },
  cancelarExpulsion: { color: color.textoSecundario, fontSize: 11 },
  panelAjuste: {
    backgroundColor: color.fondoElevado,
    borderRadius: radio.md,
    padding: espacio.sm,
    marginTop: espacio.xs,
    gap: espacio.xs,
  },
  filaAjusteRecurso: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  etiquetaAjuste: { color: color.textoSecundario, fontSize: 11, fontWeight: '700', width: 38 },
  botonPaso: {
    backgroundColor: color.superficieAlt,
    borderWidth: 1,
    borderColor: color.bordeSutil,
    borderRadius: radio.sm,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  botonPasoTexto: { color: color.texto, fontSize: 12, fontWeight: '700' },
  input: {
    backgroundColor: color.superficieAlt,
    borderRadius: radio.md,
    padding: 10,
    color: color.texto,
    borderWidth: 1,
    borderColor: color.bordeSutil,
  },
  panelLog: {
    height: 160,
    borderTopWidth: 1,
    borderTopColor: color.borde,
    padding: espacio.md,
  },
  logTexto: { color: color.textoSecundario, fontSize: 12, marginBottom: 2 },
  logHora: { color: color.textoTenue },
  modalFondo: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  modalContenido: {
    backgroundColor: color.fondo,
    borderTopLeftRadius: radio.xl,
    borderTopRightRadius: radio.xl,
    padding: espacio.lg,
    maxHeight: '80%',
    borderWidth: 1,
    borderColor: color.borde,
  },
  modalCabecera: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: espacio.sm,
  },
  nodoItemCabecera: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  nodoItemId: { color: color.texto, fontWeight: '700' },
  nodoItemTipo: { color: color.textoTenue, fontSize: 11 },
  nodoItemTexto: { color: color.textoSecundario, fontSize: 12 },
});
