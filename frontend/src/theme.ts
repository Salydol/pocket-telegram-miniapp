import { useEffect, useState } from "react";
import { inTelegram, tg } from "./tg";

/** Оформление: акцент + подложка. У каждого пользователя своё, хранится в Telegram CloudStorage. */
export type ThemeId = "telegram" | "pink" | "lavender" | "mint" | "peach" | "ocean" | "graphite";

interface Palette {
  accent: string;
  accentText: string;
  page: string; // фон страницы
  bg: string; // фон карточек
}

export interface Theme {
  id: ThemeId;
  name: string;
  light?: Palette;
  dark?: Palette;
}

export const THEMES: Theme[] = [
  { id: "telegram", name: "Telegram" },
  {
    id: "pink",
    name: "Розовая",
    light: { accent: "#E83E8C", accentText: "#ffffff", page: "#FFF0F6", bg: "#ffffff" },
    dark: { accent: "#FF7AB6", accentText: "#2B0A18", page: "#170D12", bg: "#25151D" },
  },
  {
    id: "lavender",
    name: "Лаванда",
    light: { accent: "#7C4DFF", accentText: "#ffffff", page: "#F4F0FF", bg: "#ffffff" },
    dark: { accent: "#B39DFF", accentText: "#1A1033", page: "#110F1A", bg: "#1C1828" },
  },
  {
    id: "mint",
    name: "Мята",
    light: { accent: "#0D9488", accentText: "#ffffff", page: "#ECFAF7", bg: "#ffffff" },
    dark: { accent: "#2DD4BF", accentText: "#062925", page: "#0A1614", bg: "#13221F" },
  },
  {
    id: "peach",
    name: "Персик",
    light: { accent: "#E8590C", accentText: "#ffffff", page: "#FFF3EB", bg: "#ffffff" },
    dark: { accent: "#FF9A62", accentText: "#2A1206", page: "#18100B", bg: "#261A12" },
  },
  {
    id: "ocean",
    name: "Океан",
    light: { accent: "#1D72D8", accentText: "#ffffff", page: "#EEF5FD", bg: "#ffffff" },
    dark: { accent: "#5EA8FF", accentText: "#06182E", page: "#0B121B", bg: "#141E2B" },
  },
  {
    id: "graphite",
    name: "Графит",
    light: { accent: "#2C2C2E", accentText: "#ffffff", page: "#F2F2F7", bg: "#ffffff" },
    dark: { accent: "#E5E5EA", accentText: "#000000", page: "#000000", bg: "#1C1C1E" },
  },
];

const KEY = "theme";
const VARS = ["--accent", "--accent-text", "--page", "--bg"] as const;

function isDark(): boolean {
  if (inTelegram) return tg!.colorScheme === "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function themeById(id: string | null | undefined): Theme {
  return THEMES.find((t) => t.id === id) ?? THEMES[0];
}

/** Палитра темы для текущей схемы; для «Telegram» — null (цвета берутся из темы Telegram). */
export function palette(theme: Theme): Palette | null {
  return (isDark() ? theme.dark : theme.light) ?? null;
}

let current: Theme = THEMES[0];
const listeners = new Set<(id: ThemeId) => void>();

/** Текущая тема для React-компонентов (обновляется и когда тема подтянулась из облака). */
export function useThemeId(): ThemeId {
  const [id, setId] = useState(current.id);
  useEffect(() => {
    listeners.add(setId);
    setId(current.id);
    return () => void listeners.delete(setId);
  }, []);
  return id;
}

export function applyTheme(id: ThemeId | string) {
  current = themeById(id);
  listeners.forEach((l) => l(current.id));
  const root = document.documentElement.style;
  const p = palette(current);
  if (p) {
    root.setProperty("--accent", p.accent);
    root.setProperty("--accent-text", p.accentText);
    root.setProperty("--page", p.page);
    root.setProperty("--bg", p.bg);
  } else {
    VARS.forEach((v) => root.removeProperty(v));
  }
  if (!inTelegram) return;
  // Шапка, фон под страницей и нативная кнопка Telegram — в цвет темы
  const t = tg!;
  const tgPage = t.themeParams?.secondary_bg_color;
  if (t.isVersionAtLeast("6.1")) {
    // hex в шапке — с 6.9, раньше только ключевые слова
    t.setHeaderColor?.(p && t.isVersionAtLeast("6.9") ? p.page : "secondary_bg_color");
    const bgColor = p ? p.page : tgPage;
    if (bgColor) t.setBackgroundColor?.(bgColor);
  }
  if (t.isVersionAtLeast("7.10")) t.setBottomBarColor?.(p ? p.page : "secondary_bg_color");
  t.MainButton.setParams?.({
    color: p ? p.accent : t.themeParams?.button_color,
    text_color: p ? p.accentText : t.themeParams?.button_text_color,
  });
}

function readLocal(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function writeLocal(id: string) {
  try {
    localStorage.setItem(KEY, id);
  } catch {
    /* приватный режим и т.п. */
  }
}

const cloud = () => (inTelegram && tg!.isVersionAtLeast("6.9") ? tg!.CloudStorage : undefined);

/**
 * Применяет тему сразу из локального кэша (без мигания), потом подтягивает
 * выбор из CloudStorage — он общий для всех устройств пользователя.
 */
export function initTheme() {
  applyTheme(readLocal() ?? "telegram");
  if (inTelegram) tg!.onEvent("themeChanged", () => applyTheme(current.id));
  cloud()?.getItem(KEY, (err, value) => {
    if (err || !value || value === current.id) return;
    writeLocal(value);
    applyTheme(value);
  });
}

export function saveTheme(id: ThemeId) {
  applyTheme(id);
  writeLocal(id);
  cloud()?.setItem(KEY, id);
}
