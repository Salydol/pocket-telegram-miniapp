import { useState } from "react";
import { haptic, inTelegram, tg } from "./tg";
import { palette, saveTheme, THEMES, useThemeId } from "./theme";

export default function ThemePicker() {
  const [open, setOpen] = useState(false);
  const active = useThemeId();

  if (!open)
    return (
      <button className="link-btn" onClick={() => setOpen(true)}>
        🎨 Оформление
      </button>
    );

  return (
    <div className="card">
      <div className="period-head">
        <span className="period-title">Оформление</span>
        <button className="icon-btn muted" onClick={() => setOpen(false)} aria-label="Закрыть">
          ✕
        </button>
      </div>
      <div className="themes">
        {THEMES.map((t) => {
          const p = palette(t);
          const accent = p?.accent ?? (inTelegram ? tg!.themeParams?.button_color : undefined) ?? "#2481cc";
          const page = p?.page ?? (inTelegram ? tg!.themeParams?.secondary_bg_color : undefined) ?? "#f2f2f7";
          return (
            <button
              key={t.id}
              className={"theme-swatch" + (t.id === active ? " active" : "")}
              onClick={() => {
                haptic.select();
                saveTheme(t.id);
              }}
            >
              <i style={{ background: `linear-gradient(135deg, ${accent} 50%, ${page} 50%)` }} />
              {t.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
