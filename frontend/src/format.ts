let currency = "₸";
export const setCurrency = (c: string) => (currency = c);

export function money(v: number, withCur = true): string {
  const s = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: v % 1 ? 2 : 0 }).format(v);
  return withCur ? `${s} ${currency}` : s;
}

export function shortMoney(v: number): string {
  if (v >= 1_000_000) return `${+(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1000) return `${+(v / 1000).toFixed(1)}k`;
  return String(Math.round(v));
}

const dayFmt = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" });
const weekdayFmt = new Intl.DateTimeFormat("ru-RU", { weekday: "short" });
const timeFmt = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" });

export const localDateKey = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export function dayLabel(d: Date): string {
  const today = new Date();
  const y = new Date(today);
  y.setDate(today.getDate() - 1);
  const t = new Date(today);
  t.setDate(today.getDate() + 1);
  if (localDateKey(d) === localDateKey(today)) return "Сегодня";
  if (localDateKey(d) === localDateKey(y)) return "Вчера";
  if (localDateKey(d) === localDateKey(t)) return "Завтра";
  return dayFmt.format(d);
}

export const time = (d: Date) => timeFmt.format(d);

/** "2026-09-27" → короткая подпись для оси графика */
export function axisDay(iso: string, period: "week" | "month"): string {
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return period === "week" ? weekdayFmt.format(date) : String(d);
}

export function periodTitle(start: string, end: string, period: "week" | "month"): string {
  const [y, m, d] = start.split("-").map(Number);
  const s = new Date(y, m - 1, d);
  if (period === "month") {
    const t = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" }).format(s);
    return t.charAt(0).toUpperCase() + t.slice(1).replace(" г.", "");
  }
  const [y2, m2, d2] = end.split("-").map(Number);
  const e = new Date(y2, m2 - 1, d2);
  const f = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" });
  return `${f.format(s)} – ${f.format(e)}`;
}

export function remindLabel(iso: string): { text: string; overdue: boolean } {
  const d = new Date(iso);
  const overdue = d.getTime() < Date.now();
  return { text: `${dayLabel(d)}, ${time(d)}`, overdue };
}
