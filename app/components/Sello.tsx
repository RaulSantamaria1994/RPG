import Svg, { Circle, Line, Path } from 'react-native-svg';
import { color } from '../theme';

type Props = {
  tamano?: number;
};

/** Sigilo grabado en latón: un ojo entreabierto en el centro de un
 * vórtice de zarcillos. Sustituye al típico ícono-dentro-de-un-círculo-
 * resplandeciente — es el símbolo propio de la identidad de la app, no
 * de ninguna historia en particular. */
export default function Sello({ tamano = 76 }: Props) {
  const zarcillos = [
    { x1: 60, y1: 15, x2: 60, y2: 8, cx: 64, cy: 10 },
    { x1: 91.82, y1: 28.18, x2: 96.77, y2: 23.23, cx: 98, cy: 25 },
    { x1: 105, y1: 60, x2: 112, y2: 60, cx: 112, cy: 57 },
    { x1: 91.82, y1: 91.82, x2: 96.77, y2: 96.77, cx: 96, cy: 98 },
    { x1: 60, y1: 105, x2: 60, y2: 112, cx: 56, cy: 111 },
    { x1: 28.18, y1: 91.82, x2: 23.23, y2: 96.77, cx: 22, cy: 95 },
    { x1: 15, y1: 60, x2: 8, y2: 60, cx: 8, cy: 63 },
    { x1: 28.18, y1: 28.18, x2: 23.23, y2: 23.23, cx: 24, cy: 22 },
  ];
  const angulosEstallido = [15, 75, 135, 195, 255, 315];

  return (
    <Svg width={tamano} height={tamano} viewBox="0 0 120 120">
      <Circle cx={60} cy={60} r={52} fill={color.fondo} stroke={color.acento} strokeWidth={1.5} />
      <Circle cx={60} cy={60} r={44} fill="none" stroke={color.acento} strokeWidth={0.75} opacity={0.6} />
      {zarcillos.map((z, i) => (
        <Path
          key={i}
          d={`M${z.x1},${z.y1} Q${z.cx},${z.cy} ${z.x2},${z.y2}`}
          fill="none"
          stroke={color.acento}
          strokeWidth={1.1}
        />
      ))}
      {angulosEstallido.map((angulo) => (
        <Line
          key={angulo}
          x1={60}
          y1={60}
          x2={64}
          y2={39}
          stroke={color.textoTenue}
          strokeWidth={0.7}
          opacity={0.55}
          transform={`rotate(${angulo} 60 60)`}
        />
      ))}
      <Path d="M40,60 Q60,49 80,60 Q60,71 40,60 Z" fill="none" stroke={color.texto} strokeWidth={1.3} />
      <Circle cx={60} cy={60} r={3.2} fill={color.texto} />
    </Svg>
  );
}
