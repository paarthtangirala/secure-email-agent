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
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  LinearProgress,
} from '@mui/material';
import {
  Event,
  Schedule,
  LocationOn,
  Person,
  VideoCall,
  Check,
  Close,
  Edit,
  Add,
  Refresh,
  CalendarToday,
  AccessTime,
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import { useCalendarResponse } from '../../hooks/useApi';

interface CalendarTabProps {
  emailId: string;
}

interface MeetingInfo {
  title: string;
  start_time?: string;
  end_time?: string;
  location: string;
  platform: string;
  attendees: string[];
  description: string;
  confidence: number;
}

const CalendarTab: React.FC<CalendarTabProps> = ({ emailId }) => {
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editedMeeting, setEditedMeeting] = useState<Partial<MeetingInfo>>({});
  const [addingToCalendar, setAddingToCalendar] = useState(false);
  
  const { response, loading, error, processCalendar } = useCalendarResponse();

  useEffect(() => {
    if (emailId) {
      processCalendar(emailId);
    }
  }, [emailId, processCalendar]);

  const handleAcceptMeeting = async () => {
    setAddingToCalendar(true);
    
    try {
      // Simulate adding to calendar
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // In real implementation, call calendar API
      console.log('Meeting accepted and added to calendar');
    } catch (err) {
      console.error('Failed to add to calendar');
    } finally {
      setAddingToCalendar(false);
    }
  };

  const handleEditMeeting = () => {
    if (response?.calendar_event) {
      setEditedMeeting(response.calendar_event);
      setEditDialogOpen(true);
    }
  };

  const handleSaveEdit = () => {
    // In real implementation, save the edited meeting
    setEditDialogOpen(false);
    setEditedMeeting({});
  };

  const formatDateTime = (dateTimeStr: string) => {
    try {
      return format(parseISO(dateTimeStr), 'PPP \'at\' p');
    } catch {
      return dateTimeStr;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'success';
    if (confidence >= 0.7) return 'warning';
    return 'error';
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'zoom':
      case 'teams':
      case 'meet':
      case 'virtual':
        return <VideoCall />;
      case 'in-person':
        return <LocationOn />;
      default:
        return <Event />;
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Analyzing email for meeting information...
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
          onClick={() => processCalendar(emailId)}
          fullWidth
        >
          Retry Analysis
        </Button>
      </Box>
    );
  }

  if (!response || response.action === 'none') {
    return (
      <Box sx={{ p: 2 }}>
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <Event sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No Meeting Detected
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              This email doesn't appear to contain meeting information.
            </Typography>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={() => processCalendar(emailId)}
            >
              Re-analyze Email
            </Button>
          </CardContent>
        </Card>

        {/* Manual Add Option */}
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Want to create a meeting anyway?
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              You can manually extract meeting details from this email.
            </Typography>
            <Button
              startIcon={<Add />}
              variant="outlined"
              fullWidth
              onClick={() => {
                // Handle manual meeting creation
              }}
            >
              Create Meeting Manually
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  const meeting = response.calendar_event;

  return (
    <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
      {/* Detection Summary */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Event sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">Meeting Detected</Typography>
            <Chip
              label={`${Math.round(response.confidence * 100)}% confidence`}
              size="small"
              color={getConfidenceColor(response.confidence)}
              sx={{ ml: 'auto' }}
            />
          </Box>

          <Alert
            severity={response.confidence >= 0.9 ? 'success' : response.confidence >= 0.7 ? 'info' : 'warning'}
            sx={{ mb: 2 }}
          >
            <Typography variant="body2">
              {response.message}
            </Typography>
          </Alert>

          {/* Confidence Meter */}
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Detection Confidence
            </Typography>
            <LinearProgress
              variant="determinate"
              value={response.confidence * 100}
              color={getConfidenceColor(response.confidence)}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
        </CardContent>
      </Card>

      {/* Meeting Details */}
      {meeting && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Meeting Details
            </Typography>

            <List dense>
              {/* Title */}
              <ListItem>
                <ListItemIcon>
                  <Event fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="Title"
                  secondary={meeting.title || 'Untitled Meeting'}
                />
              </ListItem>

              {/* Date & Time */}
              {meeting.start_time && (
                <ListItem>
                  <ListItemIcon>
                    <Schedule fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary="Date & Time"
                    secondary={
                      <Box>
                        <Typography variant="body2">
                          {formatDateTime(meeting.start_time)}
                        </Typography>
                        {meeting.end_time && (
                          <Typography variant="caption" color="text.secondary">
                            Until {format(parseISO(meeting.end_time), 'p')}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              )}

              {/* Location/Platform */}
              <ListItem>
                <ListItemIcon>
                  {getPlatformIcon(meeting.platform)}
                </ListItemIcon>
                <ListItemText
                  primary="Location"
                  secondary={
                    <Box>
                      <Typography variant="body2">
                        {meeting.location || 'Location TBD'}
                      </Typography>
                      <Chip
                        label={meeting.platform}
                        size="small"
                        variant="outlined"
                        sx={{ mt: 0.5 }}
                      />
                    </Box>
                  }
                />
              </ListItem>

              {/* Attendees */}
              {meeting.attendees && meeting.attendees.length > 0 && (
                <ListItem>
                  <ListItemIcon>
                    <Person fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primaryTypographyProps={{ component: 'div' }}
                    secondaryTypographyProps={{ component: 'div' }}
                    primary="Attendees"
                    secondary={
                      <Box component="div">
                        {meeting.attendees.slice(0, 3).map((attendee: string, index: number) => (
                          <Typography key={index} component="div" variant="body2">
                            {attendee}
                          </Typography>
                        ))}
                        {meeting.attendees.length > 3 && (
                          <Typography component="div" variant="caption" color="text.secondary">
                            +{meeting.attendees.length - 3} more
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              )}

              {/* Description */}
              {meeting.description && (
                <ListItem>
                  <ListItemText
                    primary="Description"
                    secondary={
                      <Typography
                        variant="body2"
                        sx={{
                          mt: 1,
                          p: 1,
                          backgroundColor: 'background.default',
                          borderRadius: 1,
                          border: '1px solid',
                          borderColor: 'divider',
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {meeting.description}
                      </Typography>
                    }
                  />
                </ListItem>
              )}
            </List>
          </CardContent>

          <CardActions sx={{ justifyContent: 'space-between' }}>
            <Button
              startIcon={<Edit />}
              variant="outlined"
              onClick={handleEditMeeting}
            >
              Edit Details
            </Button>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                startIcon={<Close />}
                variant="outlined"
                color="error"
                onClick={() => {
                  // Handle decline
                }}
              >
                Decline
              </Button>
              
              <Button
                startIcon={addingToCalendar ? <CircularProgress size={16} /> : <Check />}
                variant="contained"
                color="success"
                disabled={addingToCalendar}
                onClick={handleAcceptMeeting}
              >
                {addingToCalendar ? 'Adding...' : 'Accept & Add to Calendar'}
              </Button>
            </Box>
          </CardActions>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Quick Actions
          </Typography>

          <List dense>
            <ListItem
              button
              onClick={() => {
                // Handle view calendar
              }}
            >
              <ListItemIcon>
                <CalendarToday fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="View My Calendar" />
            </ListItem>

            <ListItem
              button
              onClick={() => {
                // Handle create custom meeting
              }}
            >
              <ListItemIcon>
                <Add fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Create Custom Meeting" />
            </ListItem>

            <ListItem
              button
              onClick={() => {
                // Handle scheduling assistant
              }}
            >
              <ListItemIcon>
                <AccessTime fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Find Available Times" />
            </ListItem>
          </List>
        </CardContent>
      </Card>

      {/* Edit Meeting Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Meeting Details</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              label="Meeting Title"
              value={editedMeeting.title || ''}
              onChange={(e) => setEditedMeeting({ ...editedMeeting, title: e.target.value })}
              fullWidth
            />
            
            <TextField
              label="Location"
              value={editedMeeting.location || ''}
              onChange={(e) => setEditedMeeting({ ...editedMeeting, location: e.target.value })}
              fullWidth
            />
            
            <TextField
              label="Description"
              value={editedMeeting.description || ''}
              onChange={(e) => setEditedMeeting({ ...editedMeeting, description: e.target.value })}
              multiline
              rows={3}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveEdit} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CalendarTab;