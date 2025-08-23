import axios from 'axios';

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const authAPI = {
  login: (credentials: { username: string; password: string }) =>
    api.post('/auth/login', credentials),
  register: (userData: any) => api.post('/auth/register', userData),
  me: () => api.get('/auth/me'),
  refresh: () => api.post('/auth/refresh'),
};

export const projectsAPI = {
  getAll: () => api.get('/projects/'),
  getById: (id: number) => api.get(`/projects/${id}`),
  create: (data: any) => api.post('/projects/', data),
  update: (id: number, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  getDashboard: (id: number) => api.get(`/projects/${id}/dashboard`),
};

export const sprintsAPI = {
  getByProject: (projectId: number) => api.get(`/sprints/project/${projectId}`),
  getById: (id: number) => api.get(`/sprints/${id}`),
  create: (data: any) => api.post('/sprints/', data),
  update: (id: number, data: any) => api.put(`/sprints/${id}`, data),
  delete: (id: number) => api.delete(`/sprints/${id}`),
  getDashboard: (id: number) => api.get(`/sprints/${id}/dashboard`),
};

export const tasksAPI = {
  getByProject: (projectId: number) => api.get(`/tasks/project/${projectId}`),
  getBySprint: (sprintId: number) => api.get(`/tasks/sprint/${sprintId}`),
  getById: (id: number) => api.get(`/tasks/${id}`),
  create: (data: any) => api.post('/tasks/', data),
  update: (id: number, data: any) => api.put(`/tasks/${id}`, data),
  delete: (id: number) => api.delete(`/tasks/${id}`),
  addComment: (taskId: number, data: any) => api.post(`/tasks/${taskId}/comments`, data),
  getComments: (taskId: number) => api.get(`/tasks/${taskId}/comments`),
};

export const teamAPI = {
  getByProject: (projectId: number) => api.get(`/team/project/${projectId}`),
  addMember: (data: any) => api.post('/team/', data),
  removeMember: (id: number) => api.delete(`/team/${id}`),
  updateRole: (id: number, role: string) => api.put(`/team/${id}/role`, { new_role: role }),
  createAIAgent: (projectId: number, role: string, config: string) =>
    api.post('/team/ai-agent', { project_id: projectId, role, agent_config: config }),
  getAIAgents: (projectId: number) => api.get(`/team/ai-agents/project/${projectId}`),
};