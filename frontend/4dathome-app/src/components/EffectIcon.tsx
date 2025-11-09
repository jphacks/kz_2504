// src/components/EffectIcon.tsx

export type EffectType = "water" | "wind" | "vibration" | "flash" | "color";

interface EffectIconProps {
  type: EffectType;
  active?: boolean; // ONならtrue
}

export function EffectIcon({ type, active = false }: EffectIconProps) {
  return (
    <span
      className={[
        "fx-icon",
        `fx-icon--${type}`,
        active ? "fx-icon--on" : "fx-icon--off",
      ].join(" ")}
    />
  );
}
