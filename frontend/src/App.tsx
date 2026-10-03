import { useEffect, useState } from "react";
import { api, Me } from "./api";
import { setCurrency } from "./format";
import { haptic, inTelegram, tg } from "./tg";
import Expenses from "./Expenses";
import Tasks from "./Tasks";
import ThemePicker from "./ThemePicker";

type Tab = "money" | "tasks";

export default function App() {
  const [tab, setTab] = useState<Tab>(() => (location.hash === "#tasks" ? "tasks" : "money"));
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [canPin, setCanPin] = useState(false);

  useEffect(() => {
    // ?startapp=tasks → сразу вкладка задач (удобно для ярлыка на рабочем столе)
    const start = new URLSearchParams(location.search).get("tgWebAppStartParam");
    if (start === "tasks") setTab("tasks");
    // Кнопка «На главный экран» (Bot API 8.0+), прячем, если ярлык уже добавлен
    if (inTelegram && tg!.isVersionAtLeast("8.0") && tg!.checkHomeScreenStatus) {
      tg!.checkHomeScreenStatus((s) => setCanPin(s === "missed"));
    }
    api
      .me()
      .then((m) => {
        setCurrency(m.currency);
        setMe(m);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error)
    return (
      <div className="center-msg">
        <div style={{ fontSize: 40 }}>🔒</div>
        <p>{inTelegram ? "Нет доступа" : "Открой приложение из Telegram-бота"}</p>
        <small className="hint">{error}</small>
      </div>
    );
  if (!me) return <div className="center-msg"><div className="spinner" /></div>;

  const switchTab = (t: Tab) => {
    haptic.select();
    setTab(t);
  };

  return (
    <div className="app">
      <div className="segmented">
        <button className={tab === "money" ? "active" : ""} onClick={() => switchTab("money")}>
          💸 Траты
        </button>
        <button className={tab === "tasks" ? "active" : ""} onClick={() => switchTab("tasks")}>
          ✅ Задачи
        </button>
      </div>
      {tab === "money" ? <Expenses /> : <Tasks />}
      <ThemePicker />
      {canPin && (
        <button className="link-btn" onClick={() => tg!.addToHomeScreen?.()}>
          📌 Добавить на главный экран
        </button>
      )}
    </div>
  );
}
