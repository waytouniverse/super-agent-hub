import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Plus, X, Users } from 'lucide-react';
import ChatInput from '../components/ChatInput';
import MessageBubble from '../components/MessageBubble';
import TokenBadge from '../components/TokenBadge';
import ParallelView from '../components/parallel/ParallelView';
import DebateView from '../components/debate/DebateView';
import PlanConfirmationPanel from '../components/consultation/PlanConfirmationPanel';
import TaskExecutionPanel from '../components/consultation/TaskExecutionPanel';
import ModeSelector from '../components/team/ModeSelector';
import ModeConfigPanel from '../components/team/ModeConfigPanel';
import { useProject } from '../contexts/ProjectContext';
import { useEngines } from '../hooks/useEngines';
import { useTeamSession } from '../hooks/useTeamSession';
import { fetchSession } from '../api';

const ENGINE_COLORS = {
  claude: '#d97706',
  codex: '#6366f1',
  hermes: '#ec4899',
};

const ENGINE_NAMES = {
  claude: 'Claude',
  codex: 'Codex',
  hermes: 'Hermes',
};

const MODE_LABELS = {
  serial: '串行审查',
  parallel: '并行讨论',
  debate: '多轮辩论',
  consultation: '会诊执行',
};

const TRANSIENT_TRANSPORT_MARKERS = [
  'Reconnecting...',
  'Falling back from WebSockets to HTTPS transport',
  'stream disconnected before completion',
  'Connection reset by peer',
];

const INTERNAL_EVENT_TYPES = new Set([
  'task_start', 'task_done', 'task_error',
  'plan_generated', 'phase_start', 'phase_end',
]);

function isTransientTransportMessage(content = '') {
  return TRANSIENT_TRANSPORT_MARKERS.some((marker) => content.includes(marker));
}

function hasVisibleMessageContent(msg) {
  if (INTERNAL_EVENT_TYPES.has(msg.type)) return false;
  if (isTransientTransportMessage(msg.content || '')) return false;
  if (msg.type === 'system' && /正在发言\.\.\.$/.test(msg.content || '')) return false;
  if (msg.role !== 'assistant' || msg.type !== 'text') return true;
  return typeof msg.content === 'string' ? msg.content.trim().length > 0 : Boolean(msg.content);
}

function TeamSetup({
  engines: allEngines,
  selectedEngines,
  onToggle,
  mode,
  onModeChange,
  modeConfig,
  onModeConfigChange,
}) {
  const installed = allEngines.filter((e) => e.installed);

  if (installed.length < 2) {
    return (
      <div className="team-setup">
        <div className="team-setup-icon"><Users size={48} /></div>
        <h2 className="team-setup-title">多引擎团队讨论</h2>
        <p className="team-setup-desc">
          需要至少 2 个已安装的引擎才能启动团队模式。
          <br />
          当前可用引擎：{installed.length} 个
        </p>
      </div>
    );
  }

  return (
    <div className="team-setup">
      <div className="team-setup-icon"><Users size={48} /></div>
      <h2 className="team-setup-title">组建你的 AI 团队</h2>
      <p className="team-setup-desc">
        选择 2-3 个引擎和协作模式，让 AI 团队协同工作。
      </p>

      <ModeSelector mode={mode} onChange={onModeChange} />

      <ModeConfigPanel
        mode={mode}
        config={modeConfig}
        onChange={onModeConfigChange}
        engines={allEngines}
      />

      <div className="team-engine-list">
        {installed.map((engine) => {
          const isSelected = selectedEngines.includes(engine.name);
          const order = selectedEngines.indexOf(engine.name);
          return (
            <div
              key={engine.name}
              className={`team-engine-item ${isSelected ? 'selected' : ''}`}
              onClick={() => onToggle(engine.name)}
            >
              <div className="team-engine-left">
                <span
                  className="team-engine-dot"
                  style={{ background: ENGINE_COLORS[engine.name] || '#888' }}
                />
                <span className="team-engine-name">{ENGINE_NAMES[engine.name] || engine.display_name}</span>
                <span className="team-engine-meta">{engine.vendor}</span>
              </div>
              {isSelected ? (
                <span className="team-engine-order" style={{ background: ENGINE_COLORS[engine.name] || '#888' }}>
                  #{order + 1}
                </span>
              ) : (
                <Plus size={16} className="team-engine-add" />
              )}
            </div>
          );
        })}
      </div>

      {selectedEngines.length > 0 && mode === 'serial' && (
        <p className="team-speak-order">
          发言顺序：
          {selectedEngines.map((e, i) => (
            <span key={e}>
              <span style={{ color: ENGINE_COLORS[e] || '#888', fontWeight: 600 }}>
                {ENGINE_NAMES[e] || e}
              </span>
              {i < selectedEngines.length - 1 && (
                <ArrowRight size={14} style={{ margin: '0 4px', verticalAlign: 'middle', opacity: 0.5 }} />
              )}
            </span>
          ))}
        </p>
      )}
    </div>
  );
}

