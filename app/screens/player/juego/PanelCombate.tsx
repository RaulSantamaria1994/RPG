import { useState } from 'react';
import { Animated, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Boton, BarraRecurso, Tarjeta } from '../../../components';
import { useEscalaPresion } from '../../../hooks/useEscalaPresion';
import { useAcento } from '../../../store/configStore';
import type { EstadoCombate, Hechizo, ObjetoInventario, Personaje } from '../../../types';
import { color, espacio, radio } from '../../../theme';

type Props = {
  combate: EstadoCombate;
  esMiTurno: boolean;
  personajeEnTurnoNombre?: string;
  personaje: Personaje;
  personajes: Personaje[];
  hechizos: Hechizo[];
  inventarioGrupo: ObjetoInventario[];
  lanzarDado: (tipoAccion: string, datos?: Record<string, unknown>) => void;
  enviar: (tipo: string, datos?: Record<string, unknown>) => void;
};

const EFECTOS_HECHIZO_COMBATE = new Set(['dano_directo', 'restaura_vida_o_mana', 'aturdir_enemigo']);
const EFECTOS_OBJETO_COMBATE = new Set(['curar_vida', 'curar_mana', 'dano']);

/** Cuánto cura, o cuánto daña, un objeto usable en combate, en un texto
 * listo para mostrar junto a su nombre. */
function textoEfectoObjeto(tipo: string | undefined, cantidad: number): string {
  if (tipo === 'curar_vida') return `+${cantidad} PV`;
  if (tipo === 'curar_mana') return `+${cantidad} maná`;
  return `${cantidad} de daño`;
}

/** El botón "Atacar" vive dentro de un `.map` por enemigo, y un hook no se
 * puede llamar directamente ahí dentro — de ahí este pequeño componente
 * aparte, solo para darle el mismo tacto de pulsación que `Boton`. */
