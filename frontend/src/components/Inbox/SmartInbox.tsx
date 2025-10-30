import React, { useState, useEffect } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Typography,
  Chip,
  Divider,
  Badge,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  Inbox,
  Label,
  Event,
  Assignment,
  PriorityHigh,
  ExpandMore,
  ExpandLess,
  Person,
} from '@mui/icons-material';
import { format, parseISO, isToday, isYesterday } from 'date-fns';
import { useEmails, Email } from '../../hooks/useApi';

interface SmartInboxProps {
  onEmailSelect: (emailId: string, threadId: string) => void;
  selectedEmailId: string | null;
  searchResults: Email[];
  searchQuery: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box>{children}</Box>}
  </div>
);

const SmartInbox: React.FC<SmartInboxProps> = ({
  onEmailSelect,
  selectedEmailId,
  searchResults,
  searchQuery,
}) => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    important: true,
    meeting: true,
    billing: false,
    followUp: false,
  });

  // Fetch emails with different filters based on tab
  const filters = [
    {}, // All emails
    { label: 'important' }, // Important
    { label: 'meeting' }, // Meetings
    { label: 'billing' }, // Billing
    { label: 'follow_up' }, // Follow-ups
  ];

  const { emails, loading, error, refetch } = useEmails(1, 50, filters[selectedTab]);

  // Use search results if searching, otherwise use filtered emails
  const displayEmails = searchQuery ? searchResults : emails;

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const formatDate = (dateString: string) => {
    try {
      const date = parseISO(dateString);
      if (isToday(date)) return 'Today';
      if (isYesterday(date)) return 'Yesterday';
      return format(date, 'MMM d');
    } catch {
      return '';
    }
  };

  const formatTime = (dateString: string) => {
    try {
      return format(parseISO(dateString), 'h:mm a');
    } catch {
      return '';
    }
  };

  const getPriorityColor = (urgency: string) => {
    switch (urgency) {
      case 'urgent': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getLabelIcon = (label: string) => {
    switch (label) {
      case 'meeting': return <Event fontSize="small" />;
      case 'billing': return <Assignment fontSize="small" />;
      case 'urgent': return <PriorityHigh fontSize="small" />;
      default: return <Label fontSize="small" />;
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

  const groupEmailsByLabel = (emails: Email[]) => {
    const groups: Record<string, Email[]> = {};
    
    emails.forEach(email => {
      const primaryLabel = email.primary_label || 'general';
      if (!groups[primaryLabel]) {
        groups[primaryLabel] = [];
      }
      groups[primaryLabel].push(email);
    });

    return groups;
  };

  const renderEmailItem = (email: Email) => (
    <ListItem key={email.id} disablePadding>
      <ListItemButton
        selected={selectedEmailId === email.id}
        onClick={() => onEmailSelect(email.id, email.thread_id)}
        sx={{
          borderLeft: selectedEmailId === email.id ? 3 : 0,
          borderColor: 'primary.main',
          backgroundColor: email.is_unread ? 'action.hover' : 'transparent',
          '&:hover': {
            backgroundColor: 'action.hover',
          },
        }}
      >
        <ListItemAvatar>
          <Badge
            color="primary"
            variant="dot"
            invisible={!email.is_unread}
          >
            <Avatar
              sx={{
                width: 40,
                height: 40,
                fontSize: '0.875rem',
                backgroundColor: 'primary.main',
              }}
            >
              <Person />
            </Avatar>
          </Badge>
        </ListItemAvatar>

        <ListItemText
          primaryTypographyProps={{ component: 'div' }}
          secondaryTypographyProps={{ component: 'div' }}
          primary={
            <Box component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <Typography
                component="div"
                variant="body2"
                fontWeight={email.is_unread ? 600 : 400}
                noWrap
                sx={{ flex: 1, minWidth: 0 }}
              >
                {email.sender.split('<')[0].trim() || email.sender_email}
              </Typography>
              <Typography component="div" variant="caption" color="text.secondary">
                {formatTime(email.date_received)}
              </Typography>
            </Box>
          }
          secondary={
            <Box component="div">
              <Typography
                component="div"
                variant="body2"
                fontWeight={email.is_unread ? 500 : 400}
                sx={{
                  mb: 0.5,
                  display: '-webkit-box',
                  WebkitLineClamp: 1,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}
              >
                {email.subject || '(No subject)'}
              </Typography>
              
              <Typography
                component="div"
                variant="caption"
                color="text.secondary"
                sx={{
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  mb: 1,
                }}
              >
                {email.body_text?.slice(0, 120)}...
              </Typography>

              {/* Labels */}
              <Box component="div" sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {email.labels?.slice(0, 2).map((label, index) => (
                  <Chip
                    key={index}
                    label={label}
                    size="small"
                    variant="filled"
                    color={getPriorityColor(email.urgency_level || 'medium') as any}
                    icon={getLabelIcon(label)}
                    sx={{ fontSize: '0.6rem', height: 20 }}
                  />
                ))}
                {email.requires_response && (
                  <Chip
                    label="Response needed"
                    size="small"
                    color="warning"
                    variant="outlined"
                    sx={{ fontSize: '0.6rem', height: 20 }}
                  />
                )}
              </Box>
            </Box>
          }
        />
      </ListItemButton>
    </ListItem>
  );

  const renderGroupedEmails = () => {
    const groups = groupEmailsByLabel(displayEmails);
    
    return Object.entries(groups).map(([label, groupEmails]) => (
      <Box key={label}>
        <ListItem>
          <ListItemButton
            onClick={() => toggleSection(label)}
            sx={{ py: 1 }}
          >
            <ListItemText
              primary={
                <Typography variant="subtitle2" fontWeight="bold">
                  {label.charAt(0).toUpperCase() + label.slice(1).replace('_', ' ')}
                  <Typography component="span" variant="caption" sx={{ ml: 1 }}>
                    ({groupEmails.length})
                  </Typography>
                </Typography>
              }
            />
            <IconButton size="small">
              {expandedSections[label] ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </ListItemButton>
        </ListItem>
        
        <Collapse in={expandedSections[label]}>
          {groupEmails.map(renderEmailItem)}
        </Collapse>
        
        <Divider />
      </Box>
    ));
  };

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Tabs */}
      <Paper elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
        <Tabs
          value={selectedTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ minHeight: 48 }}
        >
          <Tab label="All" icon={<Inbox />} iconPosition="start" />
          <Tab label="Important" icon={<PriorityHigh />} iconPosition="start" />
          <Tab label="Meetings" icon={<Event />} iconPosition="start" />
          <Tab label="Billing" icon={<Assignment />} iconPosition="start" />
          <Tab label="Follow-up" icon={<Label />} iconPosition="start" />
        </Tabs>
      </Paper>

      {/* Email List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : displayEmails.length === 0 ? (
          <Box sx={{ textAlign: 'center', p: 4 }}>
            <Typography variant="body2" color="text.secondary">
              {searchQuery ? 'No emails found for your search.' : 'No emails found.'}
            </Typography>
          </Box>
        ) : selectedTab === 0 ? (
          // Show grouped emails for "All" tab
          <List sx={{ py: 0 }}>
            {renderGroupedEmails()}
          </List>
        ) : (
          // Show flat list for filtered tabs
          <List sx={{ py: 0 }}>
            {displayEmails.map(renderEmailItem)}
          </List>
        )}
      </Box>
    </Box>
  );
};

export default SmartInbox;