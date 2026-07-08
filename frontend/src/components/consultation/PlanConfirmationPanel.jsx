import { useState, useEffect } from 'react';
import { Plus, Trash2, GripVertical, Play, Edit3, Check, X } from 'lucide-react';

const ENGINE_NAMES = {
  claude: 'Claude',
  codex: 'Codex',
  hermes: 'Hermes',
};

export default function PlanConfirmationPanel({
  plan,
  engines,
  onConfirm,
  onCancel,
}) {
  const [tasks, setTasks] = useState(() =>
    (plan?.tasks || []).map((t, i) => ({ ...t, _id: i }))
  );
  const [editingTask, setEditingTask] = useState(null);
  const [editDesc, setEditDesc] = useState('');

  // plan 变化时（新的 plan_generated 到达）重新同步任务列表
  useEffect(() => {
    setTasks((plan?.tasks || []).map((t, i) => ({ ...t, _id: i })));
    setEditingTask(null);
  }, [plan]);

  const installedEngines = engines.filter((e) => e.installed);

  const handleAdd = () => {
    setTasks([
      ...tasks,
      {
        _id: Date.now(),
        title: '新任务',
        description: '',
        engine: installedEngines[0]?.name || '',
        status: 'pending',
      },
    ]);
  };

  const handleDelete = (id) => {
    setTasks(tasks.filter((t) => t._id !== id));
  };

  const handleEngineChange = (id, engine) => {
    setTasks(tasks.map((t) => (t._id === id ? { ...t, engine } : t)));
  };

  const startEdit = (task) => {
    setEditingTask(task._id);
    setEditDesc(task.description || '');
  };

  const saveEdit = () => {
    setTasks(tasks.map((t) =>
      t._id === editingTask ? { ...t, description: editDesc } : t
    ));
    setEditingTask(null);
  };

  const confirmedPlan = {
    ...plan,
    tasks: tasks.map(({ _id, ...rest }) => rest),
  };

  return (
    <div className="plan-panel">
      <div className="plan-panel-header">
        <div>
          <h3 className="plan-panel-title">行动计划</h3>
          <p className="plan-panel-subtitle">
            审查并调整任务列表，确认后将自动按顺序执行。
          </p>
        </div>
      </div>

      {(plan?.overview || plan?.summary) && (
        <div className="plan-overview">{plan.overview || plan.summary}</div>
      )}

      <div className="plan-tasks">
        {tasks.map((task, idx) => (
          <div key={task._id} className="plan-task-item">
            <div className="plan-task-index">{idx + 1}</div>
            <div className="plan-task-body">
              <div className="plan-task-title">{task.title}</div>
              {editingTask === task._id ? (
                <div className="plan-task-edit">
                  <textarea
                    className="plan-task-edit-input"
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    rows={2}
                    autoFocus
                  />
                  <div className="plan-task-edit-actions">
                    <button className="plan-task-edit-save" onClick={saveEdit}>
                      <Check size={14} /> 保存
                    </button>
                    <button
                      className="plan-task-edit-cancel"
                      onClick={() => setEditingTask(null)}
                    >
                      <X size={14} /> 取消
                    </button>
                  </div>
                </div>
              ) : (
                task.description && (
                  <div className="plan-task-desc">{task.description}</div>
                )
              )}
            </div>
            <select
              className="plan-task-engine"
              value={task.engine || ''}
              onChange={(e) => handleEngineChange(task._id, e.target.value)}
            >
              {installedEngines.map((e) => (
                <option key={e.name} value={e.name}>
                  {ENGINE_NAMES[e.name] || e.display_name}
                </option>
              ))}
            </select>
            <div className="plan-task-actions">
              <button
                className="plan-task-btn"
                onClick={() => startEdit(task)}
                title="编辑描述"
              >
                <Edit3 size={14} />
              </button>
              <button
                className="plan-task-btn plan-task-delete"
                onClick={() => handleDelete(task._id)}
                title="删除"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <button className="plan-add-btn" onClick={handleAdd}>
        <Plus size={14} /> 添加任务
      </button>

      <div className="plan-panel-footer">
        <button className="plan-cancel-btn" onClick={onCancel}>
          取消
        </button>
        <button
          className="plan-confirm-btn"
          onClick={() => onConfirm(confirmedPlan)}
          disabled={tasks.length === 0}
        >
          <Play size={16} /> 确认并执行
        </button>
      </div>
    </div>
  );
}
