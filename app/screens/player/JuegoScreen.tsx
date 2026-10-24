import { useEffect, useRef, useState } from 'react';
import { Animated, FlatList, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../navigation/types';
import { Boton, BarraRecurso, EfectoCombate, IconoEvento, IndicadorConexion, Insignia, Tarjeta, TexturaGrano } from '../../components';
import { api } from '../../services/api';
import { useSalaStore } from '../../store/salaStore';
import { useAcento } from '../../store/configStore';
import type { Atributo, Hechizo } from '../../types';
import { color, espacio, radio, tipo } from '../../theme';
import { ETIQUETA_ATRIBUTO } from './juego/comun';
import PanelInteraccion from './juego/PanelInteraccion';
import PanelCombate from './juego/PanelCombate';
import PanelIntercambio from './juego/PanelIntercambio';

type Props = NativeStackScreenProps<RootStackParamList, 'JugadorJuego'>;

const COLOR_TIPO_NODO: Record<string, string> = {
  narrativo: color.narrativo,
  interactivo: color.interactivo,
  combate: color.combate,
};

export default function JuegoScreen({ navigation }: Props) {
  const insets = useSafeAreaInsets();
  const sala = useSalaStore((s) => s.sala);
  const personaje = useSalaStore((s) => s.personaje);
  const personajes = useSalaStore((s) => s.personajes);
  const estado = useSalaStore((s) => s.estado);
  const conectado = useSalaStore((s) => s.conectado);
  const reintentandoConexion = useSalaStore((s) => s.reintentandoConexion);
  const log = useSalaStore((s) => s.log);
  const palabrasBloqueadas = useSalaStore((s) => s.palabrasBloqueadas);
  const confirmacionesGrupales = useSalaStore((s) => s.confirmacionesGrupales);
  const votosGrupales = useSalaStore((s) => s.votosGrupales);
  const propuestasIntercambio = useSalaStore((s) => s.propuestasIntercambio);
  const ultimaTirada = useSalaStore((s) => s.ultimaTirada);
  const ultimaAccionCombate = useSalaStore((s) => s.ultimaAccionCombate);
  const epilogoPersonal = useSalaStore((s) => s.epilogoPersonal);
  const conectar = useSalaStore((s) => s.conectar);
  const desconectar = useSalaStore((s) => s.desconectar);
  const enviar = useSalaStore((s) => s.enviar);
  const reiniciar = useSalaStore((s) => s.reiniciar);
  const acento = useAcento();
  // Los estilos de arriba son estáticos (calculados una vez al cargar el
  // módulo); los que dependen del acento elegible en Opciones se recalculan
  // aquí en cada render y se mezclan en el JSX, para que el cambio de color
  // se vea al instante sin tener que convertir toda la hoja de estilos.
  const estilosAcento = {
    insigniaContador: { backgroundColor: acento.acentoFuerte },
    dadoFlotante: { borderColor: acento.acento },
    finalBanner: { backgroundColor: acento.acentoSuave, borderColor: acento.acento },
  };

  const [hechizos, setHechizos] = useState<Hechizo[]>([]);
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

  const faltanJugadores = Math.max(0, sala.min_jugadores - personajes.length);
  const nodo = estado?.nodo;
  const enCombate = estado?.fase === 'combate' && estado.combate;
  const esMiTurno =
    enCombate && estado!.combate!.orden_iniciativa[estado!.combate!.turno_index] === `personaje:${personaje.id}`;
  const soyAusente = personaje.estado === 'ausente';
  const soyMuerto = personaje.estado === 'muerto';

  const companeros: typeof personajes = [];
  for (const p of personajes) {
    if (p.id !== personaje.id) {
      companeros.push(p);
    }
  }

  const propuestasParaMi = [];
  for (const p of propuestasIntercambio) {
    if (p.destino_personaje_id === personaje.id) {
      propuestasParaMi.push(p);
    }
  }

  const idEnTurno = enCombate
    ? estado!.combate!.orden_iniciativa[estado!.combate!.turno_index]?.split(':')[1]
    : null;
  let personajeEnTurno: typeof personaje | undefined;
  if (idEnTurno === personaje.id) {
    personajeEnTurno = personaje;
  } else {
    for (const p of personajes) {
      if (p.id === idEnTurno) {
        personajeEnTurno = p;
      }
    }
  }

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
    <View style={[styles.contenedor, { paddingTop: insets.top }]}>
      <Image source={require('../../assets/fondo-archivo.jpg')} style={styles.fondoImagen} resizeMode="cover" />
      <View style={styles.fondoVelo} />
      <IndicadorConexion conectado={conectado} reintentando={reintentandoConexion} />
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
              <View style={[styles.insigniaContador, estilosAcento.insigniaContador]}>
                <Text style={styles.insigniaContadorTexto}>{estado?.diario?.length}</Text>
              </View>
            )}
          </TouchableOpacity>
          <TouchableOpacity onPress={() => navigation.navigate('Equipo')} hitSlop={8} testID="boton-equipo">
            <MaterialCommunityIcons name="sword-cross" size={22} color={color.textoSecundario} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => navigation.navigate('Ayuda')} hitSlop={8} testID="boton-ayuda">
            <Ionicons name="help-circle-outline" size={22} color={color.textoSecundario} />
          </TouchableOpacity>
          <TouchableOpacity onPress={salir}>
            <Text style={styles.salir}>Salir</Text>
          </TouchableOpacity>
        </View>
      </View>

      {ultimaAccionCombate && (
        <EfectoCombate key={ultimaAccionCombate.en} tipo={ultimaAccionCombate.tipo} exito={ultimaAccionCombate.exito} />
      )}

      <Animated.View
        style={[styles.dadoFlotante, estilosAcento.dadoFlotante, { opacity: opacidadDado }]}
        pointerEvents="none"
      >
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
          <View style={[styles.finalBanner, estilosAcento.finalBanner]}>
            <Text style={styles.finalBannerTexto}>Fin de la historia — final: {estado.tipo_final}</Text>
          </View>
        )}

        {faltanJugadores > 0 && (
          <View style={styles.ausenteBanner}>
            <Text style={styles.ausenteBannerTexto}>
              Esperando a {faltanJugadores} jugador{faltanJugadores !== 1 ? 'es' : ''} más para
              empezar ({personajes.length}/{sala.min_jugadores}).
            </Text>
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

        {companeros.length > 0 && (
          <Tarjeta style={{ gap: espacio.sm }}>
            <Text style={styles.tituloSeccion}>GRUPO</Text>
            {companeros.map((p) => (
              <View key={p.id} style={styles.companeroBloque}>
                <View style={styles.companeroCabecera}>
                  <Text style={styles.companeroNombre} numberOfLines={1}>
                    {p.nombre}
                  </Text>
                  {p.estado === 'ausente' && <Insignia texto="ausente" tono="aviso" />}
                  {p.estado === 'muerto' && <Insignia texto="caído" tono="peligro" />}
                </View>
                <BarraRecurso etiqueta="PV" actual={p.vida_actual} maximo={p.vida_max} />
                <BarraRecurso etiqueta="Maná" actual={p.mana_actual} maximo={p.mana_max} sinAlerta />
              </View>
            ))}
          </Tarjeta>
        )}

        {nodo?.tipo === 'interactivo' && !enCombate && !soyAusente && !soyMuerto && faltanJugadores === 0 && (
          <PanelInteraccion
            nodo={nodo}
            nodoActualId={estado?.nodo_actual_id ?? ''}
            palabrasClaveUsadas={estado?.palabras_clave_usadas ?? []}
            palabrasBloqueadas={palabrasBloqueadas}
            confirmacionesGrupales={confirmacionesGrupales}
            votosGrupales={votosGrupales}
            personaje={personaje}
            hechizos={hechizos}
            lanzarDado={lanzarDado}
            enviar={enviar}
          />
        )}

        {estado?.finalizada ? (
          <Boton texto="Volver al menú" onPress={salir} />
        ) : (
          nodo?.tipo === 'narrativo' &&
          !soyMuerto &&
          faltanJugadores === 0 && <Boton texto="Continuar" onPress={() => enviar('continuar')} />
        )}

        {enCombate && (
          <PanelCombate
            combate={estado!.combate!}
            esMiTurno={!!esMiTurno}
            personajeEnTurnoNombre={personajeEnTurno?.nombre}
            personaje={personaje}
            personajes={personajes}
            hechizos={hechizos}
            inventarioGrupo={estado?.inventario_grupo ?? []}
            lanzarDado={lanzarDado}
            enviar={enviar}
          />
        )}

        <PanelIntercambio
          propuestas={propuestasParaMi}
          inventarioGrupo={estado?.inventario_grupo ?? []}
          inventarioPersonal={personaje.inventario}
          companeros={companeros}
          enviar={enviar}
        />
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
      <TexturaGrano />
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: color.fondo },
  fondoImagen: { ...StyleSheet.absoluteFillObject },
  fondoVelo: { ...StyleSheet.absoluteFillObject, backgroundColor: color.fondo, opacity: 0.86 },
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
  companeroBloque: { gap: 6, paddingVertical: espacio.xs, borderTopWidth: 1, borderTopColor: color.bordeSutil },
  companeroCabecera: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: espacio.sm },
  companeroNombre: { color: color.texto, fontWeight: '700', fontSize: 13, flex: 1 },
  panelLog: {
    height: 100,
    borderTopWidth: 1,
    borderTopColor: color.borde,
    padding: espacio.sm,
  },
  logTexto: { color: color.textoTenue, fontSize: 11, marginBottom: 2 },
});
