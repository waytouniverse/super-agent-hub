import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchSessions, deleteSession } from '../api';
import SessionList from '../components/SessionList';
import { Folder, Trash2 } from 'lucide-react';

function projectNameFromPath(path) {
  if (!path) return '';
  const trimmed = path.replace(/\/+$/, '');
  return trimmed.split('/').pop() || path;
}

export default function SessionsPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [engineFilter, setEngineFilter] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    fetchSessions(100, 0, engineFilter)
      .then(data => setSessions(data.sessions || []))
      .catch((err) => {
        setError(err.message || '会话历史加载失败');
      })
      .finally(() => setLoading(false));
  }, [engineFilter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const handleVisible = () => {
      if (document.visibilityState === 'visible') {
        load();
      }
    };
    document.addEventListener('visibilitychange', handleVisible);
    return () => document.removeEventListener('visibilitychange', handleVisible);
  }, [load]);

  const handleContinue = useCallback((session) => {
    navigate(`/chat/${session.engine}?resume=${session.id}`);
  }, [navigate]);

  const handleDelete = useCallback(async (e, session) => {
    e.stopPropagation();
    if (!confirm('确定删除此会话？所有消息将被永久删除。')) return;
    await deleteSession(session.id);
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="sessions-page">
        <div className="loading"><span className="spinner" /></div>
      </div>
    );
  }

  return (
    <div className="sessions-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-8)' }}>
        <h1 className="sessions-page-title" style={{ marginBottom: 0 }}>
          会话历史
        </h1>
        <select
          className="settings-select"
          style={{ minWidth: 140 }}
          value={engineFilter}
          onChange={e => setEngineFilter(e.target.value)}
        >
          <option value="">全部引擎</option>
          <option value="claude">Claude Code</option>
          <option value="codex">Codex</option>
          <option value="hermes">Hermes</option>
          <option value="team">团队模式</option>
        </select>
      </div>

      {error ? (
        <div style={{ color: 'var(--text-muted)', padding: '48px 0', textAlign: 'center' }}>
          <div style={{ marginBottom: 12 }}>会话历史加载失败，请重试。</div>
          <button className="chat-header-btn" onClick={load}>重新加载</button>
        </div>
      ) : sessions.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', padding: '48px 0', textAlign: 'center' }}>
          暂无会话记录，开始对话后将自动保存。
        </div>
      ) : (
        sessions.map(s => (
          <div
            key={s.id}
            className="session-list-item"
            onClick={() => handleContinue(s)}
          >
            <div className="session-info">
              <div>
                <div className="session-list-title">
                  {s.title || '未命名会话'}
                </div>
                <div className="session-list-meta">
                  <span className="session-list-engine">{s.engine === 'team' ? '团队模式' : s.engine === 'claude' ? 'Claude' : s.engine === 'codex' ? 'Codex' : s.engine === 'hermes' ? 'Hermes' : s.engine}</span>
                  {s.cwd && (
                    <span className="session-list-project" title={s.cwd}>
                      <Folder size={11} />
                      {projectNameFromPath(s.cwd)}
                    </span>
                  )}
                  <span>{s.message_count || 0} 条消息</span>
                  {s.total_input_tokens > 0 && (
                    <span>
                      in {s.total_input_tokens >= 1000000
                        ? `${(s.total_input_tokens / 1000000).toFixed(1)}M`
                        : `${(s.total_input_tokens / 1000).toFixed(1)}K`}
                    </span>
                  )}
                  {s.updated_at && (
                    <span>{new Date(s.updated_at).toLocaleDateString('zh-CN')}</span>
                  )}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
              <span className="session-continue">继续</span>
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                  padding: 4,
                  display: 'flex',
                }}
                onClick={(e) => handleDelete(e, s)}
                title="删除"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
