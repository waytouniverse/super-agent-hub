import { useState, useRef, useEffect } from 'react';
import { Check, ChevronDown, Send, Shield, ShieldQuestion, Square } from 'lucide-react';

const permissionOptions = [
  {
    key: 'ask',
    label: '请求批准',
    desc: '编辑文件和运行命令前需要你确认',
    icon: ShieldQuestion,
    allowWrites: false,
  },
  {
    key: 'full',
    label: '完全访问权限',
    desc: '允许写入项目文件夹并运行项目命令',
    icon: Shield,
    allowWrites: true,
  },
];

export default function ChatInput({
  onSend,
  onStop,
  streaming,
  allowProjectWrites = false,
  onAllowProjectWritesChange,
}) {
  const [value, setValue] = useState('');
  const [permissionOpen, setPermissionOpen] = useState(false);
  const textareaRef = useRef(null);
  const permissionRef = useRef(null);
  const selectedPermission = allowProjectWrites ? permissionOptions[1] : permissionOptions[0];
  const SelectedIcon = selectedPermission.icon;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [value]);

  useEffect(() => {
    const handlePointerDown = (event) => {
      if (!permissionRef.current?.contains(event.target)) {
        setPermissionOpen(false);
      }
    };
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, []);

  const handleSend = () => {
    if (!value.trim() || streaming) return;
    onSend(value.trim());
    setValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-wrapper">
      <textarea
        ref={textareaRef}
        className="chat-input"
        placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        disabled={streaming}
      />
      <div className="chat-input-actions">
        <div className="chat-permission" ref={permissionRef}>
          <button
            type="button"
            className={`chat-permission-btn${allowProjectWrites ? ' elevated' : ''}`}
            onClick={() => setPermissionOpen(prev => !prev)}
            title={selectedPermission.label}
            disabled={streaming}
          >
            <SelectedIcon size={16} />
            <ChevronDown size={13} />
          </button>
          {permissionOpen && (
            <div className="chat-permission-menu">
              <div className="chat-permission-menu-header">
                <span>应如何批准 Agent 操作？</span>
                <span>了解更多</span>
              </div>
              {permissionOptions.map((option) => {
                const Icon = option.icon;
                const selected = option.key === selectedPermission.key;
                return (
                  <button
                    key={option.key}
                    type="button"
                    className={`chat-permission-option${selected ? ' selected' : ''}`}
                    onClick={() => {
                      onAllowProjectWritesChange?.(option.allowWrites);
                      setPermissionOpen(false);
                    }}
                  >
                    <Icon size={18} />
                    <span>
                      <strong>{option.label}</strong>
                      <small>{option.desc}</small>
                    </span>
                    {selected && <Check size={16} />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        {streaming ? (
          <button className="chat-stop-btn" onClick={onStop} title="停止">
            <Square size={16} fill="white" />
          </button>
        ) : (
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!value.trim()}
            title="发送"
          >
            <Send size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
