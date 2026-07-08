import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { chooseProjectFolder, validateProject } from '../api';

const STORAGE_KEY = 'agent-hub-selected-project';
const PROJECTS_STORAGE_KEY = 'agent-hub-project-list';
const WRITE_ACCESS_KEY = 'agent-hub-project-write-access';
const LEGACY_STORAGE_KEY = 'agent-hub-project';
const ProjectContext = createContext(null);

function projectNameFromPath(path) {
  if (!path) return '未选择项目';
  const normalized = path.replace(/\/+$/, '');
  return normalized.split('/').pop() || normalized;
}

function readProjectList() {
  try {
    const parsed = JSON.parse(localStorage.getItem(PROJECTS_STORAGE_KEY) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function normalizeProject(project) {
  return {
    path: project.path,
    name: project.name || projectNameFromPath(project.path),
  };
}

export function ProjectProvider({ children }) {
  const [projectPath, setProjectPath] = useState(() => localStorage.getItem(STORAGE_KEY) || '');
  const [projectName, setProjectName] = useState(() => projectNameFromPath(localStorage.getItem(STORAGE_KEY) || ''));
  const [projects, setProjects] = useState(readProjectList);
  const [allowProjectWrites, setAllowProjectWritesState] = useState(() => localStorage.getItem(WRITE_ACCESS_KEY) === 'true');
  const [loading] = useState(false);

  useEffect(() => {
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  }, []);

  const applyProject = useCallback((project) => {
    const normalized = normalizeProject(project);
    setProjectPath(normalized.path);
    setProjectName(normalized.name);
    localStorage.setItem(STORAGE_KEY, normalized.path);
    setProjects((prev) => {
      const next = [
        normalized,
        ...prev.filter(item => item.path !== normalized.path),
      ].slice(0, 8);
      localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
    return normalized;
  }, []);

  const setProject = useCallback(async (path) => {
    const project = await validateProject(path);
    return applyProject(project);
  }, [applyProject]);

  const chooseProject = useCallback(async () => {
    const project = await chooseProjectFolder();
    return applyProject(project);
  }, [applyProject]);

  const selectProject = useCallback((project) => applyProject(project), [applyProject]);

  const removeProject = useCallback((path) => {
    setProjects((prev) => {
      const next = prev.filter(item => item.path !== path);
      localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
    if (projectPath === path) {
      setProjectPath('');
      setProjectName(projectNameFromPath(''));
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [projectPath]);

  const setAllowProjectWrites = useCallback((allowed) => {
    setAllowProjectWritesState(allowed);
    localStorage.setItem(WRITE_ACCESS_KEY, allowed ? 'true' : 'false');
  }, []);

  const value = useMemo(() => ({
    projectPath,
    projectName,
    projects,
    allowProjectWrites,
    loading,
    setProject,
    chooseProject,
    selectProject,
    removeProject,
    setAllowProjectWrites,
  }), [
    allowProjectWrites,
    chooseProject,
    loading,
    projectName,
    projectPath,
    projects,
    removeProject,
    selectProject,
    setAllowProjectWrites,
    setProject,
  ]);

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used inside ProjectProvider');
  }
  return context;
}
