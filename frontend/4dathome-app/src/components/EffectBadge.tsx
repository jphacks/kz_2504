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
  active?: boolean;           // ONならtrue
  onClick?: () => void;       // トグルしたい場合に使う
};

export function EffectBadge({ kind, active = true, onClick }: EffectBadgeProps) {
  const className = [
    "fx-effectBadge",
    `fx-effectBadge--${kind}`,
    active ? "" : "fx-effectBadge--off",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type="button" className={className} onClick={onClick}>
      {KANJI_MAP[kind]}
    </button>
  );
}
