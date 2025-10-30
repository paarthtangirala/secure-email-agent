import { useState, useEffect, useCallback } from 'react';
import axios, { AxiosResponse } from 'axios';

// API client configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Email {
  id: string;
  thread_id: string;
  subject: string;
  sender: string;
  sender_email: string;
  recipients: string[];
  date_received: string;
  body_text: string;
  body_html?: string;
  labels: string[];
  primary_label: string;
  is_important: boolean;
  is_unread: boolean;
  attachments_count?: number;
  classification?: string;
  confidence?: number;
  urgency_level?: string;
  requires_response?: boolean;
}

export interface Thread {
  thread_id: string;
  emails: Email[];
  summary: string;
  tasks: Task[];
  meeting_info?: MeetingInfo;
}

export interface Task {
  task: string;
  due_date: string;
  owner: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  confidence: number;
  source: string;
}

export interface MeetingInfo {
  title: string;
  start_time?: string;
  end_time?: string;
  location: string;
  platform: string;
  attendees: string[];
  description: string;
  confidence: number;
}

export interface ReplyOption {
  type: string;
  subject: string;
  body: string;
  tone: string;
  confidence: number;
}

// Custom hooks
export const useEmails = (page = 1, perPage = 50, filters: any = {}) => {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const fetchEmails = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = {
        page,
        per_page: perPage,
        ...filters,
      };
      
      const response = await api.get('/emails', { params });
      const data = response.data;
      
      setEmails(data.emails);
      setTotalCount(data.total_count);
      setHasMore(data.has_more);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch emails');
    } finally {
      setLoading(false);
    }
  }, [page, perPage, JSON.stringify(filters)]);

  useEffect(() => {
    fetchEmails();
  }, [fetchEmails]);

  return {
    emails,
    loading,
    error,
    totalCount,
    hasMore,
    refetch: fetchEmails,
  };
};

export const useThread = (threadId: string) => {
  const [thread, setThread] = useState<Thread | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThread = useCallback(async () => {
    if (!threadId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(`/threads/${threadId}`);
      setThread(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch thread');
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    fetchThread();
  }, [fetchThread]);

  return {
    thread,
    loading,
    error,
    refetch: fetchThread,
  };
};

export const useReplyGeneration = () => {
  const [fastReplies, setFastReplies] = useState<ReplyOption[]>([]);
  const [smartReply, setSmartReply] = useState<ReplyOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationTime, setGenerationTime] = useState(0);

  const generateReplies = useCallback(async (emailId: string) => {
    setLoading(true);
    setError(null);
    setFastReplies([]);
    setSmartReply(null);
    
    try {
      // Generate fast replies
      const response = await api.post('/reply_suggestions', null, {
        params: { email_id: emailId }
      });
      
      const data = response.data;
      setFastReplies(data.fast_replies);
      setGenerationTime(data.generation_time_ms);
      
      // Poll for smart reply
      if (data.smart_reply_task_id) {
        pollSmartReply(data.smart_reply_task_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate replies');
    } finally {
      setLoading(false);
    }
  }, []);

  const pollSmartReply = async (taskId: string) => {
    const maxAttempts = 30; // 30 seconds max
    let attempts = 0;
    
    const poll = async () => {
      try {
        const response = await api.get(`/reply_suggestions/${taskId}/smart`);
        const data = response.data;
        
        if (data.status === 'completed' && data.result) {
          setSmartReply(data.result);
          return;
        } else if (data.status === 'error') {
          setError(data.error || 'Smart reply generation failed');
          return;
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000); // Poll every second
        }
      } catch (err) {
        console.warn('Smart reply polling failed:', err);
      }
    };
    
    poll();
  };

  return {
    fastReplies,
    smartReply,
    loading,
    error,
    generationTime,
    generateReplies,
  };
};

export const useEmailSync = () => {
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSync = useCallback(async (hoursBack = 24, deltaSync = true) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post('/sync', {
        hours_back: hoursBack,
        delta_sync: deltaSync,
      });
      
      const taskId = response.data.task_id;
      pollSyncStatus(taskId);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start sync');
      setLoading(false);
    }
  }, []);

  const pollSyncStatus = async (taskId: string) => {
    const maxAttempts = 120; // 2 minutes max
    let attempts = 0;
    
    const poll = async () => {
      try {
        const response = await api.get(`/sync/${taskId}/status`);
        const data = response.data;
        
        setSyncStatus(data);
        
        if (data.status === 'completed' || data.status === 'error') {
          setLoading(false);
          return;
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000);
        } else {
          setLoading(false);
          setError('Sync timeout');
        }
      } catch (err) {
        setLoading(false);
        setError('Sync status polling failed');
      }
    };
    
    poll();
  };

  return {
    syncStatus,
    loading,
    error,
    startSync,
  };
};

export const useTaskExtraction = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [complexity, setComplexity] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractTasks = useCallback(async (emailId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post(`/tasks/${emailId}`);
      const data = response.data;
      
      setTasks(data.tasks);
      setComplexity(data.complexity_analysis);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to extract tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    tasks,
    complexity,
    loading,
    error,
    extractTasks,
  };
};

export const useCalendarResponse = () => {
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const processCalendar = useCallback(async (emailId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post('/calendar_autorespond', null, {
        params: { email_id: emailId }
      });
      
      setResponse(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process calendar request');
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    response,
    loading,
    error,
    processCalendar,
  };
};

export const useSearch = () => {
  const [results, setResults] = useState<Email[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: string, limit = 20) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/search', {
        params: { q: query, limit }
      });
      
      setResults(response.data.results);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Search failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const clearSearch = useCallback(() => {
    setResults([]);
    setError(null);
  }, []);

  return {
    results,
    loading,
    error,
    search,
    clearSearch,
  };
};

export const useDashboard = () => {
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/dashboard/overview');
      setOverview(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchOverview, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return {
    overview,
    loading,
    error,
    refetch: fetchOverview,
  };
};

export default api;