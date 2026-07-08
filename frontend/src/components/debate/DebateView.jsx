import { useRef, useEffect } from 'react';
import MessageBubble from '../MessageBubble';
import JudgeCard from './JudgeCard';

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

  // Group messages by round
  const rounds = [];
  let currentRound = null;

  for (const msg of messages) {
    if (msg.type === 'round_separator') {
      currentRound = { round: msg.round, label: msg.content, messages: [], judge: null };
      rounds.push(currentRound);
    } else if (msg.type === 'judge') {
      if (currentRound) {
        currentRound.judge = msg;
      } else {
        // Judge decision before any round separator (edge case)
        const lastRound = rounds[rounds.length - 1];
        if (lastRound) {
          lastRound.judge = msg;
        }
      }
    } else if (currentRound) {
      currentRound.messages.push(msg);
    } else {
      // Messages before first round separator (user message)
      if (rounds.length === 0) {
        rounds.push({ round: 0, label: '', messages: [], judge: null });
        rounds[0].messages.push(msg);
      } else {
        rounds[rounds.length - 1].messages.push(msg);
      }
    }
  }

  // Current streaming belongs to the last round
  const activeStreamEngines = Object.entries(streamingContents)
    .filter(([, v]) => v)
    .map(([k]) => k);

  return (
    <div className="debate-view">
      {rounds.map((round, ri) => (
        <div key={ri} className="debate-round">
          {round.label && (
            <div className="debate-round-header">
              <span className="debate-round-label">{round.label}</span>
            </div>
          )}

          <div className="debate-round-messages">
            {round.messages.map((msg, mi) => {
              if (msg.role === 'user') {
                return (
                  <MessageBubble
                    key={mi}
                    role="user"
                    content={msg.content}
                    time={msg.time}
                  />
                );
              }
              if (msg.type === 'system') {
                return (
                  <div key={mi} className="team-separator">
                    <span className="team-separator-text">{msg.content}</span>
                  </div>
                );
              }
              return (
                <MessageBubble
                  key={mi}
                  role={msg.role}
                  content={msg.content}
                  time={msg.time}
                  engine={msg.engine}
                  showEngineLabel={true}
                />
              );
            })}

            {/* Streaming content for this round (only if last round) */}
            {ri === rounds.length - 1 && activeStreamEngines.map((eng) => (
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
          </div>

          {round.judge && (
            <JudgeCard
              decision={round.judge.decision}
              evaluation={round.judge.content}
              finalSummary={round.judge.finalSummary}
              round={round.judge.round || round.round}
            />
          )}
        </div>
      ))}

      <div ref={bottomRef} />
    </div>
  );
}
