import { useEffect, useMemo, useState } from 'react';
import {
  FlatList,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { api } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { NodoResumen } from '../../types';

type Props = NativeStackScreenProps<RootStackParamList, 'MasterSala'>;

const ETIQUETA_TIPO: Record<NodoResumen['tipo'], string> = {
  interactivo: 'Interactivo',
  narrativo: 'Narrativo',
  combate: 'Combate',
};

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

  return (
    <View style={styles.contenedor}>
      <View style={styles.cabecera}>
        <Text style={styles.codigoEtiqueta}>Código de sala</Text>
        <Text style={styles.codigo}>{sala.codigo}</Text>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.panelPrincipal} contentContainerStyle={{ padding: 16, gap: 12 }}>
        {estado?.finalizada && (
          <View style={styles.finalBanner}>
            <Text style={styles.finalBannerTexto}>
              Partida finalizada — final: {estado.tipo_final}
            </Text>
          </View>
        )}

        <Text style={styles.nodoTitulo}>Nodo: {estado?.nodo_actual_id}</Text>
        <Text style={styles.nodoTexto}>{nodo?.texto}</Text>

        {nodo?.tipo === 'interactivo' && (
          <View style={styles.seccion}>
            <Text style={styles.seccionTitulo}>Palabras clave</Text>
            {nodo.palabras_clave?.map((p) => {
              const clave = `${estado?.nodo_actual_id}:${p.texto}`;
              const usada = estado?.palabras_clave_usadas.includes(clave);
              const bloqueadaPor = palabrasBloqueadas[clave];
              return (
                <View key={p.texto} style={styles.palabraFila}>
                  <Text style={[styles.palabraTexto, usada && styles.palabraUsada]}>
                    {p.texto} {usada ? '(agotada)' : ''}
                  </Text>
                  {bloqueadaPor && <Text style={styles.palabraBloqueo}>🔒 {bloqueadaPor}</Text>}
                </View>
              );
            })}
          </View>
        )}

        {nodo?.tipo === 'narrativo' && (
          <TouchableOpacity style={styles.botonSecundario} onPress={() => enviar('continuar')}>
            <Text style={styles.botonSecundarioTexto}>Avanzar al siguiente nodo</Text>
          </TouchableOpacity>
        )}

        {estado?.fase === 'combate' && estado.combate && (
          <View style={styles.seccion}>
            <Text style={styles.seccionTitulo}>Combate — ronda {estado.combate.ronda}</Text>
            {estado.combate.enemigos.map((en) => (
              <Text key={en.enemigo_id} style={styles.enemigoTexto}>
                {en.nombre}: {en.vida}/{en.vida_max} PV {en.derrotado ? '(derrotado)' : ''}
              </Text>
            ))}
          </View>
        )}

        <View style={styles.seccion}>
          <Text style={styles.seccionTitulo}>Jugadores</Text>
          {personajes.map((p) => (
            <View key={p.id} style={styles.jugadorFila}>
              <Text style={[styles.jugadorTexto, p.estado === 'ausente' && styles.jugadorAusente]}>
                {p.nombre} ({p.jugador_nombre}) — PV {p.vida_actual}/{p.vida_max} · Maná{' '}
                {p.mana_actual}/{p.mana_max}
                {p.estado === 'ausente' ? ' · ausente' : ''}
              </Text>
              <TouchableOpacity
                style={styles.botonAusente}
                onPress={() =>
                  enviar(p.estado === 'ausente' ? 'marcar_activo' : 'marcar_ausente', {
                    personaje_id: p.id,
                  })
                }
              >
                <Text style={styles.botonAusenteTexto}>
                  {p.estado === 'ausente' ? 'Reactivar' : 'Marcar ausente'}
                </Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>

        <View style={styles.seccion}>
          <Text style={styles.seccionTitulo}>Control del máster</Text>
          <TouchableOpacity style={styles.botonSecundario} onPress={() => setSelectorVisible(true)}>
            <Text style={styles.botonSecundarioTexto}>Forzar salto de nodo…</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      <View style={styles.panelLog}>
        <Text style={styles.seccionTitulo}>Actividad en vivo</Text>
        <FlatList
          data={log}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <Text style={styles.logTexto}>
              <Text style={styles.logHora}>{item.hora} </Text>
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
              <Text style={styles.seccionTitulo}>Elegir nodo destino</Text>
              <TouchableOpacity onPress={() => setSelectorVisible(false)}>
                <Text style={styles.salir}>Cerrar</Text>
              </TouchableOpacity>
            </View>
            <TextInput
              style={styles.input}
              placeholder="Buscar por id o texto…"
              placeholderTextColor="#7a6c8f"
              value={filtro}
              onChangeText={setFiltro}
            />
            <FlatList
              data={nodosFiltrados}
              keyExtractor={(item) => item.id}
              style={{ marginTop: 8 }}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.nodoItem,
                    item.id === estado?.nodo_actual_id && styles.nodoItemActual,
                  ]}
                  onPress={() => saltarA(item.id)}
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
  contenedor: { flex: 1, backgroundColor: '#1a1523' },
  cabecera: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#3d2f57',
  },
  codigoEtiqueta: { color: '#c9b8e0', fontSize: 12 },
  codigo: { color: '#fff', fontSize: 24, fontWeight: '700', letterSpacing: 4 },
  salir: { color: '#ff8a8a' },
  panelPrincipal: { flex: 1 },
  finalBanner: { backgroundColor: '#4a2f6b', padding: 12, borderRadius: 8 },
  finalBannerTexto: { color: '#fff', fontWeight: '600' },
  nodoTitulo: { color: '#a390bd', fontSize: 12 },
  nodoTexto: { color: '#f3e9ff', fontSize: 16, lineHeight: 22 },
  seccion: { backgroundColor: '#241b33', borderRadius: 10, padding: 12, gap: 6 },
  seccionTitulo: { color: '#c9b8e0', fontWeight: '700', marginBottom: 4 },
  palabraFila: { flexDirection: 'row', justifyContent: 'space-between' },
  palabraTexto: { color: '#fff' },
  palabraUsada: { color: '#7a6c8f', textDecorationLine: 'line-through' },
  palabraBloqueo: { color: '#e0c27f' },
  enemigoTexto: { color: '#e0a9a9' },
  jugadorFila: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  jugadorTexto: { color: '#d8cbe8', flex: 1 },
  jugadorAusente: { color: '#e0a9a9', fontStyle: 'italic' },
  botonAusente: {
    backgroundColor: '#2f2540',
    borderWidth: 1,
    borderColor: '#6b3fa0',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  botonAusenteTexto: { color: '#fff', fontSize: 11, fontWeight: '600' },
  input: {
    backgroundColor: '#2f2540',
    borderRadius: 8,
    padding: 10,
    color: '#fff',
    borderWidth: 1,
    borderColor: '#453a5c',
  },
  botonSecundario: {
    backgroundColor: '#2f2540',
    borderWidth: 1,
    borderColor: '#6b3fa0',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  botonSecundarioTexto: { color: '#fff', fontWeight: '600' },
  panelLog: {
    height: 160,
    borderTopWidth: 1,
    borderTopColor: '#3d2f57',
    padding: 12,
  },
  logTexto: { color: '#c9b8e0', fontSize: 12, marginBottom: 2 },
  logHora: { color: '#7a6c8f' },
  modalFondo: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  modalContenido: {
    backgroundColor: '#1a1523',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 16,
    maxHeight: '80%',
    borderWidth: 1,
    borderColor: '#3d2f57',
  },
  modalCabecera: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  nodoItem: {
    backgroundColor: '#241b33',
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#3d2f57',
  },
  nodoItemActual: { borderColor: '#a97fe0', backgroundColor: '#3d2f57' },
  nodoItemCabecera: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  nodoItemId: { color: '#fff', fontWeight: '700' },
  nodoItemTipo: { color: '#a390bd', fontSize: 11 },
  nodoItemTexto: { color: '#c9b8e0', fontSize: 12 },
});
