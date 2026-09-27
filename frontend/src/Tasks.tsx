import { useCallback, useEffect, useState } from "react";
import { api, Task } from "./api";
import { remindLabel } from "./format";
import { confirmDialog, haptic, useMainButton } from "./tg";

type Preset = { label: string; at: () => Date };

const presets: Preset[] = [
  { label: "Через 1 ч", at: () => new Date(Date.now() + 3600_000) },
  { label: "Сегодня 20:00", at: () => at(0, 20) },
  { label: "Завтра 9:00", at: () => at(1, 9) },
  { label: "Завтра 18:00", at: () => at(1, 18) },
];

function at(daysFromNow: number, hour: number) {
  const d = new Date();
  d.setDate(d.getDate() + daysFromNow);
  d.setHours(hour, 0, 0, 0);
  return d;
}

/** Date → значение для <input type="datetime-local"> в локальном времени */
function toLocalInput(d: Date) {
  const off = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - off).toISOString().slice(0, 16);
}

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [remind, setRemind] = useState<string>(""); // datetime-local
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => api.tasks().then(setTasks), []);
  useEffect(() => void load(), [load]);

  const valid = title.trim().length > 0;
  const remindDate = remind ? new Date(remind) : null;

  const submit = useCallback(async () => {
    if (!valid || saving) return;
    setSaving(true);
    try {
      await api.addTask({ title: title.trim(), remind_at: remindDate ? remindDate.toISOString() : null });
      haptic.success();
      setTitle("");
      setRemind("");
      await load();
    } catch {
      haptic.error();
    } finally {
      setSaving(false);
    }
  }, [valid, saving, title, remindDate, load]);

  const native = useMainButton("Добавить задачу", valid, submit, saving);

  const toggle = async (t: Task) => {
    haptic.tap();
    setTasks((ts) => ts.map((x) => (x.id === t.id ? { ...x, done: !x.done } : x)));
    await api.patchTask(t.id, { done: !t.done });
    load();
  };

  const remove = async (t: Task) => {
    if (!(await confirmDialog(`Удалить «${t.title}»?`))) return;
    await api.deleteTask(t.id);
    load();
  };

  const open = tasks.filter((t) => !t.done);
  const done = tasks.filter((t) => t.done);

  return (
    <>
      <section className="card add-card">
        <input
          className="text-input big"
          placeholder="Что нужно сделать?"
          value={title}
          maxLength={256}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        <div className="chips">
          {presets.map((p) => {
            const v = toLocalInput(p.at());
            return (
              <button
                key={p.label}
                className={`chip ${remind === v ? "active accent" : ""}`}
                onClick={() => {
                  haptic.select();
                  setRemind(remind === v ? "" : v);
                }}
              >
                ⏰ {p.label}
              </button>
            );
          })}
        </div>
        <label className="dt-row">
          <span>Напомнить</span>
          <input type="datetime-local" value={remind} onChange={(e) => setRemind(e.target.value)} />
          {remind && (
            <button className="icon-btn" onClick={() => setRemind("")} aria-label="Без напоминания">
              ✕
            </button>
          )}
        </label>
        {!native && (
          <button className="primary" disabled={!valid || saving} onClick={submit}>
            Добавить задачу
          </button>
        )}
      </section>

      {open.length === 0 && done.length === 0 && <p className="hint center">Задач пока нет ✨</p>}

      {open.length > 0 && (
        <section className="card list">
          {open.map((t) => (
            <TaskRow key={t.id} t={t} onToggle={toggle} onRemove={remove} />
          ))}
        </section>
      )}

      {done.length > 0 && (
        <>
          <h3 className="section-title">Выполнено · {done.length}</h3>
          <section className="card list done">
            {done.slice(0, 30).map((t) => (
              <TaskRow key={t.id} t={t} onToggle={toggle} onRemove={remove} />
            ))}
          </section>
        </>
      )}
      <p className="hint center small">Напоминания придут сообщением от бота</p>
    </>
  );
}

function TaskRow({ t, onToggle, onRemove }: { t: Task; onToggle: (t: Task) => void; onRemove: (t: Task) => void }) {
  const r = t.remind_at ? remindLabel(t.remind_at) : null;
  return (
    <div className="row task">
      <button className={`check ${t.done ? "on" : ""}`} onClick={() => onToggle(t)} aria-label="Готово">
        {t.done ? "✓" : ""}
      </button>
      <span className="row-main" onClick={() => onToggle(t)}>
        <span className="row-title">{t.title}</span>
        {r && (
          <span className={`row-sub ${r.overdue && !t.done ? "overdue" : ""}`}>
            ⏰ {r.text}
            {t.reminded && !t.done ? " · напомнил" : ""}
          </span>
        )}
      </span>
      <button className="icon-btn muted" onClick={() => onRemove(t)} aria-label="Удалить">
        🗑
      </button>
    </div>
  );
}
