export default function TokenBadge({ inputTokens, outputTokens, costCny }) {
  if (!inputTokens && !outputTokens) return null;

  const format = (n) => {
    if (!n) return '0';
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

  return (
    <div className="token-badge">
      <span>in {format(inputTokens)}</span>
      <span className="token-badge-separator">·</span>
      <span>out {format(outputTokens)}</span>
      {costCny != null && (
        <>
          <span className="token-badge-separator">·</span>
          <span className="token-badge-cost">&yen;{costCny.toFixed(2)}</span>
        </>
      )}
    </div>
  );
}
