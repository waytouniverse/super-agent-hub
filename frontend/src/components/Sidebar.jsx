import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { MessageSquare, Activity, Clock, Settings, Sun, Moon, FolderOpen, X } from 'lucide-react';
import { useProject } from '../contexts/ProjectContext';
import { useTheme } from '../contexts/ThemeContext';

export default function Sidebar() {
  const {
    projectName,
    projectPath,
    projects,
    setProject,
    chooseProject,
    selectProject,
    removeProject,
  } = useProject();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [projectDraft, setProjectDraft] = useState(projectPath);
  const [projectOpen, setProjectOpen] = useState(false);
  const [projectError, setProjectError] = useState('');

  useEffect(() => {
    if (!projectOpen) {
      setProjectDraft(projectPath);
    }
  }, [projectOpen, projectPath]);

  const handleProjectSubmit = async (event) => {
    event.preventDefault();
    setProjectError('');
    if (!projectDraft.trim() || projectDraft === projectPath) {
      return;
    }
    try {
      const project = await setProject(projectDraft);
      setProjectDraft(project.path);
      setProjectOpen(false);
    } catch (error) {
      setProjectError(error.message || '项目目录不可用');
    }
  };

  const handleProjectInputBlur = async () => {
    if (!projectDraft.trim() || projectDraft === projectPath) {
      return;
    }
    setProjectError('');
    try {
      const project = await setProject(projectDraft);
      setProjectDraft(project.path);
      setProjectOpen(false);
    } catch (error) {
      setProjectError(error.message || '项目目录不可用');
    }
  };

  const handleChooseProject = async () => {
    setProjectError('');
    try {
      const project = await chooseProject();
      setProjectDraft(project.path);
      setProjectOpen(false);
    } catch (error) {
      setProjectError(error.message || '无法选择文件夹');
    }
  };

  const handleSelectProject = (project) => {
    selectProject(project);
    setProjectDraft(project.path);
    setProjectError('');
    setProjectOpen(false);
    navigate('/chat/claude');
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="sidebar-logo-dot" />
        <span>Agent Hub</span>
      </div>

      <div className="sidebar-project">
        <button
          className="sidebar-project-trigger"
          onClick={() => {
            setProjectDraft(projectPath);
            setProjectOpen(prev => !prev);
          }}
          title={projectPath}
        >
          <FolderOpen size={16} />
          <span>
            <span className="sidebar-project-label">项目</span>
            <span className="sidebar-project-name">{projectName}</span>
          </span>
        </button>
        {projectOpen && (
          <form className="sidebar-project-panel" onSubmit={handleProjectSubmit}>
            <button
              type="button"
              className="sidebar-project-pick-btn"
              onClick={handleChooseProject}
            >
              <FolderOpen size={14} />
              <span>选择文件夹</span>
            </button>
            {projects.length > 0 && (
              <div className="sidebar-project-list">
                <div className="sidebar-project-list-title">最近项目</div>
                {projects.map((project) => (
                  <div
                    key={project.path}
                    className={`sidebar-project-list-item${project.path === projectPath ? ' active' : ''}`}
                  >
                    <button
                      type="button"
                      className="sidebar-project-list-main"
                      onClick={() => handleSelectProject(project)}
                      title={project.path}
                    >
                      <span className="sidebar-project-list-name">{project.name}</span>
                      <span className="sidebar-project-list-path">{project.path}</span>
                    </button>
                    <button
                      type="button"
                      className="sidebar-project-remove"
                      onClick={() => removeProject(project.path)}
                      title="移除项目"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <input
              className="sidebar-project-input"
              value={projectDraft}
              onChange={(event) => setProjectDraft(event.target.value)}
              onBlur={handleProjectInputBlur}
              placeholder="或粘贴文件夹路径"
            />
            {projectError && <div className="sidebar-project-error">{projectError}</div>}
          </form>
        )}
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/chat/claude"
          className={({ isActive }) =>
            `sidebar-nav-item${isActive ? ' active' : ''}`
          }
        >
          <MessageSquare size={16} />
          <span>对话</span>
        </NavLink>
        <NavLink
          to="/stats"
          className={({ isActive }) =>
            `sidebar-nav-item${isActive ? ' active' : ''}`
          }
        >
          <Activity size={16} />
          <span>Token 统计</span>
        </NavLink>
        <NavLink
          to="/sessions"
          className={({ isActive }) =>
            `sidebar-nav-item${isActive ? ' active' : ''}`
          }
        >
          <Clock size={16} />
          <span>会话历史</span>
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `sidebar-nav-item${isActive ? ' active' : ''}`
          }
        >
          <Settings size={16} />
          <span>设置</span>
        </NavLink>
      </nav>

      <div style={{ marginTop: 'auto', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--border-primary)' }}>
        <button
          className="sidebar-nav-item"
          onClick={toggleTheme}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer' }}
          title={theme === 'dark' ? '切换浅色模式' : '切换深色模式'}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          <span>{theme === 'dark' ? '浅色模式' : '深色模式'}</span>
        </button>
      </div>
    </aside>
  );
}
