import { useState } from 'react';
import { Animated, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Boton, BarraRecurso, Tarjeta } from '../../../components';
import { useEscalaPresion } from '../../../hooks/useEscalaPresion';
import { useAcento } from '../../../store/configStore';
import type { EstadoCombate, ObjetoInventario, Personaje } from '../../../types';
import { color, espacio, radio } from '../../../theme';

type Props = {
  combate: EstadoCombate;
  esMiTurno: boolean;
  personajeEnTurnoNombre?: string;
  personaje: Personaje;
  personajes: Personaje[];
  inventarioGrupo: ObjetoInventario[];
  lanzarDado: (tipoAccion: string, datos?: Record<string, unknown>) => void;
  enviar: (tipo: string, datos?: Record<string, unknown>) => void;
};

const EFECTOS_OBJETO_COMBATE = new Set(['curar_vida', 'curar_mana', 'dano']);

/** Cuánto cura, o cuánto daña, un objeto usable en combate, en un texto
 * listo para mostrar junto a su nombre. */
function textoEfectoObjeto(tipo: string | undefined, cantidad: number): string {
  if (tipo === 'curar_vida') return `+${cantidad} PV`;
  if (tipo === 'curar_mana') return `+${cantidad} maná`;
  return `${cantidad} de daño`;
}

/** El botón "Golpear" vive dentro de un `.map` por enemigo, y un hook no se
 * puede llamar directamente ahí dentro — de ahí este pequeño componente
 * aparte, solo para darle el mismo tacto de pulsación que `Boton`. */
