import { ArrowRight, GitFork, MessageCircle, Stethoscope } from 'lucide-react';

const MODES = [
  {
    id: 'serial',
    name: '串行审查',
    icon: ArrowRight,
    desc: '引擎依次发言，后者审查前者输出，适合需要上下文积累的深度分析',
  },
  {
    id: 'parallel',
    name: '并行讨论',
    icon: GitFork,
    desc: '所有引擎同时回答，各自独立输出，快速收集多方观点',
  },
  {
    id: 'debate',
    name: '多轮辩论',
    icon: MessageCircle,
    desc: '每轮并行发言后裁判评估，多轮深度辩论直至得出结论',
  },
  {
    id: 'consultation',
    name: '会诊执行',
    icon: Stethoscope,
    desc: '辩论→生成计划→确认→自动执行，从讨论到落地的完整流程',
  },
];

export default function ModeSelector({ mode, onChange }) {
  return (
    <div className="mode-selector">
      <div className="mode-selector-label">协作模式</div>
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
