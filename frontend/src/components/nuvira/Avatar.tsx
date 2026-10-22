type Accent = "blue" | "purple" | "green" | "coral";
type Shape = "leaf" | "molecule" | "droplet" | "sprout";

const COLORS: Record<Accent, { base: string; dark: string; ink: string }> = {
  blue: { base: "#6b9fc8", dark: "#4a7fa8", ink: "#1a3d5c" },
  purple: { base: "#9b8bc8", dark: "#7b6ba8", ink: "#3d2d6c" },
  green: { base: "#7bbf8c", dark: "#5b9f6c", ink: "#1a4d2c" },
  coral: { base: "#d4836e", dark: "#b4634e", ink: "#5c2a1c" },
};

export function Avatar({
  color = "blue",
  shape = "molecule",
  expression = "calm",
  size = 52,
}: {
  color?: Accent;
  shape?: Shape;
  expression?: "calm" | "thinking" | "smiling";
  size?: number;
}) {
  const c = COLORS[color];
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
      <ellipse cx="50" cy="87" rx="28" ry="7" fill="rgba(0,0,0,.08)" />
      <circle cx="50" cy="50" r="35" fill={c.base} />
      <ellipse cx="50" cy="68" rx="31" ry="18" fill={c.dark} opacity=".18" />
      {shape === "molecule" && <g fill="rgba(255,255,255,.82)" stroke="rgba(255,255,255,.65)" strokeWidth="2"><line x1="50" y1="68" x2="39" y2="59"/><line x1="50" y1="68" x2="62" y2="58"/><line x1="50" y1="68" x2="50" y2="80"/><circle cx="50" cy="68" r="5"/><circle cx="38" cy="58" r="4"/><circle cx="63" cy="57" r="4"/><circle cx="50" cy="81" r="4"/></g>}
      {shape === "sprout" && <g stroke="rgba(255,255,255,.82)" strokeWidth="3" fill="none" strokeLinecap="round"><path d="M50 80Q50 66 50 60"/><path d="M50 68Q38 62 39 55"/><path d="M50 64Q62 58 61 51"/></g>}
      {shape === "leaf" && <path d="M50 82C35 76 34 57 50 54C65 61 65 76 50 82Z" fill="rgba(255,255,255,.82)"/>}
      {shape === "droplet" && <path d="M50 53C50 53 36 69 36 76A14 14 0 0 0 64 76C64 69 50 53 50 53Z" fill="rgba(255,255,255,.82)"/>}
      <circle cx="37" cy="45" r="7" fill="white"/><circle cx="63" cy="45" r="7" fill="white"/>
      <circle cx="39" cy="46" r="4" fill={c.ink}/><circle cx="65" cy="46" r="4" fill={c.ink}/>
      <circle cx="37" cy="43" r="1.5" fill="white"/><circle cx="63" cy="43" r="1.5" fill="white"/>
      {expression === "smiling" ? <path d="M39 58Q50 70 61 58" stroke={c.ink} strokeWidth="3" fill="none" strokeLinecap="round"/> :
        expression === "thinking" ? <path d="M42 62Q50 58 58 62" stroke={c.ink} strokeWidth="3" fill="none" strokeLinecap="round"/> :
        <path d="M42 59Q50 66 58 59" stroke={c.ink} strokeWidth="3" fill="none" strokeLinecap="round"/>}
    </svg>
  );
}