function BotonGolpear({ onPress }: { onPress: () => void }) {
  const { escala, presionar, soltar } = useEscalaPresion();
  return (
    <Animated.View style={{ transform: [{ scale: escala }] }}>
      <TouchableOpacity style={styles.botonGolpear} onPress={onPress} onPressIn={presionar} onPressOut={soltar}>
        <Text style={styles.botonGolpearTexto}>Golpear</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

/** El panel de combate entero: ronda y turno, la lista de enemigos con su
 * botón de golpear, y las movidas de proteger/escabullirse/actuar bajo
 * presión/objeto — todo resuelto con la misma tirada de 2d6 que el resto
 * del juego (ver docs/motor_pbta_plan.md, sección 6). El enemigo ya no
 * tiene turno propio: su contraataque, si lo hay, va dentro de la propia
 * resolución de la movida del jugador. Tiene su propio estado de qué
 * sección de acción está desplegada — nada fuera de este panel necesita
 * saberlo. */
export default function PanelCombate({
  combate,
  esMiTurno,
  personajeEnTurnoNombre,
  personaje,
  personajes,
  inventarioGrupo,
  lanzarDado,
  enviar,
}: Props) {
  const acento = useAcento();
  const [seccionCombate, setSeccionCombate] = useState<'objeto' | 'proteger' | null>(null);
  const [objetoAtaqueElegido, setObjetoAtaqueElegido] = useState<string | null>(null);
  const [protegidoElegido, setProtegidoElegido] = useState<string | null>(null);

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

  const enemigosVivos = [];
  for (const en of combate.enemigos) {
    if (!en.derrotado) {
      enemigosVivos.push(en);
    }
  }

  const companerosElegibles = [];
  for (const p of personajes) {
    if (p.id !== personaje.id && p.estado !== 'ausente' && p.estado !== 'muerto') {
      companerosElegibles.push(p);
    }
  }

  function cerrarSeccion() {
    setSeccionCombate(null);
    setObjetoAtaqueElegido(null);
    setProtegidoElegido(null);
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
            </Text>
            {esMiTurno && !en.derrotado && seccionCombate === null && (
              <BotonGolpear onPress={() => lanzarDado('combate_accion', { accion: 'golpear', enemigo_id: en.enemigo_id })} />
            )}
          </View>
          <BarraRecurso etiqueta="PV" actual={en.vida} maximo={en.vida_max} />
        </Tarjeta>
      ))}
      {esMiTurno && (
        <>
          <View style={{ flexDirection: 'row', gap: espacio.sm }}>
            <View style={{ flex: 1, gap: 4 }}>
              <Boton
                texto="Proteger"
                variante="secundario"
                onPress={() => {
                  setSeccionCombate(seccionCombate === 'proteger' ? null : 'proteger');
                  setObjetoAtaqueElegido(null);
                  setProtegidoElegido(null);
                }}
              />
              <Text style={styles.accionSubtexto}>Te interpones en el golpe que iba a recibir un compañero</Text>
            </View>
            <View style={{ flex: 1, gap: 4 }}>
              <Boton
                texto="Escabullirse"
                variante="secundario"
                onPress={() => lanzarDado('combate_accion', { accion: 'escabullirse' })}
              />
              <Text style={styles.accionSubtexto}>Huyes, te escondes o esquivas un peligro inmediato</Text>
            </View>
          </View>

          <View style={{ gap: 4 }}>
            <Boton
              texto="Actuar bajo presión"
              variante="secundario"
              onPress={() => lanzarDado('combate_accion', { accion: 'actuar_bajo_presion' })}
            />
            <Text style={styles.accionSubtexto}>
              Cualquier otra acción arriesgada que no sea golpear, proteger o escabullirse
            </Text>
          </View>

          <Boton
            texto={`Usar objeto (${objetosUsables.length})`}
            variante="secundario"
            onPress={() => {
              setSeccionCombate(seccionCombate === 'objeto' ? null : 'objeto');
              setObjetoAtaqueElegido(null);
              setProtegidoElegido(null);
            }}
          />

          {seccionCombate === 'proteger' && !protegidoElegido && (
            <View style={styles.panelExpandido}>
              <Text style={styles.requisitoTexto}>Elige a quién proteger:</Text>
              {companerosElegibles.length === 0 && (
                <Text style={styles.requisitoTexto}>No hay ningún compañero al que proteger ahora mismo.</Text>
              )}
              {companerosElegibles.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.botonOpcion, { borderColor: acento.acento }]}
                  onPress={() => setProtegidoElegido(c.id)}
                >
                  <Text style={styles.botonOpcionTexto}>{c.nombre}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          {seccionCombate === 'proteger' && protegidoElegido && (
            <View style={styles.panelExpandido}>
              <Text style={styles.requisitoTexto}>¿De qué enemigo lo proteges?</Text>
              {enemigosVivos.map((en) => (
                <TouchableOpacity
                  key={en.enemigo_id}
                  style={[styles.botonOpcion, { borderColor: acento.acento }]}
                  onPress={() => {
                    lanzarDado('combate_accion', {
                      accion: 'proteger',
                      protegido_personaje_id: protegidoElegido,
                      enemigo_id: en.enemigo_id,
                    });
                    cerrarSeccion();
                  }}
                >
                  <Text style={styles.botonOpcionTexto}>{en.nombre}</Text>
                </TouchableOpacity>
              ))}
              <TouchableOpacity onPress={() => setProtegidoElegido(null)}>
                <Text style={styles.botonApoyoTexto}>‹ Elegir a otro compañero</Text>
              </TouchableOpacity>
            </View>
          )}

          {seccionCombate === 'objeto' && !objetoAtaqueElegido && (
            <View style={styles.panelExpandido}>
              {objetosUsables.length === 0 && (
                <Text style={styles.requisitoTexto}>No tienes objetos usables en combate.</Text>
              )}
              {objetosUsables.map((o, idx) => (
                <TouchableOpacity
                  key={`${idx}-${o.objeto_id}`}
                  style={[styles.botonOpcion, { borderColor: acento.acento }]}
                  onPress={() => {
                    if (o.efecto?.tipo === 'dano') {
                      setObjetoAtaqueElegido(o.objeto_id);
                      return;
                    }
                    enviar('combate_accion', { accion: 'objeto', objeto_id: o.objeto_id });
                    cerrarSeccion();
                  }}
                >
                  <Text style={styles.botonOpcionTexto}>
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
                  style={[styles.botonOpcion, { borderColor: acento.acento }]}
                  onPress={() => {
                    enviar('combate_accion', {
                      accion: 'objeto',
                      objeto_id: objetoAtaqueElegido,
                      enemigo_id: en.enemigo_id,
                    });
                    cerrarSeccion();
                  }}
                >
                  <Text style={styles.botonOpcionTexto}>{en.nombre}</Text>
                </TouchableOpacity>
              ))}
              <TouchableOpacity onPress={() => setObjetoAtaqueElegido(null)}>
                <Text style={styles.botonApoyoTexto}>‹ Elegir otro objeto</Text>
              </TouchableOpacity>
            </View>
          )}
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
  accionSubtexto: { color: color.textoTenue, fontSize: 11, textAlign: 'center' },
  botonGolpear: { backgroundColor: color.peligroFuerte, borderRadius: radio.sm, paddingHorizontal: 12, paddingVertical: 6 },
  botonGolpearTexto: { color: '#fff', fontWeight: '600' },
  panelExpandido: {
    backgroundColor: color.fondoElevado,
    borderRadius: radio.md,
    padding: espacio.sm,
    marginTop: 4,
    gap: espacio.sm,
  },
  requisitoTexto: { color: color.textoSecundario, fontSize: 13, lineHeight: 18 },
  botonOpcion: {
    backgroundColor: color.superficie,
    borderRadius: radio.md,
    padding: 10,
    borderWidth: 1,
    borderColor: color.acento,
  },
  botonOpcionTexto: { color: color.textoSecundario, fontSize: 13 },
  botonApoyoTexto: { color: '#b8d8ff', fontSize: 13 },
});
