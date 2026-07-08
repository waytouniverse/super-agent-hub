import { useRef, useEffect } from 'react';
import DebateView from '../debate/DebateView';
import PlanConfirmationPanel from './PlanConfirmationPanel';
import TaskExecutionPanel from './TaskExecutionPanel';

export default function ConsultationView({
  messages,
  streamingContents,
  currentEngine,
  selectedEngines,
  engines,
  plan,
  planConfirmed,
  tasks,
  currentPhase,
  isStreaming,
  onPlanConfirm,
}) {
  if (currentPhase === 'execution' || planConfirmed) {
    return (
      <div className="consultation-view">
        {plan && (
          <div className="consultation-plan-summary">
            <div className="consultation-plan-title">执行计划</div>
            <div className="consultation-plan-text">{plan.overview || '任务执行中...'}</div>
          </div>
        )}
        <TaskExecutionPanel tasks={tasks} />
      </div>
    );
  }

  if (plan && !planConfirmed) {
    return (
      <div className="consultation-view">
        <DebateView
          messages={messages}
          streamingContents={streamingContents}
          currentEngine={currentEngine}
          selectedEngines={selectedEngines}
        />
        <PlanConfirmationPanel
          plan={plan}
          engines={engines}
          onConfirm={onPlanConfirm}
          onCancel={() => {}}
        />
      </div>
    );
  }

  // Discussion phase
  return (
    <div className="consultation-view">
      <DebateView
        messages={messages}
        streamingContents={streamingContents}
        currentEngine={currentEngine}
        selectedEngines={selectedEngines}
      />
    </div>
  );
}
