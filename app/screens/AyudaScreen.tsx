import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Tarjeta } from '../components';
import { useAcento } from '../store/configStore';
import { color, espacio, tipo } from '../theme';

type Seccion = {
  icono: ReactNode;
  titulo: string;
  /** undefined = usa el acento elegible en Opciones (la sección de
   * Inventario); el resto tiene un color semántico fijo. */
  acento?: string;
  parrafos: string[];
};

const SECCIONES: Seccion[] = [
  {
    icono: <Ionicons name="body-outline" size={18} color={color.texto} />,
    titulo: 'Atributos',
    acento: color.narrativo,
    parrafos: [
      'Cada personaje tiene cuatro: Fuerza (golpear, proteger), Astucia (investigar, leer el peligro), Voluntad (convencer, actuar bajo presión) y Agilidad (escabullirse).',
      'Van de 1 a 5 y se convierten en un modificador de -2 a +2 (valor - 3) al tirar.',
    ],
  },
  {
    icono: <MaterialCommunityIcons name="dice-6" size={18} color={color.texto} />,
    titulo: 'Tiradas',
    acento: color.interactivo,
    parrafos: [
      'Cuando una acción requiere tirada, el juego lanza 2d6 y les suma tu modificador. 10 o más es éxito limpio; 7, 8 o 9 es éxito con un pequeño coste (normalmente 1 de daño, o algo narrativo si la movida es social); 6 o menos es fallo.',
      'Las palabras clave sin movida son decisiones narrativas: no hay tirada, se resuelven en cuanto alguien del grupo las confirma — el motor no cuenta votos, lo habláis entre vosotros y uno confirma la opción acordada.',
    ],
  },
  {
    icono: <Ionicons name="list-outline" size={18} color={color.texto} />,
    titulo: 'Las movidas',
    acento: color.interactivo,
    parrafos: [
      'Golpear, Proteger a alguien y Escabullirse son las movidas de combate. Convencer o manipular, Investigar y Leer el peligro se usan explorando o hablando con alguien. Actuar bajo presión es el cajón de sastre para cualquier otra cosa arriesgada que ninguna de las anteriores cubra.',
      'Ayudar a otro es aparte: antes de que actúe un compañero, tiras tu propia tirada sin característica — si no sale fallo, le das +1 a la suya.',
    ],
  },
  {
    icono: <Ionicons name="heart-outline" size={18} color={color.texto} />,
    titulo: 'Vida y Puntos de Suerte',
    acento: color.peligro,
    parrafos: [
      'La barra de daño es de 7 para todos. Al llegar a 4 o más de daño acumulado quedas "inestable": sigues jugando, pero un golpe más es grave. Al llegar a 7/7 quedas inconsciente — o, si el máster activó la muerte permanente en esta sala, puedes morir de verdad.',
      'Empiezas con 7 Puntos de Suerte y no se recuperan solos. Puedes gastar uno, antes de tirar una movida (fuera de combate), para convertir un fallo en éxito si al final sale mal.',
      'El maná se gasta al lanzar hechizos y se recupera descansando.',
    ],
  },
  {
    icono: <Ionicons name="bag-handle-outline" size={18} color={color.texto} />,
    titulo: 'Inventario y equipo',
    parrafos: [
      'Hay objetos personales (solo tuyos, aunque puedes dárselos a otro jugador) y objetos del grupo: esos los puede usar cualquiera, sin tener que pedirlos primero.',
      'Un arma equipada suma un bono fijo al daño al golpear; una armadura equipada resta un valor fijo a cualquier golpe que recibas. Cada una tiene su propia ranura, en la pestaña de Equipo.',
    ],
  },
  {
    icono: <MaterialCommunityIcons name="sword-cross" size={18} color={color.texto} />,
    titulo: 'Combate',
    acento: color.combate,
    parrafos: [
      'Los jugadores actúan por turnos, en el orden en que se unieron a la partida. Los enemigos no tiran ni tienen turno propio: su contraataque, si lo hay, viene ya incluido en el resultado de tu propia movida.',
      'En tu turno puedes Golpear a un enemigo, Proteger a un compañero, Escabullirte, Actuar bajo presión o Usar un objeto.',
      'Golpear en 10+ no deja que el enemigo responda; en 7-9 golpeas pero recibes su daño; en 6- fallas y lo recibes igual. Proteger se lleva el golpe que iba para tu compañero si sale 7-9, o deja que le llegue igual si sale 6-.',
    ],
  },
];

export default function AyudaScreen() {
  const acento = useAcento();
  return (
    <ScrollView contentContainerStyle={styles.contenedor}>
      <Text style={styles.titulo}>Cómo se juega</Text>
      <Text style={styles.subtitulo}>
        Un resumen rápido de las reglas — no hace falta memorizarlo, el juego te indica qué tirar en cada
        momento.
      </Text>

      {SECCIONES.map((s) => (
        <Tarjeta key={s.titulo} acento={s.acento ?? acento.acento} style={styles.tarjeta}>
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