/** Serial mode message list — each assistant message renders standalone with engine label */
function SerialMessageList({ messages, streamingContents, isStreaming }) {
  if (!messages.length && !isStreaming) {
    return (
      <div className="messages-empty">
        <div className="messages-empty-title">串行审查</div>
        <div className="messages-empty-subtitle">
          引擎按顺序依次发言，后面的引擎会审查前面的输出。
        </div>
      </div>
    );
  }

  return (
    <>
      {messages.map((msg, idx) => {
        if (!hasVisibleMessageContent(msg)) {
          return null;
        }
        if (msg.type === 'round_separator') {
          return null;
        }
        if (msg.type === 'system') {
          return (
            <div key={idx} className="team-separator">
              <span className="team-separator-text">{msg.content}</span>
            </div>
          );
        }
        if (msg.role === 'user') {
          return (
            <MessageBubble
              key={idx}
              role="user"
              content={msg.content}
              time={msg.time}
            />
          );
        }
        if (msg.role === 'assistant' && msg.type === 'tool_call') {
          return (
            <MessageBubble
              key={idx}
              role="assistant"
              content=""
              engine={msg.engine}
              showEngineLabel={true}
              toolCalls={[{ tool: msg.tool || msg.tool_name, input: msg.input || msg.tool_input }]}
            />
          );
        }
        if (msg.role === 'assistant' && msg.type === 'text') {
          return (
            <MessageBubble
              key={idx}
              role="assistant"
              content={msg.content}
              time={msg.time}
              engine={msg.engine}
              showEngineLabel={true}
            />
          );
        }
        return null;
      })}

      {/* Streaming: render per-engine streaming content as temporary bubbles */}
      {Object.entries(streamingContents).map(([eng, content]) =>
        content ? (
          <MessageBubble
            key={`stream-${eng}`}
            role="assistant"
            content={content}
            streaming={true}
            engine={eng}
            showEngineLabel={true}
          />
        ) : null
      )}

      {/* If streaming but no content yet, show thinking indicator */}
      {isStreaming && !Object.values(streamingContents).some(Boolean) && (
        <MessageBubble
          role="assistant"
          content=""
          thinking={true}
          engine={messages.find((m) => m.engine)?.engine || 'claude'}
          showEngineLabel={true}
        />
      )}
    </>
  );
}

