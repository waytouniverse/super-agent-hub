import { ChevronRight, Folder } from 'lucide-react';

const ENGINE_DISPLAY = {
  claude: 'Claude',
  codex: 'Codex',
  hermes: 'Hermes',
  team: '团队模式',
};

function engineLabel(name) {
  return ENGINE_DISPLAY[name] || name;
}

function projectNameFromPath(path) {
  if (!path) return '';
  const trimmed = path.replace(/\/+$/, '');
  return trimmed.split('/').pop() || path;
}

export default function SessionList({ sessions, onContinue }) {
  if (!sessions || sessions.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', padding: 'var(--space-8) 0', textAlign: 'center' }}>
        暂无会话记录
      </div>
    );
  }

  return (
    <div>
      {sessions.map((s) => (
        <div
          key={s.id}
          className="session-list-item"
          onClick={() => onContinue?.(s)}
        >
          <div className="session-info">
            <div>
              <div className="session-list-title">
                {s.title || '未命名会话'}
              </div>
              <div className="session-list-meta">
                <span className="session-list-engine">{engineLabel(s.engine)}</span>
                {s.cwd && (
                  <span className="session-list-project" title={s.cwd}>
                    <Folder size={11} />
                    {projectNameFromPath(s.cwd)}
                  </span>
                )}
                <span>{s.message_count || 0} 条消息</span>
                {s.updated_at && (
                  <span>{new Date(s.updated_at).toLocaleDateString('zh-CN')}</span>
                )}
              </div>
            </div>
          </div>
          <div className="session-continue">
            继续 <ChevronRight size={14} />
          </div>
        </div>
      ))}
    </div>
  );
}
