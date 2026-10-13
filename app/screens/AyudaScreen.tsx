import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Tarjeta } from '../components';
import { color, espacio, tipo } from '../theme';

type Seccion = {
  icono: ReactNode;
  titulo: string;
  acento: string;
  parrafos: string[];
};

const SECCIONES: Seccion[] = [
  {
    icono: <Ionicons name="body-outline" size={18} color={color.texto} />,
    titulo: 'Atributos',
    acento: color.narrativo,
    parrafos: [
      'Cada personaje tiene cuatro: Fuerza (pelear, forzar), Astucia (observar, engañar), Voluntad (resistir, lanzar hechizos) y Agilidad (esquivar, huir, iniciativa).',
      'Cuanto más alto, mejor se te da. Cada palabra clave o acción usa el atributo que tenga más sentido para ella.',
    ],
  },
  {
    icono: <MaterialCommunityIcons name="dice-d20-outline" size={18} color={color.texto} />,
    titulo: 'Tiradas',
    acento: color.interactivo,
    parrafos: [
      'Cuando una acción requiere tirada, el juego lanza un d20, le suma tu atributo, y compara el total con la dificultad del nodo. Igualar o superarla es éxito.',
      'Algunas palabras clave no piden tirada: se resuelven solo con confirmar (o, si es una decisión del grupo, con la opción más votada).',
    ],
  },
  {
    icono: <Ionicons name="people-outline" size={18} color={color.texto} />,
    titulo: 'Decisiones en grupo',
    acento: color.interactivo,
    parrafos: [
      'Una palabra clave puede ser individual (solo tú actúas), de apoyo (otro jugador te da ventaja antes de tirar), opuesta (tirada enfrentada contra un rival) o grupal.',
      'En una decisión grupal con dificultad, todos confirman la misma opción antes de tirar. Sin dificultad, cada uno vota y gana la opción más votada (empate: al azar).',
    ],
  },
  {
    icono: <Ionicons name="heart-outline" size={18} color={color.texto} />,
    titulo: 'Vida y maná',
    acento: color.peligro,
    parrafos: [
      'La vida (PV) baja con el daño. Al llegar a 0 quedas inconsciente — o, si el máster activó la muerte permanente en esta sala, puedes morir de verdad.',
      'El maná se gasta al lanzar hechizos y se recupera descansando. Ambos se ven como una barra en la parte de arriba de la pantalla.',
    ],
  },
  {
    icono: <Ionicons name="bag-handle-outline" size={18} color={color.texto} />,
    titulo: 'Inventario',
    acento: color.acento,
    parrafos: [
      'Hay objetos personales (solo tuyos, aunque puedes dárselos a otro jugador) y objetos del grupo: esos los puede usar cualquiera, sin tener que pedirlos primero.',
    ],
  },
  {
    icono: <MaterialCommunityIcons name="sword-cross" size={18} color={color.texto} />,
    titulo: 'Combate',
    acento: color.combate,
    parrafos: [
      'Los jugadores actúan por turnos (el orden se decide al empezar, tirando Agilidad). Los enemigos no tienen turno propio: responden de inmediato cuando les atacas, o a quien les haya hecho algo si tu acción no iba dirigida a ninguno.',
      'En tu turno puedes Atacar, Huir, Negociar, Usar un objeto o Lanzar un hechizo — cada una con su propia tirada.',
    ],
  },
];

export default function AyudaScreen() {
  return (
    <ScrollView contentContainerStyle={styles.contenedor}>
      <Text style={styles.titulo}>Cómo se juega</Text>
      <Text style={styles.subtitulo}>
        Un resumen rápido de las reglas — no hace falta memorizarlo, el juego te indica qué tirar en cada
        momento.
      </Text>

      {SECCIONES.map((s) => (
        <Tarjeta key={s.titulo} acento={s.acento} style={styles.tarjeta}>
          <View style={styles.cabeceraSeccion}>
            {s.icono}
            <Text style={styles.tituloSeccion}>{s.titulo}</Text>
          </View>
          {s.parrafos.map((p) => (
            <Text key={p} style={styles.parrafo}>
              {p}
            </Text>
          ))}
        </Tarjeta>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  contenedor: { padding: espacio.xl, backgroundColor: color.fondo, flexGrow: 1, gap: espacio.md },
  titulo: { ...tipo.titulo, fontSize: 26 },
  subtitulo: { ...tipo.nota, marginBottom: espacio.sm },
  tarjeta: { gap: espacio.xs },
  cabeceraSeccion: { flexDirection: 'row', alignItems: 'center', gap: espacio.sm, marginBottom: 2 },
  tituloSeccion: { color: color.texto, fontSize: 16, fontWeight: '700' },
  parrafo: { color: color.textoSecundario, fontSize: 13, lineHeight: 19 },
});
