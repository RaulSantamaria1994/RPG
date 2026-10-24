import { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Tarjeta } from '../../../components';
import { useAcento } from '../../../store/configStore';
import type { PropuestaIntercambio } from '../../../store/salaStore';
import type { ObjetoInventario, Personaje } from '../../../types';
import { color, espacio, radio } from '../../../theme';

type Props = {
  propuestas: PropuestaIntercambio[];
  inventarioGrupo: ObjetoInventario[];
  inventarioPersonal: ObjetoInventario[];
  companeros: Personaje[];
  enviar: (tipo: string, datos?: Record<string, unknown>) => void;
};

/** Propuestas de intercambio pendientes para mí, el inventario común del
 * grupo, y mi inventario personal (desde donde puedo ofrecerle un objeto a
 * un compañero). Tiene su propio estado de "qué objeto tengo abierto para
 * dar" — nada fuera de este panel necesita saberlo. */
export default function PanelIntercambio({
  propuestas,
  inventarioGrupo,
  inventarioPersonal,
  companeros,
  enviar,
}: Props) {
  const acento = useAcento();
  const [objetoParaDar, setObjetoParaDar] = useState<string | null>(null);

  return (
    <>
      {propuestas.map((p) => (
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

      {inventarioGrupo.length > 0 && (
        <View style={{ gap: espacio.sm }}>
          <Text style={styles.tituloSeccion}>INVENTARIO DEL GRUPO</Text>
          <Text style={styles.notaInventario}>
            Común para todos: cualquiera puede usar estos objetos, sin pedirlos.
          </Text>
          {inventarioGrupo.map((o, idx) => (
            <Tarjeta key={`${idx}-${o.objeto_id}`} acento={acento.acento} style={{ paddingVertical: espacio.sm }}>
              <Text style={styles.objetoNombre}>{o.nombre}</Text>
            </Tarjeta>
          ))}
        </View>
      )}

      {inventarioPersonal.length > 0 && (
        <View style={{ gap: espacio.sm }}>
          <Text style={styles.tituloSeccion}>INVENTARIO PERSONAL</Text>
          {inventarioPersonal.map((o) => (
            <Tarjeta key={o.objeto_id} style={{ paddingVertical: espacio.sm }}>
              <TouchableOpacity onPress={() => setObjetoParaDar(objetoParaDar === o.objeto_id ? null : o.objeto_id)}>
                <Text style={styles.objetoNombre}>
                  {o.nombre} {objetoParaDar === o.objeto_id ? '▲' : '▼ dar…'}
                </Text>
              </TouchableOpacity>
              {objetoParaDar === o.objeto_id && (
                <View style={styles.filaDestinatarios}>
                  {companeros.map((otro) => (
                    <TouchableOpacity
                      key={otro.id}
                      style={[styles.botonDestinatario, { borderColor: acento.acento }]}
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
                  {companeros.length === 0 && (
                    <Text style={styles.notaInventario}>No hay a quién dárselo todavía.</Text>
                  )}
                </View>
              )}
            </Tarjeta>
          ))}
        </View>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  tarjetaPropuesta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  propuestaTexto: { color: color.texto, flex: 1, marginRight: espacio.sm, fontSize: 13 },
  botonAceptar: { backgroundColor: color.exito, borderRadius: radio.sm, paddingHorizontal: 12, paddingVertical: 8 },
  botonAceptarTexto: { color: '#17301f', fontWeight: '700' },
  tituloSeccion: { color: color.textoSecundario, fontWeight: '700', fontSize: 13, letterSpacing: 0.6 },
  notaInventario: { color: color.textoSecundario, fontSize: 12 },
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
});
