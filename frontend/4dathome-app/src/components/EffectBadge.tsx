// src/components/EffectBadge.tsx

export type EffectKind = "water" | "wind" | "light" | "shock" | "color";

const KANJI_MAP: Record<EffectKind, string> = {
  water: "水",
  wind: "風",
  light: "光",
  shock: "衝",
  color: "色",
};

type EffectBadgeProps = {
  kind: EffectKind;
  active?: boolean;  // ON/OFF
};

export function EffectBadge({ kind, active = true }: EffectBadgeProps) {
  const className = [
    "fx-effectBadge",
    `fx-effectBadge--${kind}`,
    active ? "" : "fx-effectBadge--off",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <span className={className}>
      {KANJI_MAP[kind]}
    </span>
  );
}
