import { tg } from "./tg";

export interface Category {
  id: number;
  name: string;
  emoji: string;
  color: string;
}
export interface Expense {
  id: number;
  amount: number;
  note: string;
  spent_at: string;
  category: Category | null;
}
export interface CategoryStat extends Omit<Category, "id"> {
  id: number | null;
  total: number;
  count: number;
}
export interface Stats {
  period: Period;
  start: string;
  end: string;
  total: number;
  prev_total: number;
  avg_per_day: number;
  by_category: CategoryStat[];
  by_day: { date: string; total: number }[];
}
export interface Task {
  id: number;
  title: string;
  remind_at: string | null;
  reminded: boolean;
  done: boolean;
  created_at: string;
}
export interface Me {
  id: number;
  first_name: string;
  tz: string;
  currency: string;
}
export type Period = "week" | "month";

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {
    "X-Timezone": Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
  if (tg?.initData) headers.Authorization = `tma ${tg.initData}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const r = await fetch(`/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw new Error(`${r.status}: ${(await r.text()).slice(0, 200)}`);
  return r.status === 204 ? (undefined as T) : r.json();
}

export const api = {
  me: () => req<Me>("GET", "/me"),
  categories: () => req<Category[]>("GET", "/categories"),
  addCategory: (c: Omit<Category, "id">) => req<Category>("POST", "/categories", c),
  deleteCategory: (id: number) => req<void>("DELETE", `/categories/${id}`),

  expenses: (period: Period, offset = 0) => req<Expense[]>("GET", `/expenses?period=${period}&offset=${offset}`),
  addExpense: (e: { amount: number; category_id: number | null; note: string }) =>
    req<Expense>("POST", "/expenses", e),
  deleteExpense: (id: number) => req<void>("DELETE", `/expenses/${id}`),
  stats: (period: Period, offset = 0) => req<Stats>("GET", `/stats?period=${period}&offset=${offset}`),

  tasks: () => req<Task[]>("GET", "/tasks"),
  addTask: (t: { title: string; remind_at: string | null }) => req<Task>("POST", "/tasks", t),
  patchTask: (id: number, p: Partial<{ title: string; remind_at: string; clear_remind: boolean; done: boolean }>) =>
    req<Task>("PATCH", `/tasks/${id}`, p),
  deleteTask: (id: number) => req<void>("DELETE", `/tasks/${id}`),
};
