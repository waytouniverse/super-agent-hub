import { useState, useCallback, useRef, useEffect } from 'react';

const TRANSIENT_TRANSPORT_MARKERS = [
  'Reconnecting...',
  'Falling back from WebSockets to HTTPS transport',
  'stream disconnected before completion',
  'Connection reset by peer',
];

function isTransientTransportMessage(content = '') {
  return TRANSIENT_TRANSPORT_MARKERS.some((marker) => content.includes(marker));
}

export function useTeamSession() {
  const [mode, setMode] = useState('serial');
  const [modeConfig, setModeConfig] = useState({ maxRounds: 3, judgeEngine: '' });
  const [selectedEngines, setSelectedEngines] = useState([]);
  const [started, setStarted] = useState(false);

  // Session state
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState('');
  const [sessionUsage, setSessionUsage] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);

  // Streaming: per-engine for parallel/debate, single for serial
  const [currentEngine, setCurrentEngine] = useState('');
  const [streamingContents, setStreamingContents] = useState({});
  const streamingRefs = useRef({});

  // Round tracking
  const [currentRound, setCurrentRound] = useState(0);
  const [maxRounds, setMaxRounds] = useState(3);
  const [currentPhase, setCurrentPhase] = useState('');

  // Plan state (consultation mode)
  const [plan, setPlan] = useState(null);
  const [planConfirmed, setPlanConfirmed] = useState(false);

  // Execution state
  const [tasks, setTasks] = useState([]);

  const wsRef = useRef(null);
  const currentEngineRef = useRef('');

  // Reset streaming for a new round/turn
  const resetStreaming = useCallback(() => {
    setStreamingContents({});
    streamingRefs.current = {};
    setCurrentEngine('');
    currentEngineRef.current = '';
  }, []);

  // Toggle engine selection
  const toggleEngine = useCallback((name) => {
    setSelectedEngines(prev => {
      if (prev.includes(name)) return prev.filter(e => e !== name);
      if (prev.length >= 3) return prev;
      return [...prev, name];
    });
  }, []);

  // Start team session
  const handleStart = useCallback(() => {
    if (selectedEngines.length < 2) return;
    setStarted(true);
    setMessages([]);
    resetStreaming();
  }, [selectedEngines, resetStreaming]);

  // Parse WebSocket event
  const handleEvent = useCallback((data) => {
    const now = () => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

    switch (data.type) {
      case 'session_created':
        setSessionId(data.session_id);
        break;

      case 'phase_start':
        setCurrentPhase(data.phase);
        break;

      case 'phase_end':
        setCurrentPhase('');
        break;

      case 'round_start':
        setCurrentRound(data.round);
        setMaxRounds(data.max_rounds);
        setMessages(prev => [...prev, {
          role: 'system', type: 'round_separator',
          content: `第 ${data.round} 轮讨论`,
          round: data.round,
        }]);
        break;

      case 'round_end':
        break;

      case 'engine_start': {
        const eng = data.engine;
        currentEngineRef.current = eng;
        setCurrentEngine(eng);
        // Initialize streaming content for this engine
        streamingRefs.current[eng] = '';
        setStreamingContents(prev => ({ ...prev, [eng]: '' }));
        break;
      }

      case 'text_stream': {
        const eng = data.engine;
        const acc = (streamingRefs.current[eng] || '') + data.content;
        streamingRefs.current[eng] = acc;
        setStreamingContents(prev => ({ ...prev, [eng]: acc }));
        setCurrentEngine(eng);
        break;
      }

      case 'tool_call':
        setMessages(prev => [...prev, {
          role: 'assistant', type: 'tool_call',
          tool: data.tool,
          input: data.input,
          engine: data.engine,
          time: now(),
          phase: data.phase,
          round: data.round,
        }]);
        break;

      case 'engine_done': {
        const eng = data.engine;
        const content = streamingRefs.current[eng] || '';

        if (content) {
          setMessages(prev => {
            const next = [...prev];
            next.push({
              role: 'assistant', type: 'text', content,
              time: now(), engine: eng,
              phase: data.phase, round: data.round,
            });
            return next;
          });
        }
        streamingRefs.current[eng] = '';
        setStreamingContents(prev => ({ ...prev, [eng]: '' }));
        break;
      }

      case 'judge_decision': {
        setMessages(prev => [...prev, {
          role: 'judge', type: 'judge',
          content: data.evaluation || '',
          decision: data.decision,
          finalSummary: data.final_summary || '',
          round: data.round,
        }]);
        break;
      }

      case 'plan_generated':
        setPlan(data.plan);
        setTasks((data.plan?.tasks || []).map((task) => ({
          ...task,
          status: 'pending',
        })));
        setPlanConfirmed(false);
        break;

      case 'task_start':
        setTasks(prev => {
          const exists = prev.some(t => t.id === data.task_id);
          if (exists) {
            return prev.map(t =>
              t.id === data.task_id ? { ...t, status: 'running', title: data.title || t.title, engine: data.engine || t.engine } : t
            );
          }
          return [...prev, {
            id: data.task_id,
            title: data.title || data.task_id,
            engine: data.engine || '',
            status: 'running',
          }];
        });
        break;

      case 'task_done':
        setTasks(prev => prev.map(t =>
          t.id === data.task_id ? { ...t, status: 'done' } : t
        ));
        break;

      case 'task_error':
        setTasks(prev => prev.map(t =>
          t.id === data.task_id ? { ...t, status: 'error', error: data.error } : t
        ));
        break;

      case 'done':
        if (data.usage) {
          setSessionUsage(data.usage);
        }
        setIsStreaming(false);
        setCurrentEngine('');
        break;

      case 'error':
        if (isTransientTransportMessage(data.content || '')) {
          break;
        }
        setMessages(prev => [...prev, {
          role: 'assistant', type: 'text',
          content: `*错误: ${data.content}*`,
          engine: data.engine || 'system',
        }]);
        setIsStreaming(false);
        break;
    }
  }, []);

  // Send message via WebSocket
  const handleSend = useCallback((prompt, projectPath, allowProjectWrites) => {
    if (!projectPath) {
      setMessages(prev => [...prev, {
        role: 'assistant', type: 'text',
        content: '*请先在左侧选择一个项目文件夹。*',
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        engine: 'system',
      }]);
      return;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/chat/team`;
    const socket = new WebSocket(url);
    wsRef.current = socket;

    setIsStreaming(true);
    resetStreaming();

    const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

    socket.onopen = () => {
      socket.send(JSON.stringify({
        prompt,
        engines: selectedEngines,
        mode,
        mode_config: modeConfig,
        cwd: projectPath,
        permission_mode: allowProjectWrites ? 'acceptEdits' : 'default',
        resume_session: sessionId,
      }));
      setMessages(prev => [...prev, {
        role: 'user', type: 'text', content: prompt, time: now,
      }]);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleEvent(data);
      } catch (e) {
        // Ignore parse errors
      }
    };

    socket.onerror = () => {
      if (wsRef.current === socket) {
        setIsStreaming(false);
      }
    };

    socket.onclose = () => {
      if (wsRef.current === socket) {
        setIsStreaming(false);
        wsRef.current = null;
      }
    };
  }, [selectedEngines, mode, modeConfig, sessionId, resetStreaming, handleEvent]);

  const handleStop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsStreaming(false);
    }
  }, []);

  // Send plan confirmation on existing WebSocket (consultation mode)
  const handlePlanConfirm = useCallback((confirmedPlan) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setTasks((confirmedPlan?.tasks || []).map((task) => ({
        ...task,
        status: 'pending',
      })));
      wsRef.current.send(JSON.stringify({
        type: 'plan_confirmed',
        confirmed: true,
        plan: confirmedPlan,
      }));
      setPlanConfirmed(true);
      // Resume streaming mode — execution events will follow
      setIsStreaming(true);
    }
  }, []);

  // Cleanup
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return {
    // Setup
    mode, setMode,
    modeConfig, setModeConfig,
    selectedEngines, toggleEngine, setSelectedEngines,
    started, setStarted, handleStart,
    // Session
    messages, setMessages,
    sessionId, setSessionId,
    sessionUsage, setSessionUsage,
    isStreaming,
    // Streaming
    currentEngine, streamingContents,
    // Round
    currentRound, maxRounds,
    currentPhase, setCurrentPhase,
    // Plan
    plan, setPlan, planConfirmed, setPlanConfirmed,
    // Execution
    tasks, setTasks,
    // Actions
    handleSend, handleStop, handlePlanConfirm, handleEvent,
    wsRef,
  };
}
