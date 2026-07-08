import { CheckCircle, RotateCw } from 'lucide-react';

const ENGINE_COLORS = {
  claude: '#d97706',
  codex: '#6366f1',
  hermes: '#ec4899',
};

export default function JudgeCard({ decision, evaluation, finalSummary, round }) {
  const isConclude = decision === 'CONCLUDE';

  return (
    <div className={`judge-card ${isConclude ? 'conclude' : 'continue'}`}>
      <div className="judge-card-header">
        <span className="judge-card-badge">
          {isConclude ? (
            <CheckCircle size={14} />
          ) : (
            <RotateCw size={14} />
          )}
          {isConclude ? '讨论结束' : '继续讨论'}
        </span>
        {round && <span className="judge-card-round">第 {round} 轮判定</span>}
      </div>

      {evaluation && (
        <div className="judge-card-evaluation">{evaluation}</div>
      )}

      {finalSummary && (
        <div className="judge-card-summary">
          <div className="judge-card-summary-label">最终结论</div>
          <div className="judge-card-summary-text">{finalSummary}</div>
        </div>
      )}
    </div>
  );
}
