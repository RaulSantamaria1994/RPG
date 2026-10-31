import { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Boton, Insignia, Tarjeta } from '../../../components';
import { useAcento } from '../../../store/configStore';
import type { Hechizo, Nodo, Personaje } from '../../../types';
import { color, espacio, radio } from '../../../theme';
import { ETIQUETA_ATRIBUTO, MOVIDAS, formatearId } from './comun';

type Props = {
  nodo: Nodo;
  nodoActualId: string;
  palabrasClaveUsadas: string[];
  palabrasBloqueadas: Record<string, string>;
  personaje: Personaje;
  hechizos: Hechizo[];
  lanzarDado: (tipoAccion: string, datos?: Record<string, unknown>) => void;
  enviar: (tipo: string, datos?: Record<string, unknown>) => void;
};

/** Lista de palabras clave del nodo interactivo actual — cada una se
 * despliega para mostrar qué movida resuelve (o que es una decisión sin
 * tirada), y permite ayudar a quien la resuelve o lanzarla por una vía
 * mágica alternativa. Antes vivía inline en JuegoScreen; tiene su propio
 * estado de "cuál está desplegada" porque nada fuera de este panel
 * necesita saberlo. */
export default function PanelInteraccion({
  nodo,
  nodoActualId,
  palabrasClaveUsadas,
  palabrasBloqueadas,
  personaje,
  hechizos,
  lanzarDado,
  enviar,
}: Props) {
  const acento = useAcento();
  const [palabraExpandida, setPalabraExpandida] = useState<string | null>(null);
  const [usarSuerte, setUsarSuerte] = useState(false);

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

        const movida = p.movida ? MOVIDAS[p.movida] : null;
        const caracteristica = movida?.caracteristica ?? null;
        const modificador = caracteristica ? personaje[caracteristica] - 3 : 0;
        const puedeUsarSuerte = !!movida && personaje.puntos_suerte_actual > 0;

        let contenidoRequisito;
        if (movida && caracteristica) {
          const signo = modificador >= 0 ? '+' : '';
          contenidoRequisito = (
            <Text style={styles.requisitoTexto}>
              {movida.nombre}: 2d6 {signo}
              {modificador} ({ETIQUETA_ATRIBUTO[caracteristica]} {personaje[caracteristica]}). 10+ éxito
              limpio, 7-9 éxito con coste, 6- fallo.
              {p.dano_fallo ? ` Si falla, ${p.dano_fallo.cantidad} de daño.` : ''}
            </Text>
          );
        } else if (movida) {
          // "ayudar" en sí mismo no se resuelve desde aquí (no tiene sentido
          // ayudarse a ayudar) — este caso no debería darse en una historia
          // bien formada, pero no rompe nada mostrarlo así si pasara.
          contenidoRequisito = <Text style={styles.requisitoTexto}>{movida.nombre}.</Text>;
        } else {
          contenidoRequisito = (
            <Text style={styles.requisitoTexto}>
              Decisión del grupo: no requiere tirada, se resuelve al confirmar.
            </Text>
          );
        }

        function tirar(datosExtra: Record<string, unknown> = {}) {
          const conDado = !!movida || datosExtra.via === 'hechizo' || datosExtra.rol_apoyo === 'apoyo';
          const extra = { ...datosExtra };
          if (movida && !datosExtra.via && usarSuerte) {
            extra.usar_suerte = true;
          }
          if (conDado) {
            lanzarDado('interactuar', { palabra_clave: p.texto, ...extra });
          } else {
            enviar('interactuar', { palabra_clave: p.texto, ...extra });
          }
          setPalabraExpandida(null);
          setUsarSuerte(false);
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
                    <Text style={styles.textoPalabra}>{p.texto}</Text>
                    {!deshabilitada && (
                      <Text style={styles.subtextoPalabra}>
                        {movida && (
                          <MaterialCommunityIcons name="dice-6" size={12} color={color.textoSecundario} />
                        )}
                        {movida ? ' ' : ''}
                        {movida ? movida.nombre : 'Sin tirada — se decide hablando'}
                      </Text>
                    )}
                  </View>
                  {usada && <Insignia texto="agotada" />}
                  {bloqueada && !usada && <Insignia texto="en curso…" tono="aviso" />}
                </View>

                {expandida && !deshabilitada && (
                  <View style={styles.panelExpandido}>
                    {contenidoRequisito}

                    <Boton
                      texto={movida ? 'Tirar 2d6' : 'Confirmar'}
                      icono={
                        movida ? (
                          <MaterialCommunityIcons name="dice-6" size={17} color={color.textoSobreAcento} />
                        ) : undefined
                      }
                      onPress={() => tirar()}
                    />

                    {puedeUsarSuerte && (
                      <TouchableOpacity
                        style={styles.filaSuerte}
                        onPress={() => setUsarSuerte((v) => !v)}
                        activeOpacity={0.8}
                      >
                        <Ionicons
                          name={usarSuerte ? 'checkbox' : 'square-outline'}
                          size={18}
                          color={usarSuerte ? acento.acento : color.textoSecundario}
                        />
                        <Text style={styles.suerteTexto}>
                          Si falla, gastar un Punto de Suerte para convertirlo en éxito (te quedan{' '}
                          {personaje.puntos_suerte_actual})
                        </Text>
                      </TouchableOpacity>
                    )}

                    {!!movida && (
                      <TouchableOpacity
                        style={styles.botonApoyo}
                        onPress={() => tirar({ rol_apoyo: 'apoyo' })}
                      >
                        <Text style={styles.botonApoyoTexto}>
                          Ayudar — tira aparte; si aciertas, da +1 a quien resuelva esto
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
                            <MaterialCommunityIcons name="dice-6" size={13} color={color.textoSecundario} />{' '}
                            Lanzar {info?.nombre ?? formatearId(h)} (vía mágica) — 2d6+Voluntad, coste{' '}
                            {info?.coste_mana ?? '?'} maná
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
  filaSuerte: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 2 },
  suerteTexto: { color: color.textoSecundario, fontSize: 12, flex: 1, lineHeight: 16 },
});
