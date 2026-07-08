import { useRef, useEffect } from 'react';
import MessageBubble from '../MessageBubble';

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
  if (msg.role !== 'assistant' || msg.type !== 'text') return true;
  return typeof msg.content === 'string' ? msg.content.trim().length > 0 : Boolean(msg.content);
}

export default function ParallelView({
  messages,
  streamingContents,
  currentEngine,
  selectedEngines,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamingContents, messages]);

  if (!messages.length && !Object.values(streamingContents).some(Boolean)) {
    return (
      <div className="messages-empty">
        <div className="messages-empty-title">并行讨论</div>
        <div className="messages-empty-subtitle">
          所有引擎将同时收到问题，各自独立输出。每个引擎的输出会在独立区域展示。
        </div>
      </div>
    );
  }

  // Build per-engine message lists
  const engineMessages = {};
  for (const eng of selectedEngines) {
    engineMessages[eng] = [];
  }

  for (const msg of messages) {
    if (msg.type === 'system') continue;
    if (!hasVisibleContent(msg)) continue;
    if (msg.engine && engineMessages[msg.engine]) {
      engineMessages[msg.engine].push(msg);
    }
  }

  return (
    <div className="parallel-view">
      <div className="parallel-columns">
        {selectedEngines.map((eng) => {
          const engMsgs = engineMessages[eng] || [];
          const streaming = streamingContents[eng] || '';
          const isActive = currentEngine === eng;

          return (
            <div key={eng} className="parallel-column">
              <div
                className="parallel-column-header"
                style={{ borderTopColor: ENGINE_COLORS[eng] || '#888' }}
              >
                <span
                  className="parallel-column-dot"
                  style={{ background: ENGINE_COLORS[eng] || '#888' }}
                />
                <span className="parallel-column-name">
                  {ENGINE_NAMES[eng] || eng}
                </span>
                {isActive && streaming && (
                  <span className="parallel-column-typing">输入中...</span>
                )}
              </div>
              <div className="parallel-column-body">
                {engMsgs.length === 0 && !streaming && (
                  <div className="parallel-column-empty">等待发言...</div>
                )}
                {engMsgs.map((msg, idx) => (
                  <MessageBubble
                    key={idx}
                    role={msg.role}
                    content={msg.content}
                    time={msg.time}
                    engine={msg.engine || eng}
                    showEngineLabel={false}
                    toolCalls={msg.type === 'tool_call' ? [{ tool: msg.tool || msg.tool_name, input: msg.input || msg.tool_input }] : []}
                  />
                ))}
                {streaming && (
                  <MessageBubble
                    role="assistant"
                    content={streaming}
                    streaming={true}
                    engine={eng}
                    showEngineLabel={false}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div ref={bottomRef} />
    </div>
  );
}
