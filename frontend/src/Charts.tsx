import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CategoryStat, Period } from "./api";
import { axisDay, money, shortMoney } from "./format";

/** Компактная полоска долей категорий — видна и в свёрнутом окне. */
export function CategoryBar({ data, total }: { data: CategoryStat[]; total: number }) {
  return (
    <div className="cat-bar">
      {data.map((c) => (
        <span key={c.id ?? "none"} style={{ width: `${(c.total / total) * 100}%`, background: c.color }} title={c.name} />
      ))}
    </div>
  );
}

export function Donut({ data, total }: { data: CategoryStat[]; total: number }) {
  return (
    <div className="donut-wrap">
      <div className="donut">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="total"
              nameKey="name"
              innerRadius="68%"
              outerRadius="100%"
              paddingAngle={data.length > 1 ? 2 : 0}
              stroke="none"
              isAnimationActive
            >
              {data.map((c) => (
                <Cell key={c.id ?? "none"} fill={c.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <small>всего</small>
          <b>{shortMoney(total)}</b>
        </div>
      </div>
      <ul className="legend">
        {data.map((c) => (
          <li key={c.id ?? "none"}>
            <span className="dot" style={{ background: c.color }} />
            <span className="legend-name">
              {c.emoji} {c.name}
            </span>
            <span className="legend-pct">{Math.round((c.total / total) * 100)}%</span>
            <span className="legend-sum">{money(c.total)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DailyBars({ data, period }: { data: { date: string; total: number }[]; period: Period }) {
  const max = Math.max(...data.map((d) => d.total));
  return (
    <div className="bars">
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 8, right: 0, left: -12, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tickFormatter={(v) => axisDay(v, period)}
            tick={{ fill: "var(--hint)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval={period === "month" ? 4 : 0}
          />
          <YAxis
            tickFormatter={shortMoney}
            tick={{ fill: "var(--hint)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: "var(--hover)" }}
            contentStyle={{ background: "var(--bg)", border: "none", borderRadius: 10, color: "var(--text)" }}
            labelFormatter={(v) => new Date(v + "T00:00").toLocaleDateString("ru-RU", { day: "numeric", month: "long" })}
            formatter={(v: number) => [money(v), "Потрачено"]}
          />
          <Bar dataKey="total" radius={[4, 4, 0, 0]} maxBarSize={28}>
            {data.map((d) => (
              <Cell key={d.date} fill={d.total === max && max > 0 ? "var(--accent)" : "var(--accent-soft)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
