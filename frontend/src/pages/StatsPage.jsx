import { useState } from 'react';
import { useStats } from '../hooks/useStats';
import TrendChart from '../components/TrendChart';

function formatNum(n) {
  if (!n) return '0';
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

const DAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

export default function StatsPage() {
  const [days, setDays] = useState(7);
  const { stats, loading } = useStats(days);

  if (loading) {
    return (
      <div className="stats-page">
        <div className="loading"><span className="spinner" /></div>
      </div>
    );
  }

  if (!stats?.summary) {
    return (
      <div className="stats-page">
        <h1 className="stats-page-title">Token 统计</h1>
        <div style={{ color: 'var(--text-muted)', padding: '48px 0', textAlign: 'center' }}>
          暂无数据，开始对话后将自动记录 Token 用量。
        </div>
      </div>
    );
  }

  const s = stats.summary;
  const trendData = (stats.daily_trend || []).map(d => {
    const date = new Date(d.day);
    return {
      label: `${date.getMonth() + 1}/${date.getDate()}`,
      value: d.tokens,
      displayValue: formatNum(d.tokens),
      isToday: d.day === new Date().toISOString().slice(0, 10),
    };
  });

  return (
    <div className="stats-page">
      <div className="stats-page-header">
        <h1 className="stats-page-title">Token 使用概览</h1>
        <div style={{ marginTop: 12 }}>
          <select
            className="settings-select"
            value={days}
            onChange={e => setDays(Number(e.target.value))}
          >
            <option value={7}>最近 7 天</option>
            <option value={30}>最近 30 天</option>
            <option value={90}>最近 90 天</option>
          </select>
        </div>
      </div>

      <div className="stats-cards">
        <div className="stats-card">
          <div className="stats-card-label">总消耗</div>
          <div className="stats-card-value">{formatNum(s.total_tokens)}</div>
          <div className="stats-card-sub">{s.total_events} 次调用</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-label">费用</div>
          <div className="stats-card-value">&yen;{s.total_cost_cny?.toFixed(2)}</div>
          <div className="stats-card-sub">${s.total_cost_usd?.toFixed(2)} USD</div>
        </div>
        <div className="stats-card">
          <div className="stats-card-label">输入 / 输出</div>
          <div className="stats-card-value" style={{ fontSize: 18 }}>
            {formatNum(s.total_input)} / {formatNum(s.total_output)}
          </div>
          <div className="stats-card-sub">
            缓存读 {formatNum(s.total_cache_read)} · 写 {formatNum(s.total_cache_write)}
          </div>
        </div>
      </div>

      {trendData.length > 0 && (
        <div className="stats-section">
          <div className="stats-section-title">每日趋势</div>
          <TrendChart data={trendData} />
        </div>
      )}

      {stats.by_model && Object.keys(stats.by_model).length > 0 && (
        <div className="stats-section">
          <div className="stats-section-title">模型分布</div>
          {Object.entries(stats.by_model).map(([model, info]) => (
            <div key={model} className="stats-card" style={{ marginBottom: 'var(--space-3)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, fontWeight: 500, fontFamily: "'JetBrains Mono', monospace" }}>
                  {model}
                </span>
                <span style={{ fontSize: 13, color: 'var(--accent-cyan)', fontFamily: "'JetBrains Mono', monospace" }}>
                  {formatNum(info.tokens)} · &yen;{(info.cost * 7.2).toFixed(2)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
