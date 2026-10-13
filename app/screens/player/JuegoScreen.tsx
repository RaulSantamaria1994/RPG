import { useEffect, useRef, useState } from 'react';
import { Animated, FlatList, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { Boton, BarraRecurso, IconoEvento, Insignia, Tarjeta } from '../../components';
import { api } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { Atributo, Hechizo } from '../../types';
import { color, espacio, radio, tipo } from '../../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'JugadorJuego'>;

function formatearId(id: string): string {
  return id.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

const ETIQUETA_ATRIBUTO: Record<Atributo, string> = {
  fuerza: 'Fuerza',
  astucia: 'Astucia',
  voluntad: 'Voluntad',
  agilidad: 'Agilidad',
};

const COLOR_TIPO_NODO: Record<string, string> = {
  narrativo: color.narrativo,
  interactivo: color.interactivo,
  combate: color.combate,
};

const EFECTOS_HECHIZO_COMBATE = new Set(['dano_directo', 'restaura_vida_o_mana', 'aturdir_enemigo']);
const EFECTOS_OBJETO_COMBATE = new Set(['curar_vida', 'curar_mana', 'dano']);

export default function JuegoScreen({ navigation }: Props) {
  const sala = useSalaStore((s) => s.sala);
  const personaje = useSalaStore((s) => s.personaje);
  const personajes = useSalaStore((s) => s.personajes);
  const estado = useSalaStore((s) => s.estado);
  const log = useSalaStore((s) => s.log);
  const palabrasBloqueadas = useSalaStore((s) => s.palabrasBloqueadas);
  const confirmacionesGrupales = useSalaStore((s) => s.confirmacionesGrupales);
  const votosGrupales = useSalaStore((s) => s.votosGrupales);
  const propuestasIntercambio = useSalaStore((s) => s.propuestasIntercambio);
  const ultimaTirada = useSalaStore((s) => s.ultimaTirada);
  const epilogoPersonal = useSalaStore((s) => s.epilogoPersonal);
  const conectar = useSalaStore((s) => s.conectar);
  const desconectar = useSalaStore((s) => s.desconectar);
  const enviar = useSalaStore((s) => s.enviar);
  const reiniciar = useSalaStore((s) => s.reiniciar);

  const [objetoParaDar, setObjetoParaDar] = useState<string | null>(null);
  const [palabraExpandida, setPalabraExpandida] = useState<string | null>(null);
  const [hechizos, setHechizos] = useState<Hechizo[]>([]);
  const [seccionCombate, setSeccionCombate] = useState<'objeto' | 'hechizo' | null>(null);
  const [hechizoElegido, setHechizoElegido] = useState<string | null>(null);
  const [objetoAtaqueElegido, setObjetoAtaqueElegido] = useState<string | null>(null);
  const [lanzando, setLanzando] = useState(false);
  const [caraDado, setCaraDado] = useState(20);

  const opacidadDado = useRef(new Animated.Value(0)).current;
  const intervaloDado = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutDado = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    conectar();
    return () => desconectar();
  }, []);

  useEffect(() => {
    if (sala) {
      api.listarHechizos(sala.codigo).then(setHechizos).catch(() => {});
    }
  }, [sala]);

  useEffect(() => {
    if (!ultimaTirada) return;
    if (intervaloDado.current) {
      clearInterval(intervaloDado.current);
      intervaloDado.current = null;
    }
    if (timeoutDado.current) {
      clearTimeout(timeoutDado.current);
      timeoutDado.current = null;
    }
    setLanzando(false);
    opacidadDado.setValue(1);
    Animated.timing(opacidadDado, { toValue: 0, duration: 2500, useNativeDriver: true }).start();
  }, [ultimaTirada]);

  useEffect(() => {
    return () => {
      if (intervaloDado.current) clearInterval(intervaloDado.current);
      if (timeoutDado.current) clearTimeout(timeoutDado.current);
    };
  }, []);

  useEffect(() => {
    if (!sala || !personaje) {
      navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
    }
  }, [sala, personaje]);

  if (!sala || !personaje) return null;

  const nodo = estado?.nodo;
  const enCombate = estado?.fase === 'combate' && estado.combate;
  const esMiTurno =
    enCombate && estado!.combate!.orden_iniciativa[estado!.combate!.turno_index] === `personaje:${personaje.id}`;
  const soyAusente = personaje.estado === 'ausente';
  const soyMuerto = personaje.estado === 'muerto';

  const idEnTurno = enCombate
    ? estado!.combate!.orden_iniciativa[estado!.combate!.turno_index]?.split(':')[1]
    : null;
  const personajeEnTurno =
    idEnTurno === personaje.id ? personaje : personajes.find((p) => p.id === idEnTurno);

  function lanzarDado(tipoAccion: string, datos: Record<string, unknown> = {}) {
    setLanzando(true);
    setCaraDado(1 + Math.floor(Math.random() * 20));
    opacidadDado.stopAnimation();
    opacidadDado.setValue(1);
    if (intervaloDado.current) clearInterval(intervaloDado.current);
    intervaloDado.current = setInterval(() => {
      setCaraDado(1 + Math.floor(Math.random() * 20));
    }, 80);
    if (timeoutDado.current) clearTimeout(timeoutDado.current);
    timeoutDado.current = setTimeout(() => {
      if (intervaloDado.current) {
        clearInterval(intervaloDado.current);
        intervaloDado.current = null;
      }
      setLanzando(false);
    }, 4000);
    enviar(tipoAccion, datos);
  }

  function salir() {
    reiniciar();
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  }

  return (
    <View style={styles.contenedor}>
      <View style={styles.cabecera}>
        <View style={{ flex: 1, gap: 6 }}>
          <Text style={styles.nombrePersonaje}>{personaje.nombre}</Text>
          <BarraRecurso etiqueta="PV" actual={personaje.vida_actual} maximo={personaje.vida_max} />
          <BarraRecurso etiqueta="Maná" actual={personaje.mana_actual} maximo={personaje.mana_max} sinAlerta />
          <View style={styles.filaAtributos}>
            {(Object.keys(ETIQUETA_ATRIBUTO) as Atributo[]).map((a) => (
              <View key={a} style={styles.atributoChip}>
                <Text style={styles.atributoChipTexto}>
                  {ETIQUETA_ATRIBUTO[a].slice(0, 3).toUpperCase()} {personaje[a]}
                </Text>
              </View>
            ))}
          </View>
        </View>
        <View style={styles.accionesCabecera}>
          <TouchableOpacity onPress={() => navigation.navigate('Diario')} hitSlop={8} testID="boton-diario">
            <Ionicons name="bookmark-outline" size={22} color={color.textoSecundario} />
            {(estado?.diario?.length ?? 0) > 0 && (
              <View style={styles.insigniaContador}>
                <Text style={styles.insigniaContadorTexto}>{estado?.diario?.length}</Text>
              </View>
            )}
          </TouchableOpacity>
          <TouchableOpacity onPress={() => navigation.navigate('Ayuda')} hitSlop={8} testID="boton-ayuda">
            <Ionicons name="help-circle-outline" size={22} color={color.textoSecundario} />
          </TouchableOpacity>
          <TouchableOpacity onPress={salir}>
            <Text style={styles.salir}>Salir</Text>
          </TouchableOpacity>
        </View>
      </View>

      <Animated.View style={[styles.dadoFlotante, { opacity: opacidadDado }]} pointerEvents="none">
        {lanzando ? (
          <View style={styles.filaDado}>
            <MaterialCommunityIcons name="dice-d20" size={26} color={color.texto} />
            <Text style={styles.dadoValor}>{caraDado}</Text>
          </View>
        ) : (
          ultimaTirada && (
            <>
              <View style={styles.filaDado}>
                <MaterialCommunityIcons name="dice-d20" size={26} color={color.texto} />
                <Text style={styles.dadoValor}>{ultimaTirada.dado ?? '?'}</Text>
              </View>
              <Text style={[styles.dadoResultado, ultimaTirada.exito ? styles.exito : styles.fallo]}>
                {ultimaTirada.exito ? 'ÉXITO' : 'FALLO'} · total {ultimaTirada.total ?? '?'}
              </Text>
            </>
          )
        )}
      </Animated.View>

      <ScrollView contentContainerStyle={{ padding: espacio.lg, gap: espacio.md }}>
        {estado?.finalizada && (
          <View style={styles.finalBanner}>
            <Text style={styles.finalBannerTexto}>Fin de la historia — final: {estado.tipo_final}</Text>
          </View>
        )}

        {soyAusente && (
          <View style={styles.ausenteBanner}>
            <Text style={styles.ausenteBannerTexto}>
              Estás marcado como ausente: el máster debe reactivarte para que puedas volver a actuar.
            </Text>
          </View>
        )}

        {soyMuerto && (
          <View style={styles.muerteBanner}>
            <Text style={styles.muerteBannerTitulo}>Tu historia termina aquí</Text>
            <Text style={styles.muerteBannerTexto}>
              {epilogoPersonal?.texto ?? 'Tu personaje ha caído. El resto del grupo sigue adelante sin ti.'}
            </Text>
          </View>
        )}

        <Text style={[styles.nodoTexto, nodo && { borderLeftColor: COLOR_TIPO_NODO[nodo.tipo] ?? color.borde }]}>
          {nodo?.texto}
        </Text>

        {nodo?.tipo === 'interactivo' && !enCombate && !soyAusente && !soyMuerto && (
          <View style={{ gap: espacio.sm }}>
            {nodo.palabras_clave?.map((p) => {
              const clave = `${estado?.nodo_actual_id}:${p.texto}`;
              const usada = estado?.palabras_clave_usadas.includes(clave);
              const bloqueada = !!palabrasBloqueadas[clave];
              const deshabilitada = usada || bloqueada;
              const expandida = palabraExpandida === clave;

              const hechizosDisponibles = personaje.hechizos_conocidos.filter((h) => {
                if (h === p.hechizo_id_alternativo) return true;
                if (!p.categoria_hechizo_alternativa) return false;
                return hechizos.find((x) => x.hechizo_id === h)?.categoria === p.categoria_hechizo_alternativa;
              });

              const esVotacion = p.modo_interaccion === 'grupal' && !p.dificultad;
              const confirmacion = confirmacionesGrupales[clave];

              const requiereTirada = p.modo_interaccion === 'opuesta' || !!p.dificultad;
              const resumenTirada =
                p.modo_interaccion === 'opuesta'
                  ? `${p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} contra un rival`
                  : p.dificultad
                    ? `${p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} · dificultad ${p.dificultad}`
                    : esVotacion
                      ? 'Sin tirada — gana la opción más votada por el grupo'
                      : 'Sin tirada — se resuelve al confirmar';

              function tirar(datosExtra: Record<string, unknown> = {}) {
                const conDado =
                  requiereTirada || datosExtra.via === 'hechizo' || datosExtra.rol_apoyo === 'apoyo';
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
                            {esVotacion
                              ? ' (vota el grupo)'
                              : p.modo_interaccion === 'grupal'
                                ? ' (confirma todo el grupo)'
                                : ''}
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
                        <Insignia texto={`Votos: ${votosGrupales.votados}/${votosGrupales.total}`} tono="aviso" />
                      )}
                      {!esVotacion && p.modo_interaccion === 'grupal' && confirmacion && !usada && (
                        <Insignia
                          texto={`Confirmados: ${confirmacion.confirmados}/${confirmacion.total}`}
                          tono="aviso"
                        />
                      )}

                      {expandida && !deshabilitada && (
                        <View style={styles.panelExpandido}>
                          {p.modo_interaccion === 'opuesta' ? (
                            <Text style={styles.requisitoTexto}>
                              Tirada enfrentada: tu {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} (
                              {p.atributo ? personaje[p.atributo] : '?'}) contra un rival con modificador{' '}
                              {p.npc_modificador ?? 0}.
                            </Text>
                          ) : p.dificultad ? (
                            <Text style={styles.requisitoTexto}>
                              Necesitas sacar {p.dificultad} o más tirando 1d20 +{' '}
                              {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} (tu{' '}
                              {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'}:{' '}
                              {p.atributo ? personaje[p.atributo] : '?'})
                              {p.modo_interaccion === 'grupal'
                                ? ' — cuenta la mejor tirada del grupo, según la regla.'
                                : '.'}
                              {p.dano_fallo ? ` Si falla, ${p.dano_fallo.cantidad} de daño.` : ''}
                            </Text>
                          ) : (
                            <Text style={styles.requisitoTexto}>
                              Esta acción no requiere tirada: se resuelve al confirmar.
                            </Text>
                          )}

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
                            <TouchableOpacity
                              style={styles.botonApoyo}
                              onPress={() => tirar({ rol_apoyo: 'apoyo' })}
                            >
                              <Text style={styles.botonApoyoTexto}>
                                Ayudar con{' '}
                                {p.atributo_apoyo ? ETIQUETA_ATRIBUTO[p.atributo_apoyo] : 'otro atributo'} —
                                dificultad {p.dificultad_apoyo ?? p.dificultad ?? 10} (da ventaja a quien actúe)
                              </Text>
                            </TouchableOpacity>
                          )}

                          {hechizosDisponibles.map((h) => {
                            const info = hechizos.find((x) => x.hechizo_id === h);
                            return (
                              <TouchableOpacity
                                key={h}
                                style={styles.botonHechizo}
                                onPress={() => tirar({ via: 'hechizo', hechizo_id: h })}
                              >
                                <Text style={styles.botonHechizoTexto}>
                                  <MaterialCommunityIcons name="dice-d20-outline" size={13} color={color.textoSecundario} />{' '}
                                  Lanzar {info?.nombre ?? formatearId(h)} (vía mágica) — dificultad{' '}
                                  {info?.dificultad ?? '?'}, coste {info?.coste_mana ?? '?'} maná
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
        )}

        {estado?.finalizada ? (
          <Boton texto="Volver al menú" onPress={salir} />
        ) : (
          nodo?.tipo === 'narrativo' &&
          !soyMuerto && <Boton texto="Continuar" onPress={() => enviar('continuar')} />
        )}

        {enCombate && (
          <View style={{ gap: espacio.sm }}>
            <View style={styles.filaTituloCombate}>
              <MaterialCommunityIcons name="sword-cross" size={14} color={color.textoSecundario} />
              <Text style={styles.tituloSeccion}>COMBATE — RONDA {estado!.combate!.ronda}</Text>
            </View>
            <View style={[styles.turnoBanner, esMiTurno && styles.turnoBannerActivo]}>
              <Text style={styles.turnoBannerTexto}>
                {esMiTurno && <Ionicons name="play" size={13} color={color.texto} />}
                {esMiTurno ? ' Es tu turno' : `Esperando a ${personajeEnTurno?.nombre ?? 'otro jugador'}…`}
              </Text>
            </View>
            {estado!.combate!.enemigos.map((en) => (
              <Tarjeta key={en.enemigo_id} acento={color.combate} atenuada={en.derrotado} style={styles.tarjetaEnemigo}>
                <View style={styles.filaEnemigoCabecera}>
                  <Text style={styles.enemigoNombre}>
                    {en.nombre}{' '}
                    {en.derrotado && <Ionicons name="skull-outline" size={13} color={color.textoTenue} />}
                    {en.aturdido && (
                      <>
                        <Ionicons name="sparkles-outline" size={13} color={color.aviso} /> aturdido
                      </>
                    )}
                  </Text>
                  {esMiTurno && !en.derrotado && (
                    <TouchableOpacity
                      style={styles.botonAtacar}
                      onPress={() => lanzarDado('combate_accion', { accion: 'atacar', enemigo_id: en.enemigo_id })}
                    >
                      <Text style={styles.botonAtacarTexto}>Atacar</Text>
                    </TouchableOpacity>
                  )}
                </View>
                <BarraRecurso etiqueta="PV" actual={en.vida} maximo={en.vida_max} />
                {esMiTurno && !en.derrotado && (
                  <Text style={styles.enemigoSubtexto}>
                    <MaterialCommunityIcons name="dice-d20-outline" size={11} color={color.textoTenue} /> Fuerza vs
                    defensa ({en.atributos?.defensa ?? 10})
                  </Text>
                )}
              </Tarjeta>
            ))}
            {esMiTurno && (
              <>
                <View style={{ flexDirection: 'row', gap: espacio.sm }}>
                  <View style={{ flex: 1, gap: 4 }}>
                    <Boton
                      texto="Huir"
                      variante="secundario"
                      onPress={() => lanzarDado('combate_accion', { accion: 'huir' })}
                    />
                    <Text style={styles.accionSubtexto}>
                      <MaterialCommunityIcons name="dice-d20-outline" size={11} color={color.textoTenue} /> Agilidad ·
                      dificultad {estado!.combate!.dificultad_huida ?? 12}
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
                      dificultad {estado!.combate!.dificultad_negociacion ?? 13}
                    </Text>
                  </View>
                </View>

                {(() => {
                  const objetosUsables = [
                    ...personaje.inventario.map((o) => ({ ...o, deGrupo: false })),
                    ...(estado?.inventario_grupo ?? []).map((o) => ({ ...o, deGrupo: true })),
                  ].filter((o) => o.efecto?.tipo && EFECTOS_OBJETO_COMBATE.has(o.efecto.tipo));
                  const hechizosCombate = hechizos.filter(
                    (h) =>
                      personaje.hechizos_conocidos.includes(h.hechizo_id) &&
                      h.efecto &&
                      EFECTOS_HECHIZO_COMBATE.has(h.efecto)
                  );
                  const hechizo = hechizosCombate.find((h) => h.hechizo_id === hechizoElegido);

                  return (
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
                              style={styles.botonHechizo}
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
                                {o.nombre} —{' '}
                                {o.efecto?.tipo === 'curar_vida'
                                  ? `+${o.efecto?.cantidad ?? 0} PV`
                                  : o.efecto?.tipo === 'curar_mana'
                                    ? `+${o.efecto?.cantidad ?? 0} maná`
                                    : `${o.efecto?.cantidad ?? 0} de daño`}
                                {o.deGrupo ? ' (del grupo)' : ''}
                              </Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      )}

                      {seccionCombate === 'objeto' && objetoAtaqueElegido && (
                        <View style={styles.panelExpandido}>
                          <Text style={styles.requisitoTexto}>Elige a qué enemigo usarlo:</Text>
                          {estado!.combate!.enemigos
                            .filter((en) => !en.derrotado)
                            .map((en) => (
                              <TouchableOpacity
                                key={en.enemigo_id}
                                style={styles.botonHechizo}
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
                              style={styles.botonHechizo}
                              onPress={() => setHechizoElegido(h.hechizo_id)}
                            >
                              <Text style={styles.botonHechizoTexto}>
                                <MaterialCommunityIcons name="dice-d20-outline" size={13} color={color.textoSecundario} />{' '}
                                {h.nombre} — dificultad {h.dificultad}, coste {h.coste_mana} maná (tienes{' '}
                                {personaje.mana_actual})
                              </Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      )}

                      {seccionCombate === 'hechizo' && hechizo && (
                        <View style={styles.panelExpandido}>
                          <Text style={styles.requisitoTexto}>Elige el objetivo de {hechizo.nombre}:</Text>
                          {hechizo.efecto === 'restaura_vida_o_mana'
                            ? personajes
                                .filter((p) => p.estado !== 'ausente')
                                .map((destino) => (
                                  <TouchableOpacity
                                    key={destino.id}
                                    style={styles.botonHechizo}
                                    onPress={() => {
                                      lanzarDado('combate_accion', {
                                        accion: 'hechizo',
                                        hechizo_id: hechizo.hechizo_id,
                                        objetivo_personaje_id: destino.id,
                                      });
                                      setHechizoElegido(null);
                                      setSeccionCombate(null);
                                    }}
                                  >
                                    <Text style={styles.botonHechizoTexto}>{destino.nombre}</Text>
                                  </TouchableOpacity>
                                ))
                            : estado!.combate!.enemigos
                                .filter((en) => !en.derrotado)
                                .map((en) => (
                                  <TouchableOpacity
                                    key={en.enemigo_id}
                                    style={styles.botonHechizo}
                                    onPress={() => {
                                      lanzarDado('combate_accion', {
                                        accion: 'hechizo',
                                        hechizo_id: hechizo.hechizo_id,
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
                  );
                })()}
              </>
            )}
          </View>
        )}

        {propuestasIntercambio
          .filter((p) => p.destino_personaje_id === personaje.id)
          .map((p) => (
            <Tarjeta key={p.clave} acento={color.aviso} style={styles.tarjetaPropuesta}>
              <Text style={styles.propuestaTexto}>
                {p.origen_personaje_nombre} te ofrece "{p.objeto_nombre}"
              </Text>
              <TouchableOpacity
                style={styles.botonAceptar}
                onPress={() =>
                  enviar('intercambio_confirmar', {
                    origen_personaje_id: p.origen_personaje_id,
                    objeto_id: p.objeto_id,
                  })
                }
              >
                <Text style={styles.botonAceptarTexto}>Aceptar</Text>
              </TouchableOpacity>
            </Tarjeta>
          ))}

        {(estado?.inventario_grupo.length ?? 0) > 0 && (
          <View style={{ gap: espacio.sm }}>
            <Text style={styles.tituloSeccion}>INVENTARIO DEL GRUPO</Text>
            <Text style={styles.notaInventario}>
              Común para todos: cualquiera puede usar estos objetos, sin pedirlos.
            </Text>
            {estado!.inventario_grupo.map((o, idx) => (
              <Tarjeta key={`${idx}-${o.objeto_id}`} acento={color.acento} style={{ paddingVertical: espacio.sm }}>
                <Text style={styles.objetoNombre}>{o.nombre}</Text>
              </Tarjeta>
            ))}
          </View>
        )}

        {personaje.inventario.length > 0 && (
          <View style={{ gap: espacio.sm }}>
            <Text style={styles.tituloSeccion}>INVENTARIO PERSONAL</Text>
            {personaje.inventario.map((o) => (
              <Tarjeta key={o.objeto_id} style={{ paddingVertical: espacio.sm }}>
                <TouchableOpacity onPress={() => setObjetoParaDar(objetoParaDar === o.objeto_id ? null : o.objeto_id)}>
                  <Text style={styles.objetoNombre}>
                    {o.nombre} {objetoParaDar === o.objeto_id ? '▲' : '▼ dar…'}
                  </Text>
                </TouchableOpacity>
                {objetoParaDar === o.objeto_id && (
                  <View style={styles.filaDestinatarios}>
                    {personajes
                      .filter((otro) => otro.id !== personaje.id)
                      .map((otro) => (
                        <TouchableOpacity
                          key={otro.id}
                          style={styles.botonDestinatario}
                          onPress={() => {
                            enviar('intercambio_proponer', {
                              objeto_id: o.objeto_id,
                              destino_personaje_id: otro.id,
                            });
                            setObjetoParaDar(null);
                          }}
                        >
                          <Text style={styles.botonDestinatarioTexto}>{otro.nombre}</Text>
                        </TouchableOpacity>
                      ))}
                    {personajes.length <= 1 && (
                      <Text style={styles.notaInventario}>No hay a quién dárselo todavía.</Text>
                    )}
                  </View>
                )}
              </Tarjeta>
            ))}
          </View>
        )}
      </ScrollView>

      <View style={styles.panelLog}>
        <FlatList
          data={log.slice(0, 20)}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <Text style={styles.logTexto}>
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
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: color.fondo },
  cabecera: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: espacio.lg,
    borderBottomWidth: 1,
    borderBottomColor: color.borde,
    gap: espacio.sm,
  },
  nombrePersonaje: { ...tipo.subtitulo, fontSize: 18 },
  filaAtributos: { flexDirection: 'row', gap: 6, marginTop: 2, flexWrap: 'wrap' },
  atributoChip: {
    backgroundColor: color.superficieAlt,
    borderWidth: 1,
    borderColor: color.bordeSutil,
    borderRadius: radio.sm,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  atributoChipTexto: { color: color.textoSecundario, fontSize: 11, fontWeight: '600' },
  accionesCabecera: { flexDirection: 'row', alignItems: 'center', gap: espacio.md },
  salir: { color: color.peligro, fontWeight: '600' },
  insigniaContador: {
    position: 'absolute',
    top: -4,
    right: -6,
    minWidth: 15,
    height: 15,
    borderRadius: radio.pill,
    backgroundColor: color.acentoFuerte,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 3,
  },
  insigniaContadorTexto: { color: color.textoSobreAcento, fontSize: 9, fontWeight: '700' },
  dadoFlotante: {
    position: 'absolute',
    top: 120,
    alignSelf: 'center',
    backgroundColor: color.fondoElevado,
    borderRadius: radio.lg,
    padding: espacio.md,
    alignItems: 'center',
    zIndex: 10,
    borderWidth: 1,
    borderColor: color.acento,
    shadowColor: '#000',
    shadowOpacity: 0.4,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  filaDado: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  dadoValor: { fontSize: 30, color: color.texto, fontWeight: '700' },
  dadoResultado: { fontSize: 13, marginTop: 4, fontWeight: '700' },
  exito: { color: color.exito },
  fallo: { color: color.peligro },
  finalBanner: { backgroundColor: color.acentoSuave, padding: espacio.md, borderRadius: radio.md, borderWidth: 1, borderColor: color.acento },
  finalBannerTexto: { color: color.texto, fontWeight: '600' },
  ausenteBanner: {
    backgroundColor: color.peligroSuave,
    borderRadius: radio.md,
    padding: espacio.md,
    borderWidth: 1,
    borderColor: color.peligro,
  },
  ausenteBannerTexto: { color: '#f0d0d0', fontSize: 13 },
  muerteBanner: {
    backgroundColor: color.fondoElevado,
    borderRadius: radio.md,
    padding: espacio.md,
    borderWidth: 1,
    borderColor: color.bordeSutil,
    gap: 6,
  },
  muerteBannerTitulo: { ...tipo.subtitulo, fontSize: 15 },
  muerteBannerTexto: { color: color.textoSecundario, fontSize: 13, lineHeight: 19 },
  nodoTexto: {
    color: color.texto,
    fontSize: 16,
    lineHeight: 23,
    borderLeftWidth: 3,
    borderLeftColor: color.borde,
    paddingLeft: espacio.md,
  },
  tituloSeccion: { ...tipo.seccion },
  filaTituloCombate: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  tarjetaPalabra: { gap: espacio.xs },
  filaPalabraCabecera: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: espacio.sm },
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
  notaInventario: { color: color.textoSecundario, fontSize: 12 },
  botonApoyo: {
    backgroundColor: color.superficie,
    borderRadius: radio.md,
    padding: 10,
    borderWidth: 1,
    borderColor: '#6f9fd0',
  },
  botonApoyoTexto: { color: '#b8d8ff', fontSize: 13 },
  tarjetaPropuesta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  propuestaTexto: { color: color.texto, flex: 1, marginRight: espacio.sm, fontSize: 13 },
  botonAceptar: { backgroundColor: color.exito, borderRadius: radio.sm, paddingHorizontal: 12, paddingVertical: 8 },
  botonAceptarTexto: { color: '#17301f', fontWeight: '700' },
  objetoNombre: { color: color.texto },
  filaDestinatarios: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.sm, marginTop: espacio.sm },
  botonDestinatario: {
    backgroundColor: color.superficieAlt,
    borderWidth: 1,
    borderColor: color.acento,
    borderRadius: radio.sm,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  botonDestinatarioTexto: { color: color.texto, fontSize: 12 },
  panelLog: {
    height: 100,
    borderTopWidth: 1,
    borderTopColor: color.borde,
    padding: espacio.sm,
  },
  logTexto: { color: color.textoTenue, fontSize: 11, marginBottom: 2 },
});
