import { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Boton, Insignia, Tarjeta } from '../../../components';
import { useAcento } from '../../../store/configStore';
import type { Hechizo, Nodo, Personaje } from '../../../types';
import { color, espacio, radio } from '../../../theme';
import { ETIQUETA_ATRIBUTO, formatearId, resumenDeLaTirada, sufijoModoGrupal } from './comun';

type Props = {
  nodo: Nodo;
  nodoActualId: string;
  palabrasClaveUsadas: string[];
  palabrasBloqueadas: Record<string, string>;
  confirmacionesGrupales: Record<string, { confirmados: number; total: number }>;
  votosGrupales: { votados: number; total: number; recuento: Record<string, number> } | null;
  personaje: Personaje;
  hechizos: Hechizo[];
  lanzarDado: (tipoAccion: string, datos?: Record<string, unknown>) => void;
  enviar: (tipo: string, datos?: Record<string, unknown>) => void;
};

/** Lista de palabras clave del nodo interactivo actual — cada una se
 * despliega para mostrar qué hace falta para resolverla (tirada, apoyo,
 * vía mágica alternativa) y confirma la acción. Antes vivía inline en
 * JuegoScreen; tiene su propio estado de "cuál está desplegada" porque
 * nada fuera de este panel necesita saberlo. */
