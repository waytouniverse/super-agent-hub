import { useNavigate } from 'react-router-dom';
import { Users } from 'lucide-react';
import { useEngines } from '../hooks/useEngines';
import { useStats } from '../hooks/useStats';
import EngineCard from '../components/EngineCard';
import SessionList from '../components/SessionList';
import { fetchSessions } from '../api';
import { useState, useEffect, useCallback } from 'react';

export default function HomePage() {
  const navigate = useNavigate();
  const { engines, loading: enginesLoading } = useEngines();
  const { stats, loading: statsLoading } = useStats(7);
  const [recentSessions, setRecentSessions] = useState([]);

  useEffect(() => {
    fetchSessions(5).then(data => setRecentSessions(data.sessions || [])).catch(() => {});
  }, []);

  const handleSelectEngine = useCallback((engine) => {
    if (engine.installed) {
      navigate(`/chat/${engine.name}`);
    }
  }, [navigate]);

  const handleContinueSession = useCallback((session) => {
    navigate(`/chat/${session.engine}?resume=${session.id}`);
  }, [navigate]);

  if (enginesLoading) {
    return (
      <div className="home-page">
        <div className="loading"><span className="spinner" /></div>
      </div>
    );
  }

  const installed = engines.filter(e => e.installed).length;

  return (
    <div className="home-page">
      <h1 className="home-title">Agent Hub</h1>
      <p className="home-subtitle">
        统一 AI 工作台 — 选择引擎，开始对话，所有记录永久保存。
      </p>

      {stats && (
        <div className="home-quick-stats">
          <div className="home-quick-stat">
            <div className="home-quick-stat-value">
              {stats.summary?.display_tokens || '0'}
            </div>
            <div className="home-quick-stat-label">7日 Token</div>
          </div>
          <div className="home-quick-stat">
            <div className="home-quick-stat-value">
              &yen;{stats.summary?.total_cost_cny?.toFixed(2) || '0.00'}
            </div>
            <div className="home-quick-stat-label">7日费用</div>
          </div>
          <div className="home-quick-stat">
            <div className="home-quick-stat-value">{installed}/3</div>
            <div className="home-quick-stat-label">可用引擎</div>
          </div>
        </div>
      )}

      {engines.map((engine) => (
        <EngineCard
          key={engine.name}
          engine={engine}
          onSelect={handleSelectEngine}
        />
      ))}

      <div className="team-entry-card" onClick={() => navigate('/chat/team')}>
        <div className="team-entry-icon">
          <Users size={24} />
        </div>
        <div className="team-entry-info">
          <div className="team-entry-name">团队讨论模式</div>
          <div className="team-entry-desc">
            多引擎协作 — 串联审查、交叉验证、综合总结
          </div>
        </div>
        <span className="team-entry-badge">Beta</span>
      </div>

      {recentSessions.length > 0 && (
        <div style={{ marginTop: 'var(--space-12)' }}>
          <div className="recent-sessions-title">最近会话</div>
          <SessionList sessions={recentSessions} onContinue={handleContinueSession} />
        </div>
      )}
    </div>
  );
}
