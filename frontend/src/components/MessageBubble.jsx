import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ToolCallCard from './ToolCallCard';

const LOCAL_IMAGE_EXTENSIONS = /\.(png|jpe?g|gif|webp|bmp|svg)(?:[?#].*)?$/i;

function resolveMarkdownImageSrc(src = '') {
  if (!src) return src;
  if (/^(https?:|data:|blob:)/i.test(src)) return src;
  if (src.startsWith('/api/') || src.startsWith('/assets/')) return src;

  let localPath = src.startsWith('file://') ? src.slice(7) : src;
  try {
    localPath = decodeURI(localPath);
  } catch {
    // Keep the original string when it contains malformed percent escapes.
  }
  if (localPath.startsWith('/') && LOCAL_IMAGE_EXTENSIONS.test(localPath)) {
    return `/api/files/preview?path=${encodeURIComponent(localPath)}`;
  }

  return src;
}

const ENGINE_DISPLAY = {
  claude: 'Claude Code',
  codex: 'Codex',
  hermes: 'Hermes',
};

const ENGINE_AVATAR = {
  claude: 'C',
  codex: 'X',
  hermes: 'H',
};

function getEngineDisplay(engine) {
  return ENGINE_DISPLAY[engine] || engine.charAt(0).toUpperCase() + engine.slice(1);
}

function getEngineAvatar(engine) {
  return ENGINE_AVATAR[engine] || engine.charAt(0).toUpperCase();
}

export default function MessageBubble({
  role,
  content,
  time,
  engine = 'claude',
  streaming = false,
  thinking = false,
  toolCalls = [],
  tokenInfo,
  showEngineLabel = false,
}) {
  if (role === 'user') {
    return (
      <div className="message-row user">
        <div className="message-bubble">
          <div className="message-content">{content}</div>
          {time && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, textAlign: 'right' }}>{time}</div>}
        </div>
      </div>
    );
  }

  const engineClass = ['claude', 'codex', 'hermes'].includes(engine) ? engine : 'team';

  return (
    <div className="message-row assistant">
      <span className={`message-avatar ${engineClass}`}>
        {getEngineAvatar(engine)}
      </span>
      <div className="message-bubble">
        <div className="message-header">
          <span className="message-sender">
            {showEngineLabel ? getEngineDisplay(engine) : (engine === 'claude' ? 'Claude Code' : engine === 'codex' ? 'Codex' : 'Hermes')}
          </span>
          {time && <span className="message-time">{time}</span>}
        </div>
        {toolCalls?.length > 0 && (
          <div className="message-tools">
            {toolCalls.map((toolCall, idx) => (
              <ToolCallCard
                key={`${toolCall.tool}-${idx}`}
                tool={toolCall.tool}
                input={toolCall.input}
              />
            ))}
          </div>
        )}
        {thinking ? (
          <div className="message-content stream-cursor waiting-cursor" aria-live="polite" />
        ) : content ? (
          <div className={`message-content${streaming ? ' stream-cursor' : ''}`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                img: ({ node, src, alt, ...props }) => (
                  <img
                    {...props}
                    src={resolveMarkdownImageSrc(src)}
                    alt={alt || ''}
                    loading="lazy"
                  />
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        ) : null}
        {tokenInfo && (
          <div className="message-footer">
            <span className="message-token-info">
              {tokenInfo.input && `in ${tokenInfo.input}`}
              {tokenInfo.output && ` · out ${tokenInfo.output}`}
              {tokenInfo.cost && ` · $${tokenInfo.cost}`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