export default function PanelInteraccion({
  nodo,
  nodoActualId,
  palabrasClaveUsadas,
  palabrasBloqueadas,
  confirmacionesGrupales,
  votosGrupales,
  personaje,
  hechizos,
  lanzarDado,
  enviar,
}: Props) {
  const acento = useAcento();
  const [palabraExpandida, setPalabraExpandida] = useState<string | null>(null);

  return (
    <View style={{ gap: espacio.sm }}>
      {nodo.palabras_clave?.map((p) => {
        const clave = `${nodoActualId}:${p.texto}`;
        const usada = palabrasClaveUsadas.includes(clave);
        const bloqueada = !!palabrasBloqueadas[clave];
        const deshabilitada = usada || bloqueada;
        const expandida = palabraExpandida === clave;

        const hechizosDisponibles: string[] = [];
        for (const h of personaje.hechizos_conocidos) {
          let disponible = false;
          if (h === p.hechizo_id_alternativo) {
            disponible = true;
          } else if (p.categoria_hechizo_alternativa) {
            let categoriaDelHechizo: string | undefined;
            for (const x of hechizos) {
              if (x.hechizo_id === h) {
                categoriaDelHechizo = x.categoria;
              }
            }
            disponible = categoriaDelHechizo === p.categoria_hechizo_alternativa;
          }
          if (disponible) {
            hechizosDisponibles.push(h);
          }
        }

        const esVotacion = p.modo_interaccion === 'grupal' && !p.dificultad;
        const confirmacion = confirmacionesGrupales[clave];

        const requiereTirada = p.modo_interaccion === 'opuesta' || !!p.dificultad;
        const resumenTirada = resumenDeLaTirada(p, esVotacion);

        let contenidoRequisito;
        if (p.modo_interaccion === 'opuesta') {
          contenidoRequisito = (
            <Text style={styles.requisitoTexto}>
              Tirada enfrentada: tu {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} (
              {p.atributo ? personaje[p.atributo] : '?'}) contra un rival con modificador{' '}
              {p.npc_modificador ?? 0}.
            </Text>
          );
        } else if (p.dificultad) {
          let coletilla = '.';
          if (p.modo_interaccion === 'grupal') {
            coletilla = ' — cuenta la mejor tirada del grupo, según la regla.';
          }
          contenidoRequisito = (
            <Text style={styles.requisitoTexto}>
              Necesitas sacar {p.dificultad} o más tirando 1d20 +{' '}
              {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} (tu{' '}
              {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'}:{' '}
              {p.atributo ? personaje[p.atributo] : '?'})
              {coletilla}
              {p.dano_fallo ? ` Si falla, ${p.dano_fallo.cantidad} de daño.` : ''}
            </Text>
          );
        } else {
          contenidoRequisito = (
            <Text style={styles.requisitoTexto}>
              Esta acción no requiere tirada: se resuelve al confirmar.
            </Text>
          );
        }

        function tirar(datosExtra: Record<string, unknown> = {}) {
          const conDado = requiereTirada || datosExtra.via === 'hechizo' || datosExtra.rol_apoyo === 'apoyo';
          if (conDado) {
            lanzarDado('interactuar', { palabra_clave: p.texto, ...datosExtra });
          } else {
            enviar('interactuar', { palabra_clave: p.texto, ...datosExtra });
          }
          setPalabraExpandida(null);
        }

        return (
          <View key={p.texto}>
            <TouchableOpacity
              disabled={deshabilitada}
              onPress={() => setPalabraExpandida(expandida ? null : clave)}
              activeOpacity={0.85}
            >
              <Tarjeta
                acento={color.interactivo}
                seleccionada={expandida}
                atenuada={deshabilitada}
                style={styles.tarjetaPalabra}
              >
                <View style={styles.filaPalabraCabecera}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.textoPalabra}>
                      {p.texto}
                      {sufijoModoGrupal(esVotacion, p.modo_interaccion)}
                    </Text>
                    {!deshabilitada && (
                      <Text style={styles.subtextoPalabra}>
                        {requiereTirada && (
                          <MaterialCommunityIcons name="dice-d20-outline" size={12} color={color.textoSecundario} />
                        )}
                        {requiereTirada ? ' ' : ''}
                        {resumenTirada}
                      </Text>
                    )}
                  </View>
                  {usada && <Insignia texto="agotada" />}
                  {bloqueada && !usada && <Insignia texto="en curso…" tono="aviso" />}
                </View>

                {esVotacion && votosGrupales && !usada && (
                  <View style={styles.filaVotosOpcion}>
                    <Insignia
                      texto={`${votosGrupales.recuento[p.texto] ?? 0} voto(s) a esta opción`}
                      tono="acento"
                    />
                    <Insignia texto={`${votosGrupales.votados}/${votosGrupales.total} han votado`} tono="aviso" />
                  </View>
                )}
                {!esVotacion && p.modo_interaccion === 'grupal' && confirmacion && !usada && (
                  <Insignia
                    texto={`Confirmados: ${confirmacion.confirmados}/${confirmacion.total}`}
                    tono="aviso"
                  />
                )}

                {expandida && !deshabilitada && (
                  <View style={styles.panelExpandido}>
                    {contenidoRequisito}

                    <Boton
                      texto={requiereTirada ? 'Tirar dado' : 'Confirmar'}
                      icono={
                        requiereTirada ? (
                          <MaterialCommunityIcons name="dice-d20-outline" size={17} color={color.textoSobreAcento} />
                        ) : undefined
                      }
                      onPress={() => tirar()}
                    />

                    {p.modo_interaccion === 'apoyo' && (
                      <TouchableOpacity style={styles.botonApoyo} onPress={() => tirar({ rol_apoyo: 'apoyo' })}>
                        <Text style={styles.botonApoyoTexto}>
                          Ayudar con {p.atributo_apoyo ? ETIQUETA_ATRIBUTO[p.atributo_apoyo] : 'otro atributo'} —
                          dificultad {p.dificultad_apoyo ?? p.dificultad ?? 10} (da ventaja a quien actúe)
                        </Text>
                      </TouchableOpacity>
                    )}

                    {hechizosDisponibles.map((h) => {
                      let info;
                      for (const x of hechizos) {
                        if (x.hechizo_id === h) {
                          info = x;
                        }
                      }
                      return (
                        <TouchableOpacity
                          key={h}
                          style={[styles.botonHechizo, { borderColor: acento.acento }]}
                          onPress={() => tirar({ via: 'hechizo', hechizo_id: h })}
                        >
                          <Text style={styles.botonHechizoTexto}>
                            <MaterialCommunityIcons name="dice-d20-outline" size={13} color={color.textoSecundario} />{' '}
                            Lanzar {info?.nombre ?? formatearId(h)} (vía mágica) — dificultad {info?.dificultad ?? '?'},
                            coste {info?.coste_mana ?? '?'} maná
                          </Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                )}
              </Tarjeta>
            </TouchableOpacity>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  tarjetaPalabra: { gap: espacio.xs },
  filaPalabraCabecera: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: espacio.sm },
  filaVotosOpcion: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.xs, marginTop: 4 },
  textoPalabra: { color: color.texto, fontSize: 15, fontWeight: '600' },
  subtextoPalabra: { color: color.textoSecundario, fontSize: 12, marginTop: 3 },
  panelExpandido: {
    backgroundColor: color.fondoElevado,
    borderRadius: radio.md,
    padding: espacio.sm,
    marginTop: 4,
    gap: espacio.sm,
  },
  requisitoTexto: { color: color.textoSecundario, fontSize: 13, lineHeight: 18 },
  botonHechizo: {
    backgroundColor: color.superficie,
    borderRadius: radio.md,
    padding: 10,
    borderWidth: 1,
    borderColor: color.acento,
  },
  botonHechizoTexto: { color: color.textoSecundario, fontSize: 13 },
  botonApoyo: {
    backgroundColor: color.superficie,
    borderRadius: radio.md,
    padding: 10,
    borderWidth: 1,
    borderColor: '#6f9fd0',
  },
  botonApoyoTexto: { color: '#b8d8ff', fontSize: 13 },
});
