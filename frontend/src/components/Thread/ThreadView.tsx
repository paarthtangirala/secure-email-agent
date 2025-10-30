import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Avatar,
  Divider,
  IconButton,
  Collapse,
  Alert,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  ExpandMore,
  ExpandLess,
  Reply,
  Forward,
  MoreVert,
  Person,
  Schedule,
  AttachFile,
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import { useThread, Email } from '../../hooks/useApi';

interface ThreadViewProps {
  threadId: string;
  selectedEmailId: string | null;
  onEmailSelect: (emailId: string) => void;
}

const ThreadView: React.FC<ThreadViewProps> = ({
  threadId,
  selectedEmailId,
  onEmailSelect,
}) => {
  const [expandedEmails, setExpandedEmails] = useState<Record<string, boolean>>({});
  const { thread, loading, error } = useThread(threadId);

  // Auto-expand the selected email and latest email
  useEffect(() => {
    if (thread?.emails) {
      const newExpanded: Record<string, boolean> = {};
      
      // Expand selected email
      if (selectedEmailId) {
        newExpanded[selectedEmailId] = true;
      }
      
      // Expand latest email if nothing is selected
      if (!selectedEmailId && thread.emails.length > 0) {
        const latestEmail = thread.emails[thread.emails.length - 1];
        newExpanded[latestEmail.id] = true;
      }
      
      setExpandedEmails(newExpanded);
    }
  }, [thread, selectedEmailId]);

  const toggleEmailExpansion = (emailId: string) => {
    setExpandedEmails(prev => ({
      ...prev,
      [emailId]: !prev[emailId],
    }));
    onEmailSelect(emailId);
  };

  const formatDate = (dateString: string) => {
    try {
      return format(parseISO(dateString), 'MMM d, yyyy \'at\' h:mm a');
    } catch {
      return dateString;
    }
  };

  const getInitials = (sender: string) => {
    return sender
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const extractSenderName = (sender: string) => {
    const match = sender.match(/^([^<]+)</);
    return match ? match[1].trim() : sender.split('@')[0];
  };

  const extractSenderEmail = (sender: string) => {
    const match = sender.match(/<([^>]+)>/);
    return match ? match[1] : sender;
  };

  const renderEmailCard = (email: Email, index: number) => {
    const isExpanded = expandedEmails[email.id];
    const isSelected = selectedEmailId === email.id;
    const isLatest = index === (thread?.emails.length || 0) - 1;
    
    return (
      <Card
        key={email.id}
        variant={isSelected ? 'elevation' : 'outlined'}
        sx={{
          mb: 2,
          border: isSelected ? '2px solid' : undefined,
          borderColor: isSelected ? 'primary.main' : undefined,
          transition: 'all 0.2s ease',
          '&:hover': {
            elevation: 2,
            transform: 'translateY(-1px)',
          },
        }}
      >
        {/* Email Header */}
        <CardContent
          sx={{
            pb: isExpanded ? 2 : 1,
            cursor: 'pointer',
          }}
          onClick={() => toggleEmailExpansion(email.id)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar
              sx={{
                width: 40,
                height: 40,
                backgroundColor: 'primary.main',
              }}
            >
              <Person />
            </Avatar>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Typography variant="subtitle2" fontWeight="bold" noWrap>
                  {extractSenderName(email.sender)}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {extractSenderEmail(email.sender)}
                </Typography>
                {email.is_unread && (
                  <Chip label="New" size="small" color="primary" />
                )}
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {formatDate(email.date_received)}
                </Typography>
                {email.attachments_count && email.attachments_count > 0 && (
                  <Tooltip title={`${email.attachments_count} attachments`}>
                    <AttachFile fontSize="small" color="action" />
                  </Tooltip>
                )}
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {/* Priority/Urgency indicator */}
              {email.urgency_level && email.urgency_level !== 'normal' && (
                <Chip
                  label={email.urgency_level}
                  size="small"
                  color={
                    email.urgency_level === 'urgent' ? 'error' :
                    email.urgency_level === 'high' ? 'warning' : 'info'
                  }
                />
              )}

              <IconButton size="small">
                {isExpanded ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>
          </Box>

          {/* Subject (always visible) */}
          <Typography
            variant="body1"
            fontWeight={email.is_unread ? 600 : 400}
            sx={{ mt: 1, mb: isExpanded ? 2 : 0 }}
          >
            {email.subject || '(No subject)'}
          </Typography>

          {/* Preview (when collapsed) */}
          {!isExpanded && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                mt: 1,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {email.body_text}
            </Typography>
          )}
        </CardContent>

        {/* Expanded Content */}
        <Collapse in={isExpanded}>
          <CardContent sx={{ pt: 0 }}>
            <Divider sx={{ mb: 2 }} />

            {/* Email Body */}
            <Box
              sx={{
                mb: 2,
                p: 2,
                backgroundColor: 'background.default',
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              {email.body_html ? (
                <Box
                  dangerouslySetInnerHTML={{ __html: email.body_html }}
                  sx={{
                    '& img': { maxWidth: '100%', height: 'auto' },
                    '& a': { color: 'primary.main' },
                    lineHeight: 1.6,
                  }}
                />
              ) : (
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'inherit',
                    lineHeight: 1.6,
                  }}
                >
                  {email.body_text}
                </Typography>
              )}
            </Box>

            {/* Labels */}
            {email.labels && email.labels.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                  Labels:
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {email.labels.map((label, index) => (
                    <Chip
                      key={index}
                      label={label}
                      size="small"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Box>
            )}

            {/* Recipients (if expanded and not just sender) */}
            {email.recipients && email.recipients.length > 1 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                  To: {email.recipients.join(', ')}
                </Typography>
              </Box>
            )}
          </CardContent>

          {/* Actions */}
          <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                startIcon={<Reply />}
                size="small"
                variant="outlined"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle reply
                }}
              >
                Reply
              </Button>
              <Button
                startIcon={<Forward />}
                size="small"
                variant="outlined"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle forward
                }}
              >
                Forward
              </Button>
            </Box>

            <IconButton size="small">
              <MoreVert />
            </IconButton>
          </CardActions>
        </Collapse>
      </Card>
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!thread) {
    return (
      <Box sx={{ textAlign: 'center', p: 4 }}>
        <Typography variant="body1" color="text.secondary">
          Thread not found.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', overflow: 'auto', p: 2 }}>
      {/* Thread Summary */}
      {thread.summary && (
        <Card sx={{ mb: 3, backgroundColor: 'primary.main', color: 'primary.contrastText' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Thread Summary
            </Typography>
            <Typography variant="body2">
              {thread.summary}
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Thread Stats */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h6">
          Conversation ({thread.emails.length} {thread.emails.length === 1 ? 'email' : 'emails'})
        </Typography>
        
        {thread.tasks && thread.tasks.length > 0 && (
          <Chip
            label={`${thread.tasks.length} tasks`}
            size="small"
            color="warning"
            icon={<Schedule />}
          />
        )}
        
        {thread.meeting_info && (
          <Chip
            label="Meeting detected"
            size="small"
            color="info"
            icon={<Schedule />}
          />
        )}
      </Box>

      {/* Emails */}
      <Box>
        {thread.emails.map((email, index) => renderEmailCard(email, index))}
      </Box>
    </Box>
  );
};

export default ThreadView;