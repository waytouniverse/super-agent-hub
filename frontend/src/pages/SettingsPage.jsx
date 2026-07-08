import { useState, useEffect, useCallback } from 'react';
import { useEngines } from '../hooks/useEngines';

export default function SettingsPage() {
  const { engines } = useEngines();

  return (
    <div className="settings-page">
      <h1 className="settings-page-title">设置</h1>

      <div className="settings-section">
        <div className="settings-section-title">引擎配置</div>
        {engines.map((e) => (
          <div key={e.name} className="settings-field">
            <div>
              <div className="settings-field-label">{e.display_name}</div>
              <div className="settings-field-desc">
                {e.installed ? (e.executable || '已安装') : '未安装'}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
              {e.installed && e.models?.length > 0 && (
                <select className="settings-select" defaultValue={e.models[0]}>
                  {e.models.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              )}
              <span
                style={{
                  fontSize: 12,
                  color: e.installed ? 'var(--accent-cyan)' : 'var(--text-muted)',
                }}
              >
                {e.installed ? '已连接' : '未安装'}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="settings-section">
        <div className="settings-section-title">关于</div>
        <div className="settings-field">
          <div>
            <div className="settings-field-label">Agent Hub</div>
            <div className="settings-field-desc">
              统一 AI Agent 工作台 · v0.1.0
            </div>
          </div>
        </div>
        <div className="settings-field">
          <div>
            <div className="settings-field-label">数据目录</div>
            <div className="settings-field-desc">
              ~/.agent-hub/
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
