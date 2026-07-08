import { useState } from 'react';
import { ChevronRight, Terminal } from 'lucide-react';

export default function ToolCallCard({ tool, input }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="tool-call-card">
      <div className="tool-call-header" onClick={() => setExpanded(!expanded)}>
        <ChevronRight
          size={14}
          style={{
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 150ms ease',
          }}
        />
        <Terminal size={14} />
        <span className="tool-call-name">{tool}</span>
      </div>
      {expanded && (
        <div className="tool-call-input">{typeof input === 'string' ? input : JSON.stringify(input, null, 2)}</div>
      )}
    </div>
  );
}
