import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, Category, Expense, Period, Stats } from "./api";
import { CategoryBar, DailyBars, Donut } from "./Charts";
import { dayLabel, localDateKey, money, periodTitle, time } from "./format";
import { confirmDialog, haptic, useExpanded, useMainButton } from "./tg";

const EMOJIS = ["🐈", "☕", "🍺", "📚", "✈️", "💄", "🎓", "🚗", "🐶", "💼", "🎨", "⚽"];
const COLORS = ["#FF9500", "#34C759", "#007AFF", "#AF52DE", "#FF2D55", "#5AC8FA", "#FFCC00", "#30B0C7"];

export default function Expenses() {
  const [period, setPeriod] = useState<Period>("month");
  const [offset, setOffset] = useState(0);
  const [cats, setCats] = useState<Category[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [items, setItems] = useState<Expense[]>([]);
  const [expanded, expand] = useExpanded();

  const [amount, setAmount] = useState("");
  const [catId, setCatId] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [newCat, setNewCat] = useState(false);
  const amountRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const [s, e] = await Promise.all([api.stats(period, offset), api.expenses(period, offset)]);
    setStats(s);
    setItems(e);
  }, [period, offset]);

  useEffect(() => {
    api.categories().then((c) => {
      setCats(c);
      setCatId((cur) => cur ?? c[0]?.id ?? null);
    });
  }, []);
  useEffect(() => void load(), [load]);

  const value = parseFloat(amount.replace(",", ".").replace(/\s/g, ""));
  const valid = value > 0;

  const submit = useCallback(async () => {
    if (!valid || saving) return;
    setSaving(true);
    try {
      await api.addExpense({ amount: value, category_id: catId, note: note.trim() });
      haptic.success();
      setAmount("");
      setNote("");
      setOffset(0);
      await load();
      amountRef.current?.blur();
    } catch {
      haptic.error();
    } finally {
      setSaving(false);
    }
  }, [valid, saving, value, catId, note, load]);

  const native = useMainButton(valid ? `Добавить ${money(value)}` : "Добавить", valid, submit, saving);

  const remove = async (e: Expense) => {
    if (!(await confirmDialog(`Удалить ${money(e.amount)}${e.note ? ` (${e.note})` : ""}?`))) return;
    await api.deleteExpense(e.id);
    haptic.tap();
    load();
  };

  const grouped = useMemo(() => {
    const m = new Map<string, { label: string; total: number; list: Expense[] }>();
    for (const e of items) {
      const d = new Date(e.spent_at);
      const k = localDateKey(d);
      if (!m.has(k)) m.set(k, { label: dayLabel(d), total: 0, list: [] });
      const g = m.get(k)!;
      g.total += e.amount;
      g.list.push(e);
    }
    return [...m.values()];
  }, [items]);

  const diff = stats && stats.prev_total > 0 ? (stats.total - stats.prev_total) / stats.prev_total : null;

  return (
    <>
      {/* ---- Быстрый ввод ---- */}
      <section className="card add-card">
        <div className="amount-row">
          <input
            ref={amountRef}
            className="amount-input"
            inputMode="decimal"
            placeholder="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value.replace(/[^\d.,\s]/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
          <span className="currency">₸</span>
        </div>
        <div className="chips">
          {cats.map((c) => (
            <button
              key={c.id}
              className={`chip ${catId === c.id ? "active" : ""}`}
              style={catId === c.id ? { background: c.color, borderColor: c.color } : undefined}
              onClick={() => {
                haptic.select();
                setCatId(c.id);
              }}
            >
              {c.emoji} {c.name}
            </button>
          ))}
          <button className="chip ghost" onClick={() => setNewCat((v) => !v)}>
            ＋
          </button>
        </div>
        {newCat && (
          <NewCategory
            onCreated={(c) => {
              setCats((cs) => [...cs, c]);
              setCatId(c.id);
              setNewCat(false);
            }}
          />
        )}
        <input
          className="text-input"
          placeholder="Комментарий (необязательно)"
          value={note}
          maxLength={256}
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        {!native && (
          <button className="primary" disabled={!valid || saving} onClick={submit}>
            {valid ? `Добавить ${money(value)}` : "Добавить"}
          </button>
        )}
      </section>

      {/* ---- Итог за период ---- */}
      {stats && (
        <section className="card">
          <div className="period-head">
            <button className="icon-btn" onClick={() => setOffset((o) => o + 1)} aria-label="Назад">
              ‹
            </button>
            <div className="period-title">{periodTitle(stats.start, stats.end, period)}</div>
            <button className="icon-btn" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - 1))} aria-label="Вперёд">
              ›
            </button>
          </div>
          <div className="segmented small">
            {(["week", "month"] as Period[]).map((p) => (
              <button
                key={p}
                className={period === p ? "active" : ""}
                onClick={() => {
                  haptic.select();
                  setPeriod(p);
                  setOffset(0);
                }}
              >
                {p === "week" ? "Неделя" : "Месяц"}
              </button>
            ))}
          </div>
          <div className="total">{money(stats.total)}</div>
          <div className="sub">
            ~{money(stats.avg_per_day)} в день
            {diff !== null && (
              <span className={diff > 0 ? "up" : "down"}>
                {" "}· {diff > 0 ? "▲" : "▼"} {Math.abs(Math.round(diff * 100))}% к прошлому
              </span>
            )}
          </div>

          {stats.total > 0 && <CategoryBar data={stats.by_category} total={stats.total} />}

          {expanded ? (
            stats.total > 0 && (
              <>
                <Donut data={stats.by_category} total={stats.total} />
                <h3 className="section-title">По дням</h3>
                <DailyBars data={stats.by_day} period={period} />
              </>
            )
          ) : (
            <button className="link-btn" onClick={expand}>
              ⤢ Развернуть — графики и категории
            </button>
          )}
        </section>
      )}

      {/* ---- История ---- */}
      {grouped.length === 0 ? (
        <p className="hint center">Трат за этот период нет</p>
      ) : (
        grouped.map((g) => (
          <section className="card list" key={g.label}>
            <div className="list-head">
              <span>{g.label}</span>
              <span>{money(g.total)}</span>
            </div>
            {g.list.map((e) => (
              <button className="row" key={e.id} onClick={() => remove(e)}>
                <span className="row-icon" style={{ background: (e.category?.color ?? "#8E8E93") + "33" }}>
                  {e.category?.emoji ?? "❔"}
                </span>
                <span className="row-main">
                  <span className="row-title">{e.note || e.category?.name || "Без категории"}</span>
                  <span className="row-sub">
                    {e.note ? `${e.category?.name ?? ""} · ` : ""}
                    {time(new Date(e.spent_at))}
                  </span>
                </span>
                <span className="row-amount">−{money(e.amount)}</span>
              </button>
            ))}
          </section>
        ))
      )}
      <p className="hint center small">Нажми на трату, чтобы удалить</p>
    </>
  );
}

function NewCategory({ onCreated }: { onCreated: (c: Category) => void }) {
  const [name, setName] = useState("");
  const [emoji, setEmoji] = useState(EMOJIS[0]);
  const color = useMemo(() => COLORS[Math.floor(Math.random() * COLORS.length)], []);
  const create = async () => {
    if (!name.trim()) return;
    const c = await api.addCategory({ name: name.trim(), emoji, color });
    haptic.success();
    onCreated(c);
  };
  return (
    <div className="new-cat">
      <div className="emoji-row">
        {EMOJIS.map((e) => (
          <button key={e} className={`emoji ${e === emoji ? "active" : ""}`} onClick={() => setEmoji(e)}>
            {e}
          </button>
        ))}
      </div>
      <div className="inline">
        <input
          className="text-input"
          placeholder="Название категории"
          value={name}
          maxLength={64}
          autoFocus
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && create()}
        />
        <button className="secondary" onClick={create}>
          OK
        </button>
      </div>
    </div>
  );
}
