import { useRef, useEffect } from 'react';
import MessageBubble from '../MessageBubble';
import JudgeCard from './JudgeCard';

const INTERNAL_EVENT_TYPES = new Set([
  'task_start', 'task_done', 'task_error',
  'plan_generated', 'phase_start', 'phase_end',
]);

const TRANSIENT_TRANSPORT_MARKERS = [
  'Reconnecting...',
  'Falling back from WebSockets to HTTPS transport',
  'stream disconnected before completion',
  'Connection reset by peer',
];

function isTransientTransportMessage(content = '') {
  return TRANSIENT_TRANSPORT_MARKERS.some((marker) => content.includes(marker));
}

function hasVisibleContent(msg) {
  if (INTERNAL_EVENT_TYPES.has(msg.type)) return false;
  if (isTransientTransportMessage(msg.content || '')) return false;
  if (msg.type === 'system' && /正在发言\.\.\.$/.test(msg.content || '')) return false;
  if (msg.role !== 'assistant' || msg.type !== 'text') return true;
  return typeof msg.content === 'string' ? msg.content.trim().length > 0 : Boolean(msg.content);
}

export default function DebateView({
  messages,
  streamingContents,
  currentEngine,
  selectedEngines,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContents]);

  if (!messages.length) {
    return (
      <div className="messages-empty">
        <div className="messages-empty-title">多轮辩论</div>
        <div className="messages-empty-subtitle">
          每轮所有引擎并行发言，裁判评估后决定是否继续。
        </div>
      </div>
    );
  }

  const activeStreamEngines = Object.entries(streamingContents)
    .filter(([, v]) => v)
    .map(([k]) => k);

  return (
    <div className="debate-view">
      {messages.map((msg, idx) => {
        if (!hasVisibleContent(msg)) {
          return null;
        }
        if (msg.type === 'round_separator') {
          return (
            <div key={idx} className="team-separator">
              <span className="team-separator-text">{msg.content}</span>
            </div>
          );
        }
        if (msg.type === 'judge') {
          return (
            <JudgeCard
              key={idx}
              decision={msg.decision}
              evaluation={msg.content}
              finalSummary={msg.finalSummary}
              round={msg.round}
            />
          );
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
        return (
          <MessageBubble
            key={idx}
            role={msg.role}
            content={msg.content}
            time={msg.time}
            engine={msg.engine}
            showEngineLabel={true}
            toolCalls={msg.type === 'tool_call' ? [{ tool: msg.tool || msg.tool_name, input: msg.input || msg.tool_input }] : []}
          />
        );
      })}

      {activeStreamEngines.map((eng) => (
        streamingContents[eng] ? (
          <MessageBubble
            key={`stream-${eng}`}
            role="assistant"
            content={streamingContents[eng]}
            streaming={true}
            engine={eng}
            showEngineLabel={true}
          />
        ) : null
      ))}

      <div ref={bottomRef} />
    </div>
  );
}
