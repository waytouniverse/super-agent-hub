export default function TrendChart({ data = [], maxValue, labelKey = 'label', valueKey = 'value' }) {
  const max = maxValue || Math.max(...data.map(d => d[valueKey]), 1);

  return (
    <div className="trend-chart">
      {data.map((item, idx) => (
        <div className="trend-bar" key={idx}>
          <span className={`trend-bar-label${item.isToday ? ' today' : ''}`}>
            {item[labelKey]}
          </span>
          <div className="trend-bar-track">
            <div
              className="trend-bar-fill"
              style={{ width: `${Math.max((item[valueKey] / max) * 100, 2)}%` }}
            />
          </div>
          <span className={`trend-bar-value${item.isToday ? ' today' : ''}`}>
            {item.displayValue || item[valueKey]}
          </span>
        </div>
      ))}
    </div>
  );
}