function BotonAtacar({ onPress }: { onPress: () => void }) {
  const { escala, presionar, soltar } = useEscalaPresion();
  return (
    <Animated.View style={{ transform: [{ scale: escala }] }}>
      <TouchableOpacity style={styles.botonAtacar} onPress={onPress} onPressIn={presionar} onPressOut={soltar}>
        <Text style={styles.botonAtacarTexto}>Atacar</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

/** El panel de combate entero: ronda y turno, la lista de enemigos con su
 * botón de atacar, y las acciones de huir/negociar/objeto/hechizo. Tiene su
 * propio estado de qué sección de acción está desplegada — nada fuera de
 * este panel necesita saberlo. */
export default function PanelCombate({
  combate,
  esMiTurno,
  personajeEnTurnoNombre,
  personaje,
  personajes,
  hechizos,
  inventarioGrupo,
  lanzarDado,
  enviar,
}: Props) {
  const acento = useAcento();
  const [seccionCombate, setSeccionCombate] = useState<'objeto' | 'hechizo' | null>(null);
  const [hechizoElegido, setHechizoElegido] = useState<string | null>(null);
  const [objetoAtaqueElegido, setObjetoAtaqueElegido] = useState<string | null>(null);

  const objetosUsables: (ObjetoInventario & { deGrupo: boolean })[] = [];
  for (const o of personaje.inventario) {
    if (o.efecto?.tipo && EFECTOS_OBJETO_COMBATE.has(o.efecto.tipo)) {
      objetosUsables.push({ ...o, deGrupo: false });
    }
  }
  for (const o of inventarioGrupo) {
    if (o.efecto?.tipo && EFECTOS_OBJETO_COMBATE.has(o.efecto.tipo)) {
      objetosUsables.push({ ...o, deGrupo: true });
    }
  }

  const hechizosCombate: Hechizo[] = [];
  for (const h of hechizos) {
    const loConoce =
      personaje.hechizos_conocidos.includes(h.hechizo_id) || personaje.hechizo_equipado?.hechizo_id === h.hechizo_id;
    if (loConoce && h.efecto && EFECTOS_HECHIZO_COMBATE.has(h.efecto)) {
      hechizosCombate.push(h);
    }
  }

  let hechizo: Hechizo | undefined;
  for (const h of hechizosCombate) {
    if (h.hechizo_id === hechizoElegido) {
      hechizo = h;
    }
  }

  const enemigosVivos = [];
  for (const en of combate.enemigos) {
    if (!en.derrotado) {
      enemigosVivos.push(en);
    }
  }

  // Un personaje muerto de forma permanente no se puede revivir con esto —
  // ver el gasto de maná y el turno en nada.
  const destinatariosElegibles = [];
  for (const p of personajes) {
    if (p.estado !== 'ausente' && p.estado !== 'muerto') {
      destinatariosElegibles.push(p);
    }
  }

  return (
    <View style={{ gap: espacio.sm }}>
      <View style={styles.filaTituloCombate}>
        <MaterialCommunityIcons name="sword-cross" size={14} color={color.textoSecundario} />
        <Text style={styles.tituloSeccion}>COMBATE — RONDA {combate.ronda}</Text>
      </View>
      <View style={[styles.turnoBanner, esMiTurno && [styles.turnoBannerActivo, { borderColor: acento.acentoFuerte, backgroundColor: acento.acentoSuave }]]}>
        <Text style={styles.turnoBannerTexto}>
          {esMiTurno && <Ionicons name="play" size={13} color={color.texto} />}
          {esMiTurno ? ' Es tu turno' : `Esperando a ${personajeEnTurnoNombre ?? 'otro jugador'}…`}
        </Text>
      </View>
      {combate.enemigos.map((en) => (
        <Tarjeta key={en.enemigo_id} acento={color.combate} atenuada={en.derrotado} style={styles.tarjetaEnemigo}>
          <View style={styles.filaEnemigoCabecera}>
            <Text style={styles.enemigoNombre}>
              {en.nombre} {en.derrotado && <Ionicons name="skull-outline" size={13} color={color.textoTenue} />}
              {en.aturdido && (
                <>
                  <Ionicons name="sparkles-outline" size={13} color={color.aviso} /> aturdido
                </>
              )}
            </Text>
            {esMiTurno && !en.derrotado && (
              <BotonAtacar onPress={() => lanzarDado('combate_accion', { accion: 'atacar', enemigo_id: en.enemigo_id })} />
            )}
          </View>
          <BarraRecurso etiqueta="PV" actual={en.vida} maximo={en.vida_max} />
          {esMiTurno && !en.derrotado && (
            <Text style={styles.enemigoSubtexto}>
              <MaterialCommunityIcons name="dice-d20-outline" size={11} color={color.textoTenue} /> Fuerza vs defensa (
              {en.atributos?.defensa ?? 10})
              {!!personaje.arma_equipada?.bono_dano &&
                ` · ${personaje.arma_equipada.nombre} (+${personaje.arma_equipada.bono_dano} daño)`}
            </Text>
          )}
        </Tarjeta>
      ))}
      {esMiTurno && (
        <>
          <View style={{ flexDirection: 'row', gap: espacio.sm }}>
            <View style={{ flex: 1, gap: 4 }}>
              <Boton texto="Huir" variante="secundario" onPress={() => lanzarDado('combate_accion', { accion: 'huir' })} />
              <Text style={styles.accionSubtexto}>
                <MaterialCommunityIcons name="dice-d20-outline" size={11} color={color.textoTenue} /> Agilidad ·
                dificultad {combate.dificultad_huida ?? 12}
              </Text>
            </View>
            <View style={{ flex: 1, gap: 4 }}>
              <Boton
                texto="Negociar"
                variante="secundario"
                onPress={() => lanzarDado('combate_accion', { accion: 'negociar' })}
              />
              <Text style={styles.accionSubtexto}>
                <MaterialCommunityIcons name="dice-d20-outline" size={11} color={color.textoTenue} /> Astucia ·
                dificultad {combate.dificultad_negociacion ?? 13}
              </Text>
            </View>
          </View>

          <View style={{ gap: espacio.sm }}>
            <View style={{ flexDirection: 'row', gap: espacio.sm }}>
              <Boton
                texto={`Usar objeto (${objetosUsables.length})`}
                variante="secundario"
                flex
                onPress={() => {
                  setSeccionCombate(seccionCombate === 'objeto' ? null : 'objeto');
                  setHechizoElegido(null);
                  setObjetoAtaqueElegido(null);
                }}
              />
              <Boton
                texto={`Lanzar hechizo (${hechizosCombate.length})`}
                variante="secundario"
                flex
                onPress={() => {
                  setSeccionCombate(seccionCombate === 'hechizo' ? null : 'hechizo');
                  setHechizoElegido(null);
                  setObjetoAtaqueElegido(null);
                }}
              />
            </View>

            {seccionCombate === 'objeto' && !objetoAtaqueElegido && (
              <View style={styles.panelExpandido}>
                {objetosUsables.length === 0 && (
                  <Text style={styles.requisitoTexto}>No tienes objetos usables en combate.</Text>
                )}
                {objetosUsables.map((o, idx) => (
                  <TouchableOpacity
                    key={`${idx}-${o.objeto_id}`}
                    style={[styles.botonHechizo, { borderColor: acento.acento }]}
                    onPress={() => {
                      if (o.efecto?.tipo === 'dano') {
                        setObjetoAtaqueElegido(o.objeto_id);
                        return;
                      }
                      enviar('combate_accion', { accion: 'objeto', objeto_id: o.objeto_id });
                      setSeccionCombate(null);
                    }}
                  >
                    <Text style={styles.botonHechizoTexto}>
                      {o.nombre} — {textoEfectoObjeto(o.efecto?.tipo, o.efecto?.cantidad ?? 0)}
                      {o.deGrupo ? ' (del grupo)' : ''}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {seccionCombate === 'objeto' && objetoAtaqueElegido && (
              <View style={styles.panelExpandido}>
                <Text style={styles.requisitoTexto}>Elige a qué enemigo usarlo:</Text>
                {enemigosVivos.map((en) => (
                  <TouchableOpacity
                    key={en.enemigo_id}
                    style={[styles.botonHechizo, { borderColor: acento.acento }]}
                    onPress={() => {
                      enviar('combate_accion', {
                        accion: 'objeto',
                        objeto_id: objetoAtaqueElegido,
                        enemigo_id: en.enemigo_id,
                      });
                      setObjetoAtaqueElegido(null);
                      setSeccionCombate(null);
                    }}
                  >
                    <Text style={styles.botonHechizoTexto}>{en.nombre}</Text>
                  </TouchableOpacity>
                ))}
                <TouchableOpacity onPress={() => setObjetoAtaqueElegido(null)}>
                  <Text style={styles.botonApoyoTexto}>‹ Elegir otro objeto</Text>
                </TouchableOpacity>
              </View>
            )}

            {seccionCombate === 'hechizo' && !hechizo && (
              <View style={styles.panelExpandido}>
                {hechizosCombate.length === 0 && (
                  <Text style={styles.requisitoTexto}>No conoces hechizos usables en combate.</Text>
                )}
                {hechizosCombate.map((h) => (
                  <TouchableOpacity
                    key={h.hechizo_id}
                    style={[styles.botonHechizo, { borderColor: acento.acento }]}
                    onPress={() => setHechizoElegido(h.hechizo_id)}
                  >
                    <Text style={styles.botonHechizoTexto}>
                      <MaterialCommunityIcons name="dice-d20-outline" size={13} color={color.textoSecundario} />{' '}
                      {h.nombre} — dificultad {h.dificultad}, coste {h.coste_mana} maná (tienes {personaje.mana_actual})
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {seccionCombate === 'hechizo' && hechizo && (
              <View style={styles.panelExpandido}>
                <Text style={styles.requisitoTexto}>Elige el objetivo de {hechizo.nombre}:</Text>
                {hechizo.efecto === 'restaura_vida_o_mana'
                  ? destinatariosElegibles.map((destino) => (
                      <TouchableOpacity
                        key={destino.id}
                        style={[styles.botonHechizo, { borderColor: acento.acento }]}
                        onPress={() => {
                          lanzarDado('combate_accion', {
                            accion: 'hechizo',
                            hechizo_id: hechizo!.hechizo_id,
                            objetivo_personaje_id: destino.id,
                          });
                          setHechizoElegido(null);
                          setSeccionCombate(null);
                        }}
                      >
                        <Text style={styles.botonHechizoTexto}>{destino.nombre}</Text>
                      </TouchableOpacity>
                    ))
                  : enemigosVivos.map((en) => (
                      <TouchableOpacity
                        key={en.enemigo_id}
                        style={[styles.botonHechizo, { borderColor: acento.acento }]}
                        onPress={() => {
                          lanzarDado('combate_accion', {
                            accion: 'hechizo',
                            hechizo_id: hechizo!.hechizo_id,
                            objetivo_enemigo_id: en.enemigo_id,
                          });
                          setHechizoElegido(null);
                          setSeccionCombate(null);
                        }}
                      >
                        <Text style={styles.botonHechizoTexto}>{en.nombre}</Text>
                      </TouchableOpacity>
                    ))}
                <TouchableOpacity onPress={() => setHechizoElegido(null)}>
                  <Text style={styles.botonApoyoTexto}>‹ Elegir otro hechizo</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  filaTituloCombate: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  tituloSeccion: { color: color.textoSecundario, fontWeight: '700', fontSize: 13, letterSpacing: 0.6 },
  turnoBanner: {
    backgroundColor: color.superficie,
    borderRadius: radio.md,
    paddingVertical: 10,
    paddingHorizontal: espacio.md,
    borderWidth: 1,
    borderColor: color.bordeSutil,
    alignItems: 'center',
  },
  turnoBannerActivo: { backgroundColor: color.acentoSuave, borderColor: color.acentoFuerte },
  turnoBannerTexto: { color: color.texto, fontWeight: '700', fontSize: 14 },
  tarjetaEnemigo: { gap: espacio.xs },
  filaEnemigoCabecera: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  enemigoNombre: { color: color.texto, fontWeight: '600', flex: 1 },
  enemigoSubtexto: { color: color.textoTenue, fontSize: 11 },
  accionSubtexto: { color: color.textoTenue, fontSize: 11, textAlign: 'center' },
  botonAtacar: { backgroundColor: color.peligroFuerte, borderRadius: radio.sm, paddingHorizontal: 12, paddingVertical: 6 },
  botonAtacarTexto: { color: '#fff', fontWeight: '600' },
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
  botonApoyoTexto: { color: '#b8d8ff', fontSize: 13 },
});
