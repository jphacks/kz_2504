/**
 * 4DX@HOME タイムライン仕様対応版 EffectStatusPanel
 * 
 * 仕様準拠ポイント:
 * - JSON: { events: [...] } 形式
 * - action: "caption" | "start" | "stop" | "shot"
 * - effect: "vibration" | "flash" | "color" | "water" | "wind"
 * - mode: 仕様書の全パターン対応（vibration の up/down 系、flash の blink 系、color の色名など）
 * - 将来的にモードごとのGIFアニメーション対応可能な構造
 */

import { useEffect, useState } from "react";
import { EffectBadge, type EffectKind } from "./EffectBadge";

// ========== 型定義（4DX@HOME仕様準拠） ==========

type ActionType = "caption" | "start" | "stop" | "shot";

type EffectType = "vibration" | "flash" | "color" | "water" | "wind";

/** 仕様書にある mode を文字列として扱う（将来の拡張も考えて string にしてOK） */
type VibrationMode =
  | "up_weak"
  | "up_mid_weak"
  | "up_mid_strong"
  | "up_strong"
  | "down_weak"
  | "down_mid_weak"
  | "down_mid_strong"
  | "down_strong"
  | "up_down_weak"
  | "up_down_mid_weak"
  | "up_down_mid_strong"
  | "up_down_strong"
  | "heartbeat";

type FlashMode = "steady" | "slow_blink" | "fast_blink";

type ColorMode = "red" | "green" | "blue" | "yellow" | "cyan" | "purple";

type WaterMode = "burst";

type WindMode = "burst";

type TimelineEvent =
  | {
      t: number;
      action: "caption";
      text: string;
    }
  | {
      t: number;
      action: "start" | "stop" | "shot";
      effect: EffectType;
      mode: string; // 具体的な型を絞る場合は上記の union を使ってもOK
    };

/** 各 effect ごとに「現在アクティブなモード群」を保持（将来のモード別アニメーション対応） */
type ActiveEffectState = {
  vibration: Set<string>;
  flash: Set<string>;
  color: Set<string>; // 実際には常に1つ想定だが Set にしておく
  water: Set<string>;
  wind: Set<string>;
};

type Props = {
  contentId: string;
  currentTime: number;
  visible?: boolean;
};

// ========== モード別ビジュアル設定（将来のGIF対応用） ==========

/** 将来ここに effect+mode → GIFパス や CSSクラスのマッピングを追加する */
const EFFECT_MODE_VISUALS: Partial<
  Record<EffectType, Record<string, { gif?: string; className?: string }>>
> = {
  vibration: {
    down_weak: { gif: "/gifs/vibration_down_weak.gif" },
    down_mid_weak: { gif: "/gifs/vibration_down_mid_weak.gif" },
    heartbeat: { gif: "/gifs/vibration_heartbeat.gif" },
  },
  flash: {
    fast_blink: { gif: "/gifs/flash_fast_blink.gif" },
  },
  // 必要に応じて他も定義
};

// ========== メインコンポーネント ==========

