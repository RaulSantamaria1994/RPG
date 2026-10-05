import { useEffect, useRef, useState } from 'react';
import { Animated, FlatList, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { api } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import type { Atributo, Hechizo } from '../../types';

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

const EFECTOS_HECHIZO_COMBATE = new Set(['dano_directo', 'restaura_vida_o_mana', 'aturdir_enemigo']);
const EFECTOS_OBJETO_COMBATE = new Set(['curar_vida', 'curar_mana']);

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

  function lanzarDado(tipo: string, datos: Record<string, unknown> = {}) {
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
    enviar(tipo, datos);
  }

  function salir() {
    reiniciar();
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  }

  return (
    <View style={styles.contenedor}>
      <View style={styles.cabecera}>
        <View style={{ flex: 1 }}>
          <Text style={styles.nombrePersonaje}>{personaje.nombre}</Text>
          <Text style={styles.ficha}>
            PV {personaje.vida_actual}/{personaje.vida_max} · Maná {personaje.mana_actual}/
            {personaje.mana_max}
          </Text>
          <View style={styles.filaAtributos}>
            <Text style={styles.atributoChip}>FUE {personaje.fuerza}</Text>
            <Text style={styles.atributoChip}>AST {personaje.astucia}</Text>
            <Text style={styles.atributoChip}>VOL {personaje.voluntad}</Text>
            <Text style={styles.atributoChip}>AGI {personaje.agilidad}</Text>
          </View>
        </View>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>

      <Animated.View style={[styles.dadoFlotante, { opacity: opacidadDado }]} pointerEvents="none">
        {lanzando ? (
          <Text style={styles.dadoValor}>🎲 {caraDado}…</Text>
        ) : (
          ultimaTirada && (
            <>
              <Text style={styles.dadoValor}>🎲 {ultimaTirada.dado ?? '?'}</Text>
              <Text style={[styles.dadoResultado, ultimaTirada.exito ? styles.exito : styles.fallo]}>
                {ultimaTirada.exito ? 'ÉXITO' : 'FALLO'} (total {ultimaTirada.total ?? '?'})
              </Text>
            </>
          )
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

        {soyAusente && (
          <View style={styles.ausenteBanner}>
            <Text style={styles.ausenteBannerTexto}>
              Estás marcado como ausente: el máster debe reactivarte para que puedas volver a
              actuar.
            </Text>
          </View>
        )}

        {soyMuerto && (
          <View style={styles.muerteBanner}>
            <Text style={styles.muerteBannerTitulo}>Tu historia termina aquí</Text>
            <Text style={styles.muerteBannerTexto}>
              {epilogoPersonal?.texto ??
                'Tu personaje ha caído. El resto del grupo sigue adelante sin ti.'}
            </Text>
          </View>
        )}

        <Text style={styles.nodoTexto}>{nodo?.texto}</Text>

        {nodo?.tipo === 'interactivo' && !enCombate && !soyAusente && !soyMuerto && (
          <View style={{ gap: 8 }}>
            {nodo.palabras_clave?.map((p) => {
              const clave = `${estado?.nodo_actual_id}:${p.texto}`;
              const usada = estado?.palabras_clave_usadas.includes(clave);
              const bloqueada = !!palabrasBloqueadas[clave];
              const deshabilitada = usada || bloqueada;
              const expandida = palabraExpandida === clave;

              const hechizosDisponibles = personaje.hechizos_conocidos.filter(
                (h) => h === p.hechizo_id_alternativo
              );

              const esVotacion = p.modo_interaccion === 'grupal' && !p.dificultad;
              const confirmacion = confirmacionesGrupales[clave];

              const requiereTirada = p.modo_interaccion === 'opuesta' || !!p.dificultad;
              const resumenTirada =
                p.modo_interaccion === 'opuesta'
                  ? `🎲 ${p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} contra un rival`
                  : p.dificultad
                    ? `🎲 ${p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} · dificultad ${p.dificultad}`
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
                <View key={p.texto} style={styles.tarjetaPalabra}>
                  <TouchableOpacity
                    disabled={deshabilitada}
                    style={[styles.botonPalabra, deshabilitada && styles.botonPalabraDeshabilitado]}
                    onPress={() => setPalabraExpandida(expandida ? null : clave)}
                  >
                    <View style={{ flex: 1 }}>
                      <Text
                        style={[
                          styles.botonPalabraTexto,
                          deshabilitada && styles.botonPalabraTextoDeshabilitado,
                        ]}
                      >
                        {p.texto}
                        {esVotacion
                          ? ' (se decide por votación del grupo)'
                          : p.modo_interaccion === 'grupal'
                            ? ' (todos deben confirmar)'
                            : ''}
                      </Text>
                      {!deshabilitada && (
                        <Text style={styles.botonPalabraSubtexto}>{resumenTirada}</Text>
                      )}
                    </View>
                    {usada && <Text style={styles.etiquetaEstado}>agotada</Text>}
                    {bloqueada && !usada && <Text style={styles.etiquetaEstado}>en curso…</Text>}
                  </TouchableOpacity>

                  {esVotacion && votosGrupales && !usada && (
                    <Text style={styles.etiquetaConfirmacion}>
                      Votos: {votosGrupales.votados}/{votosGrupales.total}
                    </Text>
                  )}
                  {!esVotacion && p.modo_interaccion === 'grupal' && confirmacion && !usada && (
                    <Text style={styles.etiquetaConfirmacion}>
                      Confirmados: {confirmacion.confirmados}/{confirmacion.total}
                    </Text>
                  )}

                  {expandida && !deshabilitada && (
                    <View style={styles.panelRequisito}>
                      {p.modo_interaccion === 'opuesta' ? (
                        <Text style={styles.requisitoTexto}>
                          Tirada enfrentada: tu {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} (
                          {p.atributo ? personaje[p.atributo] : '?'}) contra un rival con
                          modificador {p.npc_modificador ?? 0}.
                        </Text>
                      ) : p.dificultad ? (
                        <Text style={styles.requisitoTexto}>
                          Necesitas sacar {p.dificultad} o más tirando 1d20 +{' '}
                          {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'} (tu{' '}
                          {p.atributo ? ETIQUETA_ATRIBUTO[p.atributo] : '?'}: {p.atributo ? personaje[p.atributo] : '?'})
                          {p.modo_interaccion === 'grupal' ? ' — cuenta la mejor tirada del grupo, según la regla.' : '.'}
                          {p.dano_fallo ? ` Si falla, ${p.dano_fallo.cantidad} de daño.` : ''}
                        </Text>
                      ) : (
                        <Text style={styles.requisitoTexto}>
                          Esta acción no requiere tirada: se resuelve al confirmar.
                        </Text>
                      )}

                      <TouchableOpacity style={styles.botonTirar} onPress={() => tirar()}>
                        <Text style={styles.botonTirarTexto}>
                          {requiereTirada ? '🎲 Tirar dado' : 'Confirmar'}
                        </Text>
                      </TouchableOpacity>

                      {p.modo_interaccion === 'apoyo' && (
                        <TouchableOpacity
                          style={styles.botonApoyo}
                          onPress={() => tirar({ rol_apoyo: 'apoyo' })}
                        >
                          <Text style={styles.botonApoyoTexto}>
                            Ayudar con {p.atributo_apoyo ? ETIQUETA_ATRIBUTO[p.atributo_apoyo] : 'otro atributo'} —
                            dificultad {p.dificultad_apoyo ?? p.dificultad ?? 10} (da ventaja a quien
                            actúe)
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
                              🎲 Lanzar {info?.nombre ?? formatearId(h)} (vía mágica) — dificultad{' '}
                              {info?.dificultad ?? '?'}, coste {info?.coste_mana ?? '?'} maná
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  )}
                </View>
              );
            })}
          </View>
        )}

        {estado?.finalizada ? (
          <TouchableOpacity style={styles.botonContinuar} onPress={salir}>
            <Text style={styles.botonContinuarTexto}>Volver al menú</Text>
          </TouchableOpacity>
        ) : (
          nodo?.tipo === 'narrativo' &&
          !soyMuerto && (
            <TouchableOpacity style={styles.botonContinuar} onPress={() => enviar('continuar')}>
              <Text style={styles.botonContinuarTexto}>Continuar</Text>
            </TouchableOpacity>
          )
        )}

        {enCombate && (
          <View style={{ gap: 8 }}>
            <Text style={styles.seccionTitulo}>Combate — ronda {estado!.combate!.ronda}</Text>
            <View style={[styles.turnoBanner, esMiTurno && styles.turnoBannerActivo]}>
              <Text style={styles.turnoBannerTexto}>
                {esMiTurno
                  ? '▶ Es tu turno'
                  : `Esperando a ${personajeEnTurno?.nombre ?? 'otro jugador'}…`}
              </Text>
            </View>
            {estado!.combate!.enemigos.map((en) => (
              <View key={en.enemigo_id} style={styles.tarjetaEnemigo}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.enemigoNombre}>
                    {en.nombre} — {en.vida}/{en.vida_max} PV {en.derrotado ? '☠' : ''}
                    {en.aturdido ? ' 💫 aturdido' : ''}
                  </Text>
                  {esMiTurno && !en.derrotado && (
                    <Text style={styles.enemigoSubtexto}>
                      🎲 Fuerza vs defensa ({en.atributos?.defensa ?? 10})
                    </Text>
                  )}
                </View>
                {esMiTurno && !en.derrotado && (
                  <TouchableOpacity
                    style={styles.botonAtacar}
                    onPress={() =>
                      lanzarDado('combate_accion', { accion: 'atacar', enemigo_id: en.enemigo_id })
                    }
                  >
                    <Text style={styles.botonAtacarTexto}>Atacar</Text>
                  </TouchableOpacity>
                )}
              </View>
            ))}
            {esMiTurno && (
              <>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <View style={{ flex: 1, gap: 4 }}>
                    <TouchableOpacity
                      style={styles.botonSecundario}
                      onPress={() => lanzarDado('combate_accion', { accion: 'huir' })}
                    >
                      <Text style={styles.botonSecundarioTexto}>Huir</Text>
                    </TouchableOpacity>
                    <Text style={styles.accionSubtexto}>
                      🎲 Agilidad · dificultad {estado!.combate!.dificultad_huida ?? 12}
                    </Text>
                  </View>
                  <View style={{ flex: 1, gap: 4 }}>
                    <TouchableOpacity
                      style={styles.botonSecundario}
                      onPress={() => lanzarDado('combate_accion', { accion: 'negociar' })}
                    >
                      <Text style={styles.botonSecundarioTexto}>Negociar</Text>
                    </TouchableOpacity>
                    <Text style={styles.accionSubtexto}>
                      🎲 Astucia · dificultad {estado!.combate!.dificultad_negociacion ?? 13}
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
                    <View style={{ gap: 8 }}>
                      <View style={{ flexDirection: 'row', gap: 8 }}>
                        <TouchableOpacity
                          style={styles.botonSecundario}
                          onPress={() => {
                            setSeccionCombate(seccionCombate === 'objeto' ? null : 'objeto');
                            setHechizoElegido(null);
                          }}
                        >
                          <Text style={styles.botonSecundarioTexto}>
                            Usar objeto ({objetosUsables.length})
                          </Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          style={styles.botonSecundario}
                          onPress={() => {
                            setSeccionCombate(seccionCombate === 'hechizo' ? null : 'hechizo');
                            setHechizoElegido(null);
                          }}
                        >
                          <Text style={styles.botonSecundarioTexto}>
                            Lanzar hechizo ({hechizosCombate.length})
                          </Text>
                        </TouchableOpacity>
                      </View>

                      {seccionCombate === 'objeto' && (
                        <View style={styles.panelRequisito}>
                          {objetosUsables.length === 0 && (
                            <Text style={styles.requisitoTexto}>No tienes objetos usables en combate.</Text>
                          )}
                          {objetosUsables.map((o, idx) => (
                            <TouchableOpacity
                              key={`${idx}-${o.objeto_id}`}
                              style={styles.botonHechizo}
                              onPress={() => {
                                enviar('combate_accion', { accion: 'objeto', objeto_id: o.objeto_id });
                                setSeccionCombate(null);
                              }}
                            >
                              <Text style={styles.botonHechizoTexto}>
                                {o.nombre} — {o.efecto?.tipo === 'curar_vida' ? `+${o.efecto?.cantidad ?? 0} PV` : `+${o.efecto?.cantidad ?? 0} maná`}
                                {o.deGrupo ? ' (del grupo)' : ''}
                              </Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      )}

                      {seccionCombate === 'hechizo' && !hechizo && (
                        <View style={styles.panelRequisito}>
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
                                🎲 {h.nombre} — dificultad {h.dificultad}, coste {h.coste_mana} maná
                                (tienes {personaje.mana_actual})
                              </Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      )}

                      {seccionCombate === 'hechizo' && hechizo && (
                        <View style={styles.panelRequisito}>
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
            <View key={p.clave} style={styles.tarjetaPropuesta}>
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
            </View>
          ))}

        {(estado?.inventario_grupo.length ?? 0) > 0 && (
          <View style={{ gap: 8 }}>
            <Text style={styles.seccionTitulo}>Inventario del grupo</Text>
            <Text style={styles.inventarioTexto}>
              Común para todos: cualquiera puede usar estos objetos, sin pedirlos.
            </Text>
            {estado!.inventario_grupo.map((o, idx) => (
              <View key={`${idx}-${o.objeto_id}`} style={styles.tarjetaObjeto}>
                <Text style={styles.objetoNombre}>{o.nombre}</Text>
              </View>
            ))}
          </View>
        )}

        {personaje.inventario.length > 0 && (
          <View style={{ gap: 8 }}>
            <Text style={styles.seccionTitulo}>Inventario personal</Text>
            {personaje.inventario.map((o) => (
              <View key={o.objeto_id} style={styles.tarjetaObjeto}>
                <TouchableOpacity
                  onPress={() =>
                    setObjetoParaDar(objetoParaDar === o.objeto_id ? null : o.objeto_id)
                  }
                >
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
                      <Text style={styles.inventarioTexto}>No hay a quién dárselo todavía.</Text>
                    )}
                  </View>
                )}
              </View>
            ))}
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
    alignItems: 'flex-start',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#3d2f57',
  },
  nombrePersonaje: { color: '#fff', fontSize: 18, fontWeight: '700' },
  ficha: { color: '#c9b8e0', fontSize: 12 },
  filaAtributos: { flexDirection: 'row', gap: 6, marginTop: 6, flexWrap: 'wrap' },
  atributoChip: {
    color: '#d8cbe8',
    fontSize: 11,
    fontWeight: '600',
    backgroundColor: '#2f2540',
    borderWidth: 1,
    borderColor: '#453a5c',
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    overflow: 'hidden',
  },
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
  ausenteBanner: {
    backgroundColor: '#4a2f2f',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#a05f5f',
  },
  ausenteBannerTexto: { color: '#f0d0d0', fontSize: 13 },
  muerteBanner: {
    backgroundColor: '#1a1420',
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: '#5f4f75',
    gap: 6,
  },
  muerteBannerTitulo: { color: '#c9b8e0', fontSize: 15, fontWeight: '700' },
  muerteBannerTexto: { color: '#a390bd', fontSize: 13, lineHeight: 19 },
  nodoTexto: { color: '#f3e9ff', fontSize: 16, lineHeight: 22 },
  panelRequisito: {
    backgroundColor: '#1f1830',
    borderRadius: 8,
    padding: 10,
    marginTop: 4,
    gap: 8,
    borderWidth: 1,
    borderColor: '#453a5c',
  },
  requisitoTexto: { color: '#d8cbe8', fontSize: 13, lineHeight: 18 },
  botonTirar: {
    backgroundColor: '#6b3fa0',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  botonTirarTexto: { color: '#fff', fontWeight: '700' },
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
  botonPalabraSubtexto: { color: '#b39fd6', fontSize: 12, marginTop: 3 },
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
  turnoBanner: {
    backgroundColor: '#241b33',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: '#453a5c',
    alignItems: 'center',
  },
  turnoBannerActivo: { backgroundColor: '#3d2360', borderColor: '#a97fe0' },
  turnoBannerTexto: { color: '#f3e9ff', fontWeight: '700', fontSize: 14 },
  tarjetaEnemigo: {
    backgroundColor: '#2f1f1f',
    borderRadius: 8,
    padding: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  enemigoNombre: { color: '#f3d9d9' },
  enemigoSubtexto: { color: '#d6a9a9', fontSize: 11, marginTop: 2 },
  accionSubtexto: { color: '#b39fd6', fontSize: 11, textAlign: 'center' },
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
  etiquetaConfirmacion: { color: '#e0c27f', fontSize: 12, marginLeft: 4 },
  botonApoyo: {
    backgroundColor: '#1f2b45',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#6f9fd0',
    marginLeft: 12,
  },
  botonApoyoTexto: { color: '#b8d8ff', fontSize: 13 },
  tarjetaPropuesta: {
    backgroundColor: '#2b2a1f',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#d0b86f',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  propuestaTexto: { color: '#f0e6c9', flex: 1, marginRight: 8 },
  botonAceptar: { backgroundColor: '#6b9f3f', borderRadius: 6, paddingHorizontal: 12, paddingVertical: 8 },
  botonAceptarTexto: { color: '#fff', fontWeight: '600' },
  tarjetaObjeto: {
    backgroundColor: '#241b33',
    borderRadius: 8,
    padding: 10,
  },
  objetoNombre: { color: '#fff' },
  filaDestinatarios: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  botonDestinatario: {
    backgroundColor: '#2f2540',
    borderWidth: 1,
    borderColor: '#6b3fa0',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  botonDestinatarioTexto: { color: '#fff', fontSize: 12 },
  panelLog: {
    height: 100,
    borderTopWidth: 1,
    borderTopColor: '#3d2f57',
    padding: 10,
  },
  logTexto: { color: '#a390bd', fontSize: 11, marginBottom: 2 },
});
