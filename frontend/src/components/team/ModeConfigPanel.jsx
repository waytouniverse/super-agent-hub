const ENGINE_NAMES = {
  claude: 'Claude',
  codex: 'Codex',
  hermes: 'Hermes',
};

export default function ModeConfigPanel({
  mode,
  config,
  onChange,
  engines,
}) {
  if (mode === 'serial' || mode === 'parallel') {
    return (
      <div className="mode-config">
        <div className="mode-config-hint">
          {mode === 'serial'
            ? '引擎按选择顺序依次发言，每个引擎可以看到前面引擎的输出。'
            : '所有引擎同时收到相同的问题，各自独立输出，互不影响。'}
        </div>
      </div>
    );
  }

  const maxRounds = config.maxRounds || 3;
  const judgeEngine = config.judgeEngine || '';

  const installedEngines = engines.filter((e) => e.installed);

  return (
    <div className="mode-config">
      <div className="mode-config-row">
        <label className="mode-config-label">最大轮数</label>
        <div className="mode-config-control">
          <input
            type="range"
            min="2"
            max="5"
            value={maxRounds}
            onChange={(e) => onChange({ ...config, maxRounds: parseInt(e.target.value) })}
            className="mode-config-slider"
          />
          <span className="mode-config-value">{maxRounds} 轮</span>
        </div>
        <div className="mode-config-hint">
          辩论达到最大轮数后将强制结束，取最后一轮结论。
        </div>
      </div>

      <div className="mode-config-row">
        <label className="mode-config-label">裁判引擎</label>
        <select
          className="mode-config-select"
          value={judgeEngine}
          onChange={(e) => onChange({ ...config, judgeEngine: e.target.value })}
        >
          <option value="">不启用（仅按轮数结束）</option>
          {installedEngines.map((e) => (
            <option key={e.name} value={e.name}>
              {ENGINE_NAMES[e.name] || e.display_name}
            </option>
          ))}
        </select>
        <div className="mode-config-hint">
          裁判引擎每轮评估讨论质量，决定 CONTINUE（继续）或 CONCLUDE（结束）。
        </div>
      </div>
    </div>
  );
}
