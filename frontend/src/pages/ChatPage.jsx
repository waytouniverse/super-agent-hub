import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import MessageList from '../components/MessageList';
import ChatInput from '../components/ChatInput';
import TokenBadge from '../components/TokenBadge';
import { useProject } from '../contexts/ProjectContext';
import { useEngines } from '../hooks/useEngines';
import { fetchSession } from '../api';

export default function ChatPage() {
  const { engine } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const resumeId = searchParams.get('resume');

  const { engines } = useEngines();
  const { projectPath, allowProjectWrites, setAllowProjectWrites, setProject } = useProject();
  const engineInfo = engines.find(e => e.name === engine) || {};

  const [messages, setMessages] = useState([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [sessionUsage, setSessionUsage] = useState(null);

  const wsRef = useRef(null);
  const streamingRef = useRef('');
  const sessionIdRef = useRef('');

  // 恢复历史会话
  useEffect(() => {
    if (!resumeId) return;
    fetchSession(resumeId).then(data => {
      if (data?.messages) {
        const formatted = data.messages.map(m => ({
          role: m.role,
          type: m.type,
          content: m.content,
          tool: m.tool_name,
          input: m.tool_input,
          time: m.created_at ? new Date(m.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '',
        }));
        setMessages(formatted);
        setSessionId(resumeId);
        sessionIdRef.current = resumeId;
        if (data.session?.cwd) {
          setProject(data.session.cwd).catch(() => {});
        }
      }
    }).catch(() => {});
  }, [resumeId, setProject]);

  // 切换引擎时断开旧连接
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [engine]);

  const connectAndSend = useCallback((prompt) => {
    if (!projectPath) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        type: 'text',
        content: '*请先在左侧选择一个项目文件夹。*',
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      }]);
      return;
    }

    // 关闭旧连接
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/chat/${engine}`;
    const socket = new WebSocket(url);

    wsRef.current = socket;
    setIsStreaming(true);
    setStreamingContent('');
    streamingRef.current = '';

    const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

    socket.onopen = () => {
      socket.send(JSON.stringify({
        prompt,
        resume_session: sessionIdRef.current,
        cwd: projectPath,
        permission_mode: allowProjectWrites ? 'acceptEdits' : 'default',
        allow_project_tools: allowProjectWrites,
      }));
      setMessages(prev => [...prev, {
        role: 'user',
        type: 'text',
        content: prompt,
        time: now,
      }]);
    };

    const flushStreamingContent = (suffix = '') => {
      if (!streamingRef.current) {
        setStreamingContent('');
        return;
      }

      const content = streamingRef.current + suffix;
      setMessages(prev => [...prev, {
        role: 'assistant',
        type: 'text',
        content,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      }]);
      streamingRef.current = '';
      setStreamingContent('');
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'session_created':
          setSessionId(data.session_id);
          sessionIdRef.current = data.session_id;
          break;

        case 'text_stream':
          streamingRef.current += data.content;
          setStreamingContent(streamingRef.current);
          break;

        case 'tool_call':
          setMessages(prev => [...prev, {
            role: 'assistant',
            type: 'tool_call',
            tool: data.tool,
            input: data.input,
          }]);
          break;

        case 'text':
          setStreamingContent('');
          setMessages(prev => [...prev, {
            role: 'assistant',
            type: 'text',
            content: data.content || streamingRef.current,
            time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
          }]);
          streamingRef.current = '';
          break;

        case 'done':
          if (data.usage) {
            setSessionUsage(data.usage);
          }
          flushStreamingContent();
          setIsStreaming(false);
          break;

        case 'error':
          flushStreamingContent();
          setMessages(prev => [...prev, {
            role: 'assistant',
            type: 'text',
            content: `*错误: ${data.content}*`,
          }]);
          setIsStreaming(false);
          break;
      }
    };

    socket.onerror = () => {
      if (wsRef.current === socket) {
        flushStreamingContent(' *[连接中断]*');
        setIsStreaming(false);
      }
    };

    socket.onclose = () => {
      if (wsRef.current === socket) {
        flushStreamingContent();
        setIsStreaming(false);
        wsRef.current = null;
      }
    };
  }, [allowProjectWrites, engine, projectPath]);

  const handleStop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsStreaming(false);
      if (streamingRef.current) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          type: 'text',
          content: streamingRef.current + ' *[已停止]*',
          time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        }]);
        streamingRef.current = '';
        setStreamingContent('');
      }
    }
  }, []);

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div className="chat-header-content">
          <div className="chat-header-left">
            <span className={`message-avatar ${engine}`}>
              {engineInfo.display_name?.charAt(0) || engine?.charAt(0)?.toUpperCase()}
            </span>
            <span className="chat-header-engine">
              {engineInfo.display_name || engine}
            </span>
            {engineInfo.models?.[0] && (
              <span className="chat-header-model">{engineInfo.models[0]}</span>
            )}
          </div>
          <div className="chat-header-right">
            {sessionUsage && (
              <TokenBadge
                inputTokens={sessionUsage.input_tokens}
                outputTokens={sessionUsage.output_tokens}
                costCny={sessionUsage.cost_cny}
              />
            )}
            <button
              className="chat-header-btn"
              onClick={() => navigate('/')}
            >
              新建对话 <ChevronDown size={14} />
            </button>
          </div>
        </div>
      </div>

      <div className="chat-messages">
        <div className="chat-content-column">
          <MessageList
            messages={messages}
            streamingContent={streamingContent}
            isStreaming={isStreaming}
            engine={engine}
          />
        </div>
      </div>

      <div className="chat-input-area">
        <div className="chat-content-column">
          <ChatInput
            onSend={connectAndSend}
            onStop={handleStop}
            streaming={isStreaming}
            allowProjectWrites={allowProjectWrites}
            onAllowProjectWritesChange={setAllowProjectWrites}
          />
        </div>
      </div>
    </div>
  );
}
