import { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';

function groupMessages(messages, streamingContent, isStreaming) {
  const groups = [];

  messages.forEach((msg) => {
    if (msg.role === 'assistant' || msg.type === 'tool_call') {
      const last = groups[groups.length - 1];
      const group = last?.role === 'assistant'
        ? last
        : {
            role: 'assistant',
            type: 'assistant_group',
            content: '',
            toolCalls: [],
            time: msg.time,
            tokenInfo: msg.tokenInfo,
          };

      if (last?.role !== 'assistant') {
        groups.push(group);
      }

      if (msg.type === 'tool_call') {
        group.toolCalls.push({
          tool: msg.tool,
          input: msg.input,
        });
      } else {
        group.content = group.content
          ? `${group.content}\n\n${msg.content || ''}`
          : (msg.content || '');
        group.time = group.time || msg.time;
        group.tokenInfo = group.tokenInfo || msg.tokenInfo;
      }
      return;
    }

    groups.push(msg);
  });

  if (streamingContent) {
    const last = groups[groups.length - 1];
    if (last?.role === 'assistant') {
      last.streamingContent = streamingContent;
      last.streaming = true;
    } else {
      groups.push({
        role: 'assistant',
        type: 'assistant_group',
        content: streamingContent,
        toolCalls: [],
        streaming: true,
      });
    }
  } else if (isStreaming) {
    const last = groups[groups.length - 1];
    if (last?.role === 'assistant') {
      last.thinking = true;
    } else {
      groups.push({
        role: 'assistant',
        type: 'assistant_group',
        content: '',
        toolCalls: [],
        thinking: true,
      });
    }
  }

  return groups;
}

export default function MessageList({
  messages = [],
  streamingContent = '',
  isStreaming = false,
  engine = 'claude',
  teamMode = false,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, isStreaming]);

  if (!messages.length && !streamingContent) {
    return (
      <div className="messages-empty">
        <svg className="messages-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
        </svg>
        <div className="messages-empty-title">开始新的对话</div>
        <div className="messages-empty-subtitle">
          在下方输入你的问题，AI Agent 将为你提供帮助。所有对话都会自动保存。
        </div>
      </div>
    );
  }

  if (teamMode) {
    // 团队模式：每条消息独立显示，带引擎标签
    return (
      <>
        {messages.map((msg, idx) => {
          if (msg.type === 'system') {
            return (
              <div key={idx} className="team-separator">
                <span className="team-separator-text">{msg.content}</span>
              </div>
            );
          }
          return (
            <MessageBubble
              key={idx}
              role={msg.role}
              content={msg.content}
              time={msg.time}
              engine={msg.engine || engine}
              streaming={false}
              thinking={false}
              toolCalls={msg.type === 'tool_call' ? [{ tool: msg.tool || msg.tool_name, input: msg.input || msg.tool_input }] : []}
              showEngineLabel={msg.role === 'assistant'}
            />
          );
        })}
        {streamingContent && (
          <MessageBubble
            role="assistant"
            content={streamingContent}
            streaming={true}
            engine={engine}
            showEngineLabel={true}
          />
        )}
        <div ref={bottomRef} />
      </>
    );
  }

  const groupedMessages = groupMessages(messages, streamingContent, isStreaming);

  return (
    <>
      {groupedMessages.map((msg, idx) => {
        return (
          <MessageBubble
            key={idx}
            role={msg.role}
            content={msg.streamingContent || msg.content}
            time={msg.time}
            engine={engine}
            streaming={msg.streaming}
            thinking={msg.thinking}
            toolCalls={msg.toolCalls}
            tokenInfo={msg.tokenInfo}
          />
        );
      })}
      <div ref={bottomRef} />
    </>
  );
}
