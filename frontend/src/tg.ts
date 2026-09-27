import { useEffect, useState } from "react";

/** Минимальная типизация Telegram.WebApp — только то, что используем. */
interface MainButton {
  setText(t: string): void;
  show(): void;
  hide(): void;
  enable(): void;
  disable(): void;
  showProgress(leaveActive?: boolean): void;
  hideProgress(): void;
  onClick(cb: () => void): void;
  offClick(cb: () => void): void;
}

interface WebApp {
  initData: string;
  platform: string;
  version: string;
  isExpanded: boolean;
  colorScheme: "light" | "dark";
  ready(): void;
  expand(): void;
  isVersionAtLeast(v: string): boolean;
  onEvent(e: string, cb: () => void): void;
  offEvent(e: string, cb: () => void): void;
  showConfirm(msg: string, cb: (ok: boolean) => void): void;
  addToHomeScreen?(): void;
  checkHomeScreenStatus?(cb: (status: string) => void): void;
  MainButton: MainButton;
  HapticFeedback: {
    impactOccurred(s: "light" | "medium" | "heavy" | "rigid" | "soft"): void;
    notificationOccurred(t: "error" | "success" | "warning"): void;
    selectionChanged(): void;
  };
  setHeaderColor?(c: string): void;
}

declare global {
  interface Window {
    Telegram?: { WebApp: WebApp };
  }
}

const raw = window.Telegram?.WebApp;
/** true, если открыто внутри Telegram (а не просто в браузере для разработки) */
export const inTelegram = !!raw && !!raw.initData;
export const tg = raw;

export function initTelegram() {
  if (!inTelegram || !tg) {
    document.documentElement.classList.add("no-tg");
    return;
  }
  tg.ready();
  if (tg.isVersionAtLeast("6.1")) tg.setHeaderColor?.("secondary_bg_color");
}

export const haptic = {
  tap: () => inTelegram && tg!.HapticFeedback.impactOccurred("light"),
  select: () => inTelegram && tg!.HapticFeedback.selectionChanged(),
  success: () => inTelegram && tg!.HapticFeedback.notificationOccurred("success"),
  error: () => inTelegram && tg!.HapticFeedback.notificationOccurred("error"),
};

export function confirmDialog(msg: string): Promise<boolean> {
  if (inTelegram && tg!.isVersionAtLeast("6.2")) {
    return new Promise((res) => tg!.showConfirm(msg, res));
  }
  return Promise.resolve(window.confirm(msg));
}

/** Развёрнуто ли окно Mini App на весь экран. В браузере — всегда да. */
export function useExpanded(): [boolean, () => void] {
  const [expanded, setExpanded] = useState(inTelegram ? tg!.isExpanded : true);
  useEffect(() => {
    if (!inTelegram) return;
    const h = () => setExpanded(tg!.isExpanded);
    tg!.onEvent("viewportChanged", h);
    return () => tg!.offEvent("viewportChanged", h);
  }, []);
  return [expanded, () => (inTelegram ? tg!.expand() : undefined)];
}

/**
 * Нативная кнопка Telegram внизу экрана. В браузере возвращает false —
 * тогда компонент рисует обычную кнопку.
 */
export function useMainButton(text: string, visible: boolean, onClick: () => void, busy = false) {
  useEffect(() => {
    if (!inTelegram) return;
    const mb = tg!.MainButton;
    mb.setText(text);
    if (visible) mb.show();
    else mb.hide();
    if (busy) mb.showProgress(false);
    else mb.hideProgress();
    mb.onClick(onClick);
    return () => mb.offClick(onClick);
  }, [text, visible, onClick, busy]);

  useEffect(() => () => void (inTelegram && tg!.MainButton.hide()), []);
  return inTelegram;
}
