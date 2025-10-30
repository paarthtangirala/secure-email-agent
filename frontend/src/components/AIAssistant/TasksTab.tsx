import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Checkbox,
  Chip,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  LinearProgress,
} from '@mui/material';
import {
  Assignment,
  Schedule,
  Person,
  PriorityHigh,
  CheckCircle,
  MoreVert,
  Add,
  Refresh,
} from '@mui/icons-material';
import { format, parseISO, isPast, isToday, isTomorrow } from 'date-fns';
import { useTaskExtraction } from '../../hooks/useApi';

interface TasksTabProps {
  emailId: string;
}

interface Task {
  task: string;
  due_date: string;
  owner: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  confidence: number;
  source: string;
  completed?: boolean;
}

const TasksTab: React.FC<TasksTabProps> = ({ emailId }) => {
  const [completedTasks, setCompletedTasks] = useState<Set<string>>(new Set());
  const { tasks, complexity, loading, error, extractTasks } = useTaskExtraction();

  useEffect(() => {
    if (emailId) {
      extractTasks(emailId);
    }
  }, [emailId, extractTasks]);

  const handleTaskToggle = (taskIndex: number) => {
    const taskId = `${emailId}-${taskIndex}`;
    setCompletedTasks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(taskId)) {
        newSet.delete(taskId);
      } else {
        newSet.add(taskId);
      }
      return newSet;
    });
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'urgent': return <PriorityHigh />;
      case 'high': return <PriorityHigh />;
      default: return <Assignment />;
    }
  };

  const formatDueDate = (dueDateStr: string) => {
    if (dueDateStr === 'none' || !dueDateStr) return 'No due date';
    
    try {
      // Handle relative dates
      if (dueDateStr.includes('today')) return 'Today';
      if (dueDateStr.includes('tomorrow')) return 'Tomorrow';
      if (dueDateStr.includes('friday') || dueDateStr.includes('monday')) {
        return dueDateStr;
      }
      
      // Handle ISO dates
      const date = parseISO(dueDateStr);
      if (isToday(date)) return 'Today';
      if (isTomorrow(date)) return 'Tomorrow';
      if (isPast(date)) return `Overdue (${format(date, 'MMM d')})`;
      return format(date, 'MMM d');
    } catch {
      return dueDateStr;
    }
  };

  const getDueDateStyle = (dueDateStr: string) => {
    if (dueDateStr === 'none' || !dueDateStr) return {};
    
    try {
      const date = parseISO(dueDateStr);
      if (isPast(date)) return { color: 'error.main', fontWeight: 'bold' };
      if (isToday(date)) return { color: 'warning.main', fontWeight: 'bold' };
    } catch {
      // Handle relative dates
      if (dueDateStr.includes('today')) return { color: 'warning.main', fontWeight: 'bold' };
      if (dueDateStr.includes('overdue')) return { color: 'error.main', fontWeight: 'bold' };
    }
    
    return {};
  };

  if (loading) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Extracting tasks from email...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => extractTasks(emailId)}
          fullWidth
        >
          Retry Task Extraction
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
      {/* Complexity Overview */}
      {complexity && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Assignment sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6">Task Overview</Typography>
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 2 }}>
              <Box>
                <Typography variant="h4" color="primary.main">
                  {complexity.total_tasks}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Total Tasks
                </Typography>
              </Box>
              
              <Box>
                <Typography variant="h4" color={
                  complexity.complexity === 'high' ? 'error.main' :
                  complexity.complexity === 'medium' ? 'warning.main' : 'success.main'
                }>
                  {complexity.complexity}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Complexity
                </Typography>
              </Box>
            </Box>

            {complexity.urgent_count > 0 && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  {complexity.urgent_count} urgent task{complexity.urgent_count !== 1 ? 's' : ''} require immediate attention
                </Typography>
              </Alert>
            )}

            {complexity.estimated_hours > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                  Estimated Time
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Schedule sx={{ mr: 1, fontSize: '1rem', color: 'text.secondary' }} />
                  <Typography variant="body2">
                    ~{Math.round(complexity.estimated_hours * 10) / 10} hours
                  </Typography>
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tasks List */}
      {tasks && tasks.length > 0 ? (
        <Card>
          <CardContent sx={{ pb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6">Extracted Tasks</Typography>
              <Chip
                label={`${tasks.filter((_, i) => !completedTasks.has(`${emailId}-${i}`)).length} pending`}
                size="small"
                color="primary"
              />
            </Box>

            <List dense>
              {tasks.map((task, index) => {
                const taskId = `${emailId}-${index}`;
                const isCompleted = completedTasks.has(taskId);
                
                return (
                  <React.Fragment key={index}>
                    <ListItem
                      sx={{
                        opacity: isCompleted ? 0.6 : 1,
                        textDecoration: isCompleted ? 'line-through' : 'none',
                      }}
                    >
                      <ListItemIcon>
                        <Checkbox
                          checked={isCompleted}
                          onChange={() => handleTaskToggle(index)}
                          icon={getPriorityIcon(task.priority)}
                          checkedIcon={<CheckCircle />}
                          color={getPriorityColor(task.priority) as any}
                        />
                      </ListItemIcon>

                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" sx={{ flex: 1 }}>
                              {task.task}
                            </Typography>
                            <Chip
                              label={task.priority}
                              size="small"
                              color={getPriorityColor(task.priority) as any}
                              variant="outlined"
                            />
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 0.5 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <Schedule fontSize="small" color="action" />
                                <Typography
                                  variant="caption"
                                  sx={getDueDateStyle(task.due_date)}
                                >
                                  {formatDueDate(task.due_date)}
                                </Typography>
                              </Box>
                              
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <Person fontSize="small" color="action" />
                                <Typography variant="caption" color="text.secondary">
                                  {task.owner}
                                </Typography>
                              </Box>
                            </Box>

                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="caption" color="text.secondary">
                                Confidence: {Math.round(task.confidence * 100)}%
                              </Typography>
                              <LinearProgress
                                variant="determinate"
                                value={task.confidence * 100}
                                sx={{ flexGrow: 1, height: 4, borderRadius: 2 }}
                                color={task.confidence > 0.8 ? 'success' : task.confidence > 0.6 ? 'warning' : 'error'}
                              />
                            </Box>
                          </Box>
                        }
                      />

                      <ListItemSecondaryAction>
                        <IconButton size="small">
                          <MoreVert />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                    
                    {index < tasks.length - 1 && <Divider />}
                  </React.Fragment>
                );
              })}
            </List>
          </CardContent>

          <CardActions>
            <Button
              startIcon={<Add />}
              size="small"
              color="primary"
              onClick={() => {
                // Handle add custom task
              }}
            >
              Add Custom Task
            </Button>
            
            <Button
              size="small"
              color="primary"
              onClick={() => {
                // Handle export to calendar/task manager
              }}
            >
              Export Tasks
            </Button>
          </CardActions>
        </Card>
      ) : (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <Assignment sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No Tasks Detected
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              This email doesn't appear to contain any actionable tasks.
            </Typography>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={() => extractTasks(emailId)}
            >
              Re-analyze Email
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Task Management Tips */}
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            💡 Task Management Tips
          </Typography>
          <List dense>
            <ListItem sx={{ pl: 0 }}>
              <Typography variant="caption" color="text.secondary">
                • Tasks are automatically extracted using AI analysis
              </Typography>
            </ListItem>
            <ListItem sx={{ pl: 0 }}>
              <Typography variant="caption" color="text.secondary">
                • Check off completed tasks to track progress
              </Typography>
            </ListItem>
            <ListItem sx={{ pl: 0 }}>
              <Typography variant="caption" color="text.secondary">
                • Red dates indicate overdue or urgent items
              </Typography>
            </ListItem>
          </List>
        </CardContent>
      </Card>
    </Box>
  );
};

export default TasksTab;