import { CheckCircle, Loader, AlertCircle, Clock } from 'lucide-react';

const ENGINE_NAMES = {
  claude: 'Claude',
  codex: 'Codex',
  hermes: 'Hermes',
};

const STATUS_ICON = {
  pending: Clock,
  running: Loader,
  done: CheckCircle,
  error: AlertCircle,
};

const STATUS_CLASS = {
  pending: '',
  running: 'active',
  done: 'done',
  error: 'error',
};

export default function TaskExecutionPanel({ tasks = [] }) {
  if (!tasks.length) return null;

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <h3 className="execution-panel-title">任务执行</h3>
        <span className="execution-panel-progress">
          {tasks.filter((t) => t.status === 'done').length} / {tasks.length}
        </span>
      </div>

      <div className="execution-steps">
        {tasks.map((task, idx) => {
          const Icon = STATUS_ICON[task.status] || Clock;
          const cls = STATUS_CLASS[task.status] || '';

          return (
            <div key={task.id || idx} className={`execution-step ${cls}`}>
              <div className="execution-step-indicator">
                <Icon
                  size={16}
                  className={task.status === 'running' ? 'spin' : ''}
                />
              </div>
              <div className="execution-step-body">
                <div className="execution-step-title">
                  {task.title || `任务 ${idx + 1}`}
                </div>
                {task.engine && (
                  <span className="execution-step-engine">
                    {ENGINE_NAMES[task.engine] || task.engine}
                  </span>
                )}
                {task.status === 'running' && (
                  <div className="execution-step-status">执行中...</div>
                )}
                {task.status === 'done' && (
                  <div className="execution-step-status done">完成</div>
                )}
                {task.status === 'error' && task.error && (
                  <div className="execution-step-error">{task.error}</div>
                )}
              </div>
              {idx < tasks.length - 1 && (
                <div className="execution-step-connector" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
