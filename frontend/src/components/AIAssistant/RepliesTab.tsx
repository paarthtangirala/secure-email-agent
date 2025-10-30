import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  IconButton,
  Tooltip,
  Skeleton,
  Collapse,
  TextField,
} from '@mui/material';
import {
  Reply,
  ContentCopy,
  Send,
  ThumbUp,
  ThumbDown,
  Edit,
  Refresh,
  AutoAwesome,
  Speed,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import { useReplyGeneration } from '../../hooks/useApi';

interface RepliesTabProps {
  emailId: string;
}

interface ReplyOption {
  type: string;
  subject: string;
  body: string;
  tone: string;
  confidence: number;
}

const RepliesTab: React.FC<RepliesTabProps> = ({ emailId }) => {
  const [selectedReply, setSelectedReply] = useState<number | null>(null);
  const [customizing, setCustomizing] = useState<number | null>(null);
  const [customReply, setCustomReply] = useState('');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  
  const {
    fastReplies,
    smartReply,
    loading,
    error,
    generationTime,
    generateReplies,
  } = useReplyGeneration();

  useEffect(() => {
    if (emailId) {
      generateReplies(emailId);
    }
  }, [emailId, generateReplies]);

  const handleCopyReply = async (reply: ReplyOption, index: number) => {
    try {
      await navigator.clipboard.writeText(reply.body);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Failed to copy text');
    }
  };

  const handleCustomize = (index: number, reply: ReplyOption) => {
    setCustomizing(index);
    setCustomReply(reply.body);
  };

  const handleSaveCustomization = () => {
    // In real implementation, save the customized reply
    setCustomizing(null);
    setCustomReply('');
  };

  const getToneIcon = (tone: string) => {
    switch (tone.toLowerCase()) {
      case 'professional': return '💼';
      case 'friendly': return '😊';
      case 'quick': return '⚡';
      case 'detailed': return '📋';
      case 'action-oriented': return '🎯';
      default: return '💬';
    }
  };

  const getToneColor = (tone: string) => {
    switch (tone.toLowerCase()) {
      case 'professional': return 'primary';
      case 'friendly': return 'success';
      case 'quick': return 'warning';
      case 'detailed': return 'info';
      case 'action-oriented': return 'error';
      default: return 'default';
    }
  };

  const renderReplyCard = (reply: ReplyOption, index: number, isSmartReply = false) => {
    const isSelected = selectedReply === index;
    const isCustomizing = customizing === index;
    const isCopied = copiedIndex === index;

    return (
      <Card
        key={index}
        variant={isSelected ? 'elevation' : 'outlined'}
        sx={{
          mb: 2,
          border: isSelected ? '2px solid' : undefined,
          borderColor: isSelected ? 'primary.main' : undefined,
          position: 'relative',
          transition: 'all 0.2s ease',
          '&:hover': {
            elevation: 2,
            transform: 'translateY(-1px)',
          },
        }}
      >
        {/* Smart Reply Badge */}
        {isSmartReply && (
          <Chip
            label="Smart Reply"
            icon={<AutoAwesome />}
            size="small"
            color="primary"
            sx={{
              position: 'absolute',
              top: 8,
              right: 8,
              zIndex: 1,
            }}
          />
        )}

        <CardContent onClick={() => setSelectedReply(isSelected ? null : index)}>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="h6" sx={{ flex: 1 }}>
              {getToneIcon(reply.tone)} {reply.type}
            </Typography>
            
            <Chip
              label={reply.tone}
              size="small"
              color={getToneColor(reply.tone) as any}
              variant="outlined"
            />
            
            <Chip
              label={`${Math.round(reply.confidence * 100)}% confidence`}
              size="small"
              color={reply.confidence > 0.8 ? 'success' : reply.confidence > 0.6 ? 'warning' : 'error'}
            />
          </Box>

          {/* Subject */}
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            Subject: {reply.subject}
          </Typography>

          {/* Body Preview */}
          <Box
            sx={{
              p: 2,
              backgroundColor: 'background.default',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'divider',
              cursor: 'pointer',
            }}
          >
            {isCustomizing ? (
              <TextField
                multiline
                rows={6}
                value={customReply}
                onChange={(e) => setCustomReply(e.target.value)}
                fullWidth
                variant="outlined"
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <Typography
                variant="body2"
                sx={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  lineHeight: 1.6,
                  display: '-webkit-box',
                  WebkitLineClamp: isSelected ? 'none' : 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: isSelected ? 'visible' : 'hidden',
                }}
              >
                {reply.body}
              </Typography>
            )}
          </Box>

          {/* Expand/Collapse indicator */}
          {!isSelected && reply.body.length > 200 && (
            <Box sx={{ textAlign: 'center', mt: 1 }}>
              <IconButton size="small">
                <ExpandMore />
              </IconButton>
            </Box>
          )}
        </CardContent>

        {/* Actions */}
        <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {isCustomizing ? (
              <>
                <Button
                  size="small"
                  variant="contained"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSaveCustomization();
                  }}
                >
                  Save
                </Button>
                <Button
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCustomizing(null);
                  }}
                >
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button
                  startIcon={isCopied ? <ThumbUp /> : <ContentCopy />}
                  size="small"
                  variant="outlined"
                  color={isCopied ? 'success' : 'primary'}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopyReply(reply, index);
                  }}
                >
                  {isCopied ? 'Copied!' : 'Copy'}
                </Button>
                
                <Button
                  startIcon={<Edit />}
                  size="small"
                  variant="outlined"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCustomize(index, reply);
                  }}
                >
                  Customize
                </Button>
                
                <Button
                  startIcon={<Send />}
                  size="small"
                  variant="contained"
                  onClick={(e) => {
                    e.stopPropagation();
                    // Handle send
                  }}
                >
                  Send
                </Button>
              </>
            )}
          </Box>

          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Tooltip title="This reply is helpful">
              <IconButton size="small">
                <ThumbUp fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="This reply needs improvement">
              <IconButton size="small">
                <ThumbDown fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </CardActions>
      </Card>
    );
  };

  if (loading) {
    return (
      <Box sx={{ p: 2 }}>
        {/* Fast replies loading skeleton */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Speed color="primary" />
            <Typography variant="h6">Fast Replies</Typography>
            <CircularProgress size={16} />
          </Box>
          
          {[1, 2, 3].map((i) => (
            <Card key={i} sx={{ mb: 2 }}>
              <CardContent>
                <Skeleton variant="text" width="40%" />
                <Skeleton variant="text" width="60%" sx={{ mb: 1 }} />
                <Skeleton variant="rectangular" height={80} />
              </CardContent>
            </Card>
          ))}
        </Box>

        {/* Smart reply loading */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <AutoAwesome color="primary" />
            <Typography variant="h6">Smart Reply</Typography>
            <CircularProgress size={16} />
          </Box>
          <Alert severity="info">
            Generating personalized smart reply... This may take a moment.
          </Alert>
        </Box>
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
          onClick={() => generateReplies(emailId)}
          fullWidth
        >
          Retry Generation
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
      {/* Generation Stats */}
      <Card sx={{ mb: 3, backgroundColor: 'primary.main', color: 'primary.contrastText' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Reply />
            <Typography variant="h6">Reply Generation Complete</Typography>
          </Box>
          <Typography variant="body2">
            Generated {fastReplies.length} fast replies in {generationTime}ms
            {smartReply && ' + 1 smart reply'}
          </Typography>
        </CardContent>
      </Card>

      {/* Fast Replies */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Speed color="primary" />
          <Typography variant="h6">Fast Replies</Typography>
          <Chip label={`${fastReplies.length} options`} size="small" color="primary" />
        </Box>
        
        {fastReplies.map((reply, index) => renderReplyCard(reply, index))}
      </Box>

      {/* Smart Reply */}
      {smartReply ? (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <AutoAwesome color="primary" />
            <Typography variant="h6">Smart Reply</Typography>
            <Chip label="AI Personalized" size="small" color="secondary" />
          </Box>
          
          {renderReplyCard(smartReply, 1000, true)}
        </Box>
      ) : (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <AutoAwesome color="primary" />
            <Typography variant="h6">Smart Reply</Typography>
          </Box>
          
          <Alert severity="info">
            Smart reply is being generated in the background...
            <Button
              size="small"
              onClick={() => generateReplies(emailId)}
              sx={{ ml: 1 }}
            >
              Check Status
            </Button>
          </Alert>
        </Box>
      )}

      {/* Tips */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            💡 Reply Tips
          </Typography>
          <Typography variant="caption" color="text.secondary" component="div">
            • Fast replies are generated instantly using templates
          </Typography>
          <Typography variant="caption" color="text.secondary" component="div">
            • Smart replies are personalized using AI analysis
          </Typography>
          <Typography variant="caption" color="text.secondary" component="div">
            • Customize any reply before sending
          </Typography>
          <Typography variant="caption" color="text.secondary" component="div">
            • Use feedback buttons to improve future suggestions
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RepliesTab;