import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { 
  Plus, 
  FolderOpen, 
  Users, 
  Calendar, 
  CheckCircle, 
  Clock,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { projectsAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  
  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsAPI.getAll(),
  });

  const stats = [
    {
      name: 'Active Projects',
      value: projects?.data?.length || 0,
      icon: FolderOpen,
      color: 'bg-blue-500',
    },
    {
      name: 'Team Members',
      value: projects?.data?.reduce((acc: number, project: any) => acc + (project.team_members?.length || 0), 0) || 0,
      icon: Users,
      color: 'bg-green-500',
    },
    {
      name: 'Active Sprints',
      value: projects?.data?.filter((p: any) => p.current_sprint).length || 0,
      icon: Calendar,
      color: 'bg-purple-500',
    },
    {
      name: 'Completed Tasks',
      value: projects?.data?.reduce((acc: number, project: any) => acc + (project.tasks_summary?.done || 0), 0) || 0,
      icon: CheckCircle,
      color: 'bg-emerald-500',
    },
  ];

  const recentActivities = [
    {
      id: 1,
      type: 'task_completed',
      message: 'Task "Implement user authentication" completed by AI Developer',
      time: '2 hours ago',
      project: 'E-commerce Platform',
    },
    {
      id: 2,
      type: 'sprint_started',
      message: 'Sprint "Sprint 3 - User Management" started',
      time: '1 day ago',
      project: 'E-commerce Platform',
    },
    {
      id: 3,
      type: 'team_member_added',
      message: 'AI QA Engineer added to team',
      time: '2 days ago',
      project: 'Mobile App',
    },
    {
      id: 4,
      type: 'project_created',
      message: 'New project "Analytics Dashboard" created',
      time: '3 days ago',
      project: 'Analytics Dashboard',
    },
  ];

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'task_completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'sprint_started':
        return <Calendar className="h-5 w-5 text-blue-500" />;
      case 'team_member_added':
        return <Users className="h-5 w-5 text-purple-500" />;
      case 'project_created':
        return <FolderOpen className="h-5 w-5 text-orange-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user?.full_name}!</h1>
          <p className="text-gray-600">Here's what's happening with your agile team today.</p>
        </div>
        <Link
          to="/projects/new"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Project
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.name}
              className="bg-white overflow-hidden shadow rounded-lg"
            >
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`inline-flex items-center justify-center h-8 w-8 rounded-md ${stat.color} text-white`}>
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        {stat.name}
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {stat.value}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Projects and Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Projects */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Recent Projects
            </h3>
            <div className="space-y-3">
              {projects?.data?.slice(0, 5).map((project: any) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="block p-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">
                        {project.name}
                      </h4>
                      <p className="text-xs text-gray-500">
                        {project.team_members?.length || 0} team members
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        project.status === 'active' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {project.status}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
              {(!projects?.data || projects.data.length === 0) && (
                <div className="text-center py-8 text-gray-500">
                  <FolderOpen className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No projects yet</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Get started by creating your first project.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Recent Activity
            </h3>
            <div className="space-y-3">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-1">
                    {getActivityIcon(activity.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900">{activity.message}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs text-gray-500">{activity.time}</span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-primary-600">{activity.project}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* AI Team Insights */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            AI Team Insights
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <TrendingUp className="mx-auto h-8 w-8 text-blue-600 mb-2" />
              <h4 className="text-sm font-medium text-blue-900">Team Velocity</h4>
              <p className="text-2xl font-bold text-blue-600">24.5</p>
              <p className="text-xs text-blue-600">story points/sprint</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <CheckCircle className="mx-auto h-8 w-8 text-green-600 mb-2" />
              <h4 className="text-sm font-medium text-green-900">Sprint Completion</h4>
              <p className="text-2xl font-bold text-green-600">87%</p>
              <p className="text-xs text-green-600">on track</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <Users className="mx-auto h-8 w-8 text-purple-600 mb-2" />
              <h4 className="text-sm font-medium text-purple-900">AI Agents</h4>
              <p className="text-2xl font-bold text-purple-600">6</p>
              <p className="text-xs text-purple-600">active team members</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;