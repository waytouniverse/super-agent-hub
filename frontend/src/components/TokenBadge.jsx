export default function TokenBadge({ inputTokens, outputTokens, costCny }) {
  if (!inputTokens && !outputTokens) return null;

  const format = (n) => {
    if (!n) return '0';
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 'var(--space-2)',
      padding: '2px 8px',
      background: 'var(--bg-tertiary)',
      borderRadius: 'var(--radius-sm)',
      fontSize: 11,
      fontFamily: "'JetBrains Mono', monospace",
      color: 'var(--text-muted)',
    }}>
      <span>in {format(inputTokens)}</span>
      <span style={{ color: 'var(--border-active)' }}>·</span>
      <span>out {format(outputTokens)}</span>
      {costCny !== undefined && (
        <>
          <span style={{ color: 'var(--border-active)' }}>·</span>
          <span style={{ color: 'var(--accent-cyan)' }}>&yen;{costCny.toFixed(2)}</span>
        </>
      )}
    </div>
  );
}