export default function EffectStatusPanel({ contentId, currentTime, visible = true }: Props) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);

  // JSONファイルの読み込み
  useEffect(() => {
    if (!contentId) return;

    const url = `/json/${contentId}.json`;

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        console.log("[EffectStatusPanel] raw timeline data:", data);

        if (!data || !Array.isArray(data.events)) {
          throw new Error("Unexpected timeline json format: expected { events: [...] }");
        }

        // 時刻順にソートされている前提だが、念のためソートしておく
        const sortedEvents = [...data.events].sort(
          (a, b) => (a.t as number) - (b.t as number)
        ) as TimelineEvent[];
        
        setEvents(sortedEvents);
      })
      .catch((err) => {
        console.error("Timeline load error:", err);
      });
  }, [contentId]);

  // ========== 状態計算関数 ==========

  const SHOT_WINDOW = 0.5; // shot イベントの表示時間（秒）

  const computeActiveEffects = (
    events: TimelineEvent[],
    currentTime: number
  ): ActiveEffectState => {
    const active: ActiveEffectState = {
      vibration: new Set(),
      flash: new Set(),
      color: new Set(),
      water: new Set(),
      wind: new Set(),
    };

    for (const ev of events) {
      if (ev.t > currentTime) break;
      if (ev.action === "caption") continue;

      const { effect, mode } = ev as Extract<
        TimelineEvent,
        { action: "start" | "stop" | "shot" }
      >;

      if (ev.action === "start") {
        if (effect === "color") {
          // 色は1色だけ有効（仕様書準拠）
          active.color.clear();
          active.color.add(mode);
        } else {
          active[effect].add(mode);
        }
      } else if (ev.action === "stop") {
        active[effect].delete(mode);
      } else if (ev.action === "shot") {
        // shot は currentTime に対して別途判定
        if (currentTime >= ev.t && currentTime <= ev.t + SHOT_WINDOW) {
          active[effect].add(mode);
        }
      }
    }

    return active;
  };

  const getCaptionAtTime = (
    events: TimelineEvent[],
    currentTime: number
  ): string | null => {
    let lastCaption: string | null = null;
    let lastT = -1;

    for (const ev of events) {
      if (ev.t > currentTime) break;
      if (ev.action === "caption") {
        if (ev.t >= lastT) {
          lastT = ev.t;
          lastCaption = ev.text;
        }
      }
    }

    return lastCaption;
  };

  /** 今はとりあえず「どの mode がアクティブか」を見て代表1つを返す */
  const getPrimaryMode = (effect: EffectType, active: ActiveEffectState): string | null => {
    const set = active[effect];
    const [first] = Array.from(set.values());
    return first ?? null;
  };

  // 現在の状態を計算
  const activeEffects = computeActiveEffects(events, currentTime);
  const currentCaption = getCaptionAtTime(events, currentTime);

  // ========== UI レンダリング ==========

  // EffectType → EffectKind マッピング
  const effectTypeToKind = (effect: EffectType): EffectKind => {
    switch (effect) {
      case "vibration":
        return "shock";
      case "flash":
        return "light";
      case "water":
        return "water";
      case "wind":
        return "wind";
      case "color":
        return "color";
    }
  };

  const effectItems: { effect: EffectType }[] = [
    { effect: "vibration" },
    { effect: "flash" },
    { effect: "wind" },
    { effect: "water" },
    { effect: "color" },
  ];

  // visible が false の場合は何も表示しない
  if (!visible) {
    return null;
  }

  return (
    <div className="effect-status-panel">
      {/* 左側: エフェクトアイコン */}
      <div className="effect-icons">
        {effectItems.map(({ effect }) => {
          const isActive = activeEffects[effect].size > 0;
          const primaryMode = getPrimaryMode(effect, activeEffects);
          const kind = effectTypeToKind(effect);

          return (
            <div
              key={effect}
              className={`effect-item ${isActive ? "active" : "inactive"}`}
              data-effect={effect}
              data-mode={primaryMode ?? ""}
            >
              {/* 漢字バッジのみ（ラベル完全削除） */}
              <EffectBadge kind={kind} active={isActive} />
            </div>
          );
        })}
      </div>

      {/* アイコンのすぐ右: Caption テキスト（左寄せ） */}
      {currentCaption && (
        <div className="caption-area-left">
          <div className="caption-card">{currentCaption}</div>
        </div>
      )}

      <style>{`
        .effect-status-panel {
          position: absolute;
          top: 16px;
          left: 16px;
          z-index: 10;
          display: flex;
          align-items: flex-start;
          gap: 16px;
          pointer-events: none;
        }

        .effect-icons {
          display: flex;
          flex-direction: column;
          gap: 8px;
          align-items: flex-start;
        }

        .effect-item {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 6px;
          transition: all 0.2s ease;
          pointer-events: auto;
        }

        .effect-item.active {
          transform: scale(1.05);
        }

        .effect-item.inactive {
          /* アイコン自体が薄くなるので追加スタイル不要 */
        }

        .caption-area-left {
          display: flex;
          align-items: flex-start;
          max-width: 800px;
        }

        .caption-card {
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(4px);
          color: #fff;
          padding: 10px 14px;
          border-radius: 8px;
          font-size: 30px;
          line-height: 1.5;
          border: 1px solid rgba(255, 255, 255, 0.15);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          pointer-events: auto;
          text-align: left;
        }
      `}</style>
    </div>
  );
}

