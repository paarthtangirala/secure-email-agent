import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  Button,
  Divider,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  Summarize,
  TrendingUp,
  Schedule,
  Assignment,
  Person,
  Email,
  Refresh,
} from '@mui/icons-material';
import { useThread } from '../../hooks/useApi';

interface SummaryTabProps {
  emailId: string;
  threadId: string | null;
  onTasksFound?: () => void;
  onMeetingFound?: () => void;
}

const SummaryTab: React.FC<SummaryTabProps> = ({
  emailId,
  threadId,
  onTasksFound,
  onMeetingFound,
}) => {
  const [emailData, setEmailData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { thread, loading: threadLoading } = useThread(threadId || '');

  // Fetch email-specific data
  useEffect(() => {
    fetchEmailData();
  }, [emailId]);

  // Notify parent about found content
  useEffect(() => {
    if (thread?.tasks && thread.tasks.length > 0 && onTasksFound) {
      onTasksFound();
    }
    if (thread?.meeting_info && onMeetingFound) {
      onMeetingFound();
    }
  }, [thread, onTasksFound, onMeetingFound]);

  const fetchEmailData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // In real implementation, fetch email details
      // For now, simulate data
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setEmailData({
        sentiment: 0.2, // Slightly positive
        importance: 0.8, // High importance
        urgency: 'medium',
        responseRequired: true,
        estimatedReadTime: '2 min',
        keyTopics: ['project update', 'deadline', 'approval needed'],
      });
    } catch (err: any) {
      setError('Failed to analyze email');
    } finally {
      setLoading(false);
    }
  };

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment > 0.3) return { label: 'Positive', color: 'success' as const };
    if (sentiment < -0.3) return { label: 'Negative', color: 'error' as const };
    return { label: 'Neutral', color: 'info' as const };
  };

  const getImportanceLevel = (importance: number) => {
    if (importance > 0.7) return { label: 'High', color: 'error' as const };
    if (importance > 0.4) return { label: 'Medium', color: 'warning' as const };
    return { label: 'Low', color: 'success' as const };
  };

  if (loading || threadLoading) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Analyzing email content...
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
          onClick={fetchEmailData}
          fullWidth
        >
          Retry Analysis
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
      {/* Thread Summary */}
      {thread?.summary && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Summarize sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6">Thread Summary</Typography>
            </Box>
            <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
              {thread.summary}
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Email Analysis */}
      {emailData && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <TrendingUp sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6">Email Analysis</Typography>
            </Box>

            {/* Metrics Grid */}
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 2 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Importance
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                  <LinearProgress
                    variant="determinate"
                    value={emailData.importance * 100}
                    color={getImportanceLevel(emailData.importance).color}
                    sx={{ flexGrow: 1, mr: 1 }}
                  />
                  <Chip
                    label={getImportanceLevel(emailData.importance).label}
                    size="small"
                    color={getImportanceLevel(emailData.importance).color}
                  />
                </Box>
              </Box>

              <Box>
                <Typography variant="caption" color="text.secondary">
                  Sentiment
                </Typography>
                <Box sx={{ mt: 0.5 }}>
                  <Chip
                    label={getSentimentLabel(emailData.sentiment).label}
                    size="small"
                    color={getSentimentLabel(emailData.sentiment).color}
                    variant="outlined"
                  />
                </Box>
              </Box>
            </Box>

            {/* Quick Facts */}
            <List dense>
              <ListItem>
                <ListItemIcon>
                  <Schedule fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="Read Time"
                  secondary={emailData.estimatedReadTime}
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <Assignment fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="Response Required"
                  secondary={emailData.responseRequired ? 'Yes' : 'No'}
                />
              </ListItem>

              <ListItem>
                <ListItemIcon>
                  <TrendingUp fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="Urgency"
                  secondary={emailData.urgency}
                />
              </ListItem>
            </List>

            {/* Key Topics */}
            {emailData.keyTopics && emailData.keyTopics.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                  Key Topics
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {emailData.keyTopics.map((topic: string, index: number) => (
                    <Chip
                      key={index}
                      label={topic}
                      size="small"
                      variant="outlined"
                      color="primary"
                    />
                  ))}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Quick Actions
          </Typography>

          {thread?.tasks && thread.tasks.length > 0 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                {thread.tasks.length} task{thread.tasks.length !== 1 ? 's' : ''} detected in this email.
              </Typography>
            </Alert>
          )}

          {thread?.meeting_info && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                Meeting invitation detected with {Math.round(thread.meeting_info.confidence * 100)}% confidence.
              </Typography>
            </Alert>
          )}

          {emailData?.responseRequired && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2">
                This email appears to require a response.
              </Typography>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Context & History */}
      {thread?.emails && thread.emails.length > 1 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Email sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6">Conversation Context</Typography>
            </Box>

            <List dense>
              <ListItem>
                <ListItemIcon>
                  <Person fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="Participants"
                  secondary={`${thread.emails.length} emails in conversation`}
                />
              </ListItem>

              <ListItem>
                <ListItemIcon>
                  <Schedule fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="Duration"
                  secondary="Active conversation"
                />
              </ListItem>
            </List>

            {/* Recent Activity */}
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, mb: 1, display: 'block' }}>
              Recent Activity
            </Typography>
            
            {thread.emails.slice(-3).map((email, index) => (
              <Box key={email.id} sx={{ mb: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {email.sender.split('<')[0].trim() || email.sender_email}
                </Typography>
                <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                  {email.subject || '(No subject)'}
                </Typography>
                {index < 2 && <Divider sx={{ my: 1 }} />}
              </Box>
            ))}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default SummaryTab;