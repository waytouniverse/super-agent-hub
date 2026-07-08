import { ChevronRight } from 'lucide-react';

export default function EngineCard({ engine, onSelect }) {
  const installed = engine.installed;

  return (
    <div
      className="engine-card"
      onClick={() => installed && onSelect?.(engine)}
      style={{ opacity: installed ? 1 : 0.5, cursor: installed ? 'pointer' : 'default' }}
    >
      <div className={`engine-card-icon ${engine.name}`}>
        {engine.display_name.charAt(0)}
      </div>
      <div className="engine-card-info">
        <div className="engine-card-name">{engine.display_name}</div>
        <div className="engine-card-meta">
          {engine.vendor}
          {engine.version && ` · ${engine.version}`}
          {!installed && ' · 未安装'}
        </div>
      </div>
      <div className={`engine-card-status ${installed ? 'connected' : 'disconnected'}`}>
        {installed ? '已连接' : '未安装'}
      </div>
      {installed && (
        <ChevronRight size={16} className="engine-card-arrow" />
      )}
    </div>
  );
}
