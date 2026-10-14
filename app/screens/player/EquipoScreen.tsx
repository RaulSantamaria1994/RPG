import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Boton, Tarjeta } from '../../components';
import { api } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { Hechizo, ObjetoInventario } from '../../types';
import { color, espacio, tipo } from '../../theme';

function nombreGrimorio(objeto: ObjetoInventario, hechizos: Hechizo[]): string {
  const hechizo = hechizos.find((h) => h.hechizo_id === objeto.hechizo_id);
  return hechizo ? `${objeto.nombre} — permite lanzar "${hechizo.nombre}"` : objeto.nombre;
}

/** Pestaña de equipo: cada jugador lleva como mucho un arma y un hechizo
 * (grimorio) equipados, sacados del inventario común — equiparlos los
 * reserva para quien los lleva, y desequiparlos los devuelve al grupo
 * para que otro los use. */
export default function EquipoScreen() {
  const sala = useSalaStore((s) => s.sala);
  const personaje = useSalaStore((s) => s.personaje);
  const inventarioGrupo = useSalaStore((s) => s.estado?.inventario_grupo) ?? [];
  const enviar = useSalaStore((s) => s.enviar);

  const [hechizos, setHechizos] = useState<Hechizo[]>([]);

  useEffect(() => {
    if (sala) {
      api.listarHechizos(sala.codigo).then(setHechizos).catch(() => {});
    }
  }, [sala]);

  if (!personaje) return null;

  const armas = inventarioGrupo.filter((o) => o.categoria === 'arma');
  const grimorios = inventarioGrupo.filter((o) => o.categoria === 'grimorio');

  return (
    <ScrollView contentContainerStyle={styles.contenedor}>
      <Text style={styles.titulo}>Equipo</Text>
      <Text style={styles.subtitulo}>
        Un arma y un hechizo como mucho, sacados del inventario común. Al desequipar algo vuelve al
        grupo para que otro lo lleve.
      </Text>

      <View style={{ gap: espacio.sm }}>
        <Text style={styles.seccionTitulo}>RANURA DE ARMA</Text>
        {personaje.arma_equipada ? (
          <Tarjeta acento={color.combate} style={styles.tarjetaRanura}>
            <View style={styles.filaRanura}>
              <MaterialCommunityIcons name="sword-cross" size={20} color={color.combate} />
              <View style={{ flex: 1 }}>
                <Text style={styles.objetoNombre}>{personaje.arma_equipada.nombre}</Text>
                {!!personaje.arma_equipada.bono_dano && (
                  <Text style={styles.objetoDetalle}>+{personaje.arma_equipada.bono_dano} de daño al atacar</Text>
                )}
              </View>
            </View>
            <Boton
              texto="Desequipar"
              variante="fantasma"
              onPress={() => enviar('desequipar_objeto', { ranura: 'arma' })}
            />
          </Tarjeta>
        ) : (
          <Tarjeta style={styles.tarjetaVacia}>
            <Text style={styles.vacioTexto}>Ninguna arma equipada.</Text>
          </Tarjeta>
        )}
      </View>

      <View style={{ gap: espacio.sm }}>
        <Text style={styles.seccionTitulo}>RANURA DE HECHIZO</Text>
        {personaje.hechizo_equipado ? (
          <Tarjeta acento={color.narrativo} style={styles.tarjetaRanura}>
            <View style={styles.filaRanura}>
              <MaterialCommunityIcons name="auto-fix" size={20} color={color.narrativo} />
              <View style={{ flex: 1 }}>
                <Text style={styles.objetoNombre}>{nombreGrimorio(personaje.hechizo_equipado, hechizos)}</Text>
              </View>
            </View>
            <Boton
              texto="Desequipar"
              variante="fantasma"
              onPress={() => enviar('desequipar_objeto', { ranura: 'hechizo' })}
            />
          </Tarjeta>
        ) : (
          <Tarjeta style={styles.tarjetaVacia}>
            <Text style={styles.vacioTexto}>Ningún hechizo equipado.</Text>
          </Tarjeta>
        )}
      </View>

      <View style={{ gap: espacio.sm }}>
        <Text style={styles.seccionTitulo}>ARMAS DEL INVENTARIO COMÚN</Text>
        {armas.length === 0 ? (
          <Text style={styles.vacioTexto}>No hay ninguna arma suelta en el grupo ahora mismo.</Text>
        ) : (
          armas.map((o) => (
            <Tarjeta key={o.objeto_id} style={styles.tarjetaDisponible}>
              <View style={{ flex: 1 }}>
                <Text style={styles.objetoNombre}>{o.nombre}</Text>
                {!!o.bono_dano && <Text style={styles.objetoDetalle}>+{o.bono_dano} de daño al atacar</Text>}
              </View>
              <Boton texto="Equipar" variante="secundario" onPress={() => enviar('equipar_objeto', { objeto_id: o.objeto_id })} />
            </Tarjeta>
          ))
        )}
      </View>

      <View style={{ gap: espacio.sm }}>
        <Text style={styles.seccionTitulo}>GRIMORIOS DEL INVENTARIO COMÚN</Text>
        {grimorios.length === 0 ? (
          <Text style={styles.vacioTexto}>No hay ningún grimorio suelto en el grupo ahora mismo.</Text>
        ) : (
          grimorios.map((o) => (
            <Tarjeta key={o.objeto_id} style={styles.tarjetaDisponible}>
              <Text style={[styles.objetoNombre, { flex: 1 }]}>{nombreGrimorio(o, hechizos)}</Text>
              <Boton texto="Equipar" variante="secundario" onPress={() => enviar('equipar_objeto', { objeto_id: o.objeto_id })} />
            </Tarjeta>
          ))
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: espacio.xl, backgroundColor: color.fondo, flexGrow: 1, gap: espacio.lg },
  titulo: { ...tipo.titulo, fontSize: 26, marginBottom: 2 },
  subtitulo: { ...tipo.nota },
  seccionTitulo: { color: color.textoSecundario, fontSize: 13, fontWeight: '700', letterSpacing: 0.6 },
  tarjetaRanura: { gap: espacio.sm },
  tarjetaVacia: { paddingVertical: espacio.md },
  tarjetaDisponible: { flexDirection: 'row', alignItems: 'center', gap: espacio.sm, paddingVertical: espacio.sm },
  filaRanura: { flexDirection: 'row', alignItems: 'center', gap: espacio.sm },
  objetoNombre: { color: color.texto, fontWeight: '600', fontSize: 14 },
  objetoDetalle: { color: color.textoSecundario, fontSize: 12, marginTop: 2 },
  vacioTexto: { color: color.textoTenue, fontSize: 13 },
});
