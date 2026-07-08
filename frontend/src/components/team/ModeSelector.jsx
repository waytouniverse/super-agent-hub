import { ArrowRight, GitFork, MessageCircle } from 'lucide-react';

const MODES = [
  {
    id: 'serial',
    name: '串行审查',
    icon: ArrowRight,
    desc: '依次分析并审查，最后生成执行计划',
  },
  {
    id: 'parallel',
    name: '并行讨论',
    icon: GitFork,
    desc: '同时给出方案，汇总后生成执行计划',
  },
  {
    id: 'debate',
    name: '多轮辩论',
    icon: MessageCircle,
    desc: '多轮互相补充，收敛后生成执行计划',
  },
];

export default function ModeSelector({ mode, onChange }) {
  return (
    <div className="mode-selector">
      <div className="mode-selector-label">协作模式</div>
      <div className="mode-selector-hint">所有模式都会在讨论后生成行动计划，确认后执行任务。</div>
      <div className="mode-selector-grid">
        {MODES.map((m) => {
          const Icon = m.icon;
          const active = mode === m.id;
          return (
            <button
              key={m.id}
              className={`mode-card ${active ? 'active' : ''}`}
              onClick={() => onChange(m.id)}
            >
              <div className="mode-card-icon">
                <Icon size={20} />
              </div>
              <div className="mode-card-info">
                <div className="mode-card-name">{m.name}</div>
                <div className="mode-card-desc">{m.desc}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