export default function TeamChatPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resumeId = searchParams.get('resume');
  const { engines } = useEngines();
  const { projectPath, allowProjectWrites, setAllowProjectWrites, setProject } = useProject();

  const team = useTeamSession();
  const [resumeLoading, setResumeLoading] = useState(false);

  // 恢复历史团队会话
  useEffect(() => {
    if (!resumeId) return;
    setResumeLoading(true);
    fetchSession(resumeId).then((data) => {
      if (!data?.session) {
        setResumeLoading(false);
        return;
      }

      const s = data.session;

      // 优先从 team_config 恢复引擎列表，fallback 到 model 字段
      let enginesList = [];
      try {
        const tc = JSON.parse(s.team_config || '{}');
        if (tc.engines && Array.isArray(tc.engines)) {
          enginesList = tc.engines;
        }
        // 恢复模式配置
        team.setMode(tc.mode || s.team_mode || 'serial');
        if (tc.max_rounds || tc.judge_engine) {
          team.setModeConfig({
            maxRounds: tc.max_rounds || 3,
            judgeEngine: tc.judge_engine || '',
          });
        }
      } catch {
        team.setMode(s.team_mode || 'serial');
      }

      // fallback：从 model 字段恢复
      if (!enginesList.length) {
        enginesList = (s.model || '').split(',').map((v) => v.trim()).filter(Boolean);
      }

      if (enginesList.length < 2) {
        console.error('团队会话引擎不足:', enginesList);
        setResumeLoading(false);
        return;
      }

      // 一次性恢复所有状态
      team.setSelectedEngines(enginesList);
      team.setSessionId(s.id || resumeId);

      if (s.cwd) setProject(s.cwd).catch(() => {});

      if (data.messages?.length) {
        // 重建任务执行状态（按顺序处理事件）
        let restoredPlan = null;
        let restoredTasks = [];
        let restoredPlanConfirmed = false;
        let restoredPhase = '';
        const taskStatuses = {}; // taskId -> { status, title, engine, error }

        const formatted = data.messages.map((m) => {
          const base = {
            role: m.role,
            type: m.type,
            content: m.content,
            tool: m.tool_name,
            input: m.tool_input,
            engine: m.engine_name || '',
            time: m.created_at
              ? new Date(m.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
              : '',
            phase: m.phase || '',
            round: m.round || 0,
          };

          // 恢复 judge 消息的额外字段
          if (m.type === 'judge') {
            try {
              const j = JSON.parse(m.content || '{}');
              base.decision = j.decision || '';
              base.finalSummary = j.final_summary || '';
              base.content = j.evaluation || '';
            } catch {}
          }

          // 从消息中重建 plan/tasks/phase 状态
          if (m.type === 'plan_generated') {
            try {
              restoredPlan = JSON.parse(m.content || '{}');
            } catch {}
          }
          if (m.type === 'phase_start') {
            restoredPhase = m.content || '';
          }
          if (m.type === 'phase_end') {
            restoredPhase = '';
          }
          if (m.type === 'task_start') {
            try {
              const td = JSON.parse(m.content || '{}');
              taskStatuses[td.task_id] = {
                status: 'running',
                title: td.title || '',
                engine: td.engine || '',
              };
            } catch {}
          }
          if (m.type === 'task_done') {
            try {
              const td = JSON.parse(m.content || '{}');
              if (taskStatuses[td.task_id]) {
                taskStatuses[td.task_id].status = 'done';
              }
            } catch {}
          }
          if (m.type === 'task_error') {
            try {
              const td = JSON.parse(m.content || '{}');
              if (taskStatuses[td.task_id]) {
                taskStatuses[td.task_id].status = 'error';
                taskStatuses[td.task_id].error = td.error || '';
              }
            } catch {}
          }

          return base;
        }).filter(hasVisibleMessageContent);
        team.setMessages(formatted);

        // 兼容旧会话：即使没有 plan_generated 持久化，也能从任务事件重建
        if (!restoredPlan && Object.keys(taskStatuses).length > 0) {
          restoredPlan = { summary: '', tasks: [] };
        }

        // 应用重建的状态
        if (restoredPlan) {
          const hasTaskEvents = Object.keys(taskStatuses).length > 0;
          // 只有明确被中断的会话（非 running 非 active）才标记 running 任务为中断
          // running 状态表示后端仍在执行，刷新页面不应影响任务
          const wasInterrupted = s.status === 'interrupted';
          restoredTasks = Object.entries(taskStatuses).map(([id, ts]) => {
            let finalStatus = ts.status;
            if (finalStatus === 'running' && wasInterrupted) {
              finalStatus = 'error';
              ts.error = '会话中断，任务未完成';
            }
            return {
              id,
              title: ts.title,
              engine: ts.engine,
              status: finalStatus,
              error: ts.error || '',
            };
          });
          team.setPlan(restoredPlan);
          team.setTasks(restoredTasks);
          team.setPlanConfirmed(hasTaskEvents);
        }
        if (restoredPhase) {
          team.setCurrentPhase(restoredPhase);
        }
      }

      if (s.total_input_tokens || s.total_output_tokens) {
        team.setSessionUsage({
          input_tokens: s.total_input_tokens,
          output_tokens: s.total_output_tokens,
          cache_read: s.total_cache_read || 0,
          cache_write: s.total_cache_write || 0,
          cost_cny: (s.total_cost_usd || 0) * 7.2,
        });
      }

      // 最后设置 started，确保其他状态已就绪
      team.setStarted(true);
      setResumeLoading(false);
    }).catch((err) => {
      console.error('恢复团队会话失败:', err);
      setResumeLoading(false);
    });
  }, [resumeId, setProject]);

  // 正在恢复会话
  if (resumeLoading) {
    return (
      <div className="team-chat-page">
        <div className="chat-header">
          <div className="chat-header-content">
            <div className="chat-header-left">
              <span className="message-avatar team">T</span>
              <span className="chat-header-engine">团队模式</span>
            </div>
          </div>
        </div>
        <div className="loading" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span className="spinner" />
          <span style={{ marginLeft: 12, color: 'var(--text-muted)' }}>正在加载会话...</span>
        </div>
      </div>
    );
  }

  // Setup phase
  if (!team.started || team.selectedEngines.length < 2) {
    return (
      <div className="team-chat-page">
        <div className="chat-header">
          <div className="chat-header-content">
            <div className="chat-header-left">
              <span className="message-avatar team">T</span>
              <span className="chat-header-engine">团队模式</span>
            </div>
            <div className="chat-header-right">
              <button className="chat-header-btn" onClick={() => navigate('/')}>
                新建对话 <ArrowRight size={14} style={{ transform: 'rotate(90deg)' }} />
              </button>
            </div>
          </div>
        </div>
        <div className="team-setup-container">
          <TeamSetup
            engines={engines}
            selectedEngines={team.selectedEngines}
            onToggle={team.toggleEngine}
            mode={team.mode}
            onModeChange={team.setMode}
            modeConfig={team.modeConfig}
            onModeConfigChange={team.setModeConfig}
          />
          {team.selectedEngines.length >= 2 && (
            <button className="team-start-btn" onClick={team.handleStart}>
              <Users size={18} />
              开始团队讨论
            </button>
          )}
        </div>
      </div>
    );
  }

  const renderDiscussion = () => {
    switch (team.mode) {
      case 'parallel':
        return (
          <ParallelView
            messages={team.messages}
            streamingContents={team.streamingContents}
            currentEngine={team.currentEngine}
            selectedEngines={team.selectedEngines}
          />
        );
      case 'debate':
        return (
          <DebateView
            messages={team.messages}
            streamingContents={team.streamingContents}
            currentEngine={team.currentEngine}
            selectedEngines={team.selectedEngines}
          />
        );
      case 'consultation':
        return (
          <DebateView
            messages={team.messages}
            streamingContents={team.streamingContents}
            currentEngine={team.currentEngine}
            selectedEngines={team.selectedEngines}
          />
        );
      default:
        return (
          <SerialMessageList
            messages={team.messages}
            streamingContents={team.streamingContents}
            isStreaming={team.isStreaming}
          />
        );
    }
  };

  const renderMessages = () => (
    <>
      {renderDiscussion()}
      {team.plan && !team.planConfirmed && (
        <PlanConfirmationPanel
          plan={team.plan}
          engines={engines}
          onConfirm={(confirmedPlan) => team.handlePlanConfirm(confirmedPlan)}
          onCancel={() => {}}
        />
      )}
      {(team.planConfirmed || team.currentPhase === 'execution') && (
        <TaskExecutionPanel tasks={team.tasks} />
      )}
    </>
  );

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div className="chat-header-content">
          <div className="chat-header-left">
            <span className="message-avatar team">T</span>
            <span className="chat-header-engine">团队模式</span>
            <span className="chat-header-model">{MODE_LABELS[team.mode] || team.mode}</span>
            <span className="chat-header-model" style={{ display: 'flex', gap: 4 }}>
              {team.selectedEngines.map((e, i) => (
                <span key={e} style={{ color: ENGINE_COLORS[e] || '#888' }}>
                  {ENGINE_NAMES[e] || e}
                  {i < team.selectedEngines.length - 1 ? ' · ' : ''}
                </span>
              ))}
            </span>
          </div>
          <div className="chat-header-right">
            {team.sessionUsage && (
              <TokenBadge
                inputTokens={team.sessionUsage.input_tokens}
                outputTokens={team.sessionUsage.output_tokens}
                costCny={team.sessionUsage.cost_cny}
              />
            )}
            <button className="chat-header-btn" onClick={() => navigate('/')}>
              退出团队 <X size={14} />
            </button>
          </div>
        </div>
      </div>

      <div className="chat-messages">
        <div className="chat-content-column">
          {renderMessages()}
        </div>
      </div>

      <div className="chat-input-area">
        <div className="chat-content-column">
          <ChatInput
            onSend={(prompt) => team.handleSend(prompt, projectPath, allowProjectWrites)}
            onStop={team.handleStop}
            streaming={team.isStreaming}
            allowProjectWrites={allowProjectWrites}
            onAllowProjectWritesChange={setAllowProjectWrites}
          />
        </div>
      </div>
    </div>
  );
}
