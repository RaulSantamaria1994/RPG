import Svg, { Circle, Path } from 'react-native-svg';
import type { NodoResumen } from '../types';

type Props = {
  tipo: NodoResumen['tipo'];
  color: string;
  tamano?: number;
};

/** Un glifo propio por tipo de nodo — una pluma, un camino que se
 * bifurca, una grieta — en vez de depender solo de un punto de color
 * para distinguirlos. */
export default function GlifoNodo({ tipo, color, tamano = 14 }: Props) {
  if (tipo === 'narrativo') {
    return (
      <Svg width={tamano} height={tamano * 1.1} viewBox="0 0 18 20">
        <Path d="M3,18 L15,3" stroke={color} strokeWidth={1.4} fill="none" />
        <Path d="M15,3 L10,7 M15,3 L8,5" stroke={color} strokeWidth={1.1} fill="none" />
        <Circle cx={3} cy={18} r={1.2} fill={color} />
      </Svg>
    );
  }
  if (tipo === 'interactivo') {
    return (
      <Svg width={tamano} height={tamano * 1.1} viewBox="0 0 20 22">
        <Path d="M10,2 L10,10 M10,10 L3,19 M10,10 L17,19" stroke={color} strokeWidth={1.4} fill="none" />
      </Svg>
    );
  }
  return (
    <Svg width={tamano} height={tamano * 1.1} viewBox="0 0 18 22">
      <Path d="M10,2 L6,10 L12,12 L7,20" stroke={color} strokeWidth={1.4} fill="none" strokeLinejoin="round" />
    </Svg>
  );
}
