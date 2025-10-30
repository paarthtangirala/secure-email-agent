import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Tabs,
  Tab,
  Typography,
  Divider,
} from '@mui/material';
import {
  Summarize,
  Assignment,
  Reply,
  Event,
} from '@mui/icons-material';
import SummaryTab from './SummaryTab';
import TasksTab from './TasksTab';
import RepliesTab from './RepliesTab';
import CalendarTab from './CalendarTab';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    style={{ height: value === index ? 'calc(100% - 64px)' : 0 }}
  >
    {value === index && (
      <Box sx={{ height: '100%', overflow: 'auto' }}>
        {children}
      </Box>
    )}
  </div>
);

interface AIAssistantPanelProps {
  emailId: string;
  threadId: string | null;
}

const AIAssistantPanel: React.FC<AIAssistantPanelProps> = ({
  emailId,
  threadId,
}) => {
  const [selectedTab, setSelectedTab] = useState(0);

  // Auto-switch to relevant tabs based on content
  useEffect(() => {
    // Reset to summary tab when email changes
    setSelectedTab(0);
  }, [emailId]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const tabs = [
    {
      label: 'Summary',
      icon: <Summarize />,
      component: (
        <SummaryTab 
          emailId={emailId} 
          threadId={threadId}
          onTasksFound={() => {
            // Auto-switch to tasks tab if tasks are found
            // Could implement notification here
          }}
          onMeetingFound={() => {
            // Auto-switch to calendar tab if meeting is found
            // Could implement notification here
          }}
        />
      ),
    },
    {
      label: 'Tasks',
      icon: <Assignment />,
      component: <TasksTab emailId={emailId} />,
    },
    {
      label: 'Replies',
      icon: <Reply />,
      component: <RepliesTab emailId={emailId} />,
    },
    {
      label: 'Calendar',
      icon: <Event />,
      component: <CalendarTab emailId={emailId} />,
    },
  ];

  return (
    <Paper
      elevation={0}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'background.paper',
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Typography variant="h6" fontWeight="bold">
          AI Assistant
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Intelligent insights and suggestions
        </Typography>
      </Box>

      {/* Tabs */}
      <Tabs
        value={selectedTab}
        onChange={handleTabChange}
        variant="fullWidth"
        sx={{
          borderBottom: '1px solid',
          borderColor: 'divider',
          '& .MuiTab-root': {
            minHeight: 64,
            textTransform: 'none',
            fontSize: '0.875rem',
            fontWeight: 500,
          },
        }}
      >
        {tabs.map((tab, index) => (
          <Tab
            key={index}
            label={tab.label}
            icon={tab.icon}
            iconPosition="top"
            sx={{
              '& .MuiSvgIcon-root': {
                fontSize: '1.25rem',
                mb: 0.5,
              },
            }}
          />
        ))}
      </Tabs>

      {/* Tab Content */}
      {tabs.map((tab, index) => (
        <TabPanel key={index} value={selectedTab} index={index}>
          {tab.component}
        </TabPanel>
      ))}
    </Paper>
  );
};

export default AIAssistantPanel;