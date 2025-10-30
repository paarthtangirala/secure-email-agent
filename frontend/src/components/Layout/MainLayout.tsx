import React, { useState, useContext } from 'react';
import {
  AppBar,
  Box,
  CssBaseline,
  Drawer,
  Grid,
  IconButton,
  Toolbar,
  Typography,
  TextField,
  InputAdornment,
  Switch,
  FormControlLabel,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Search as SearchIcon,
  DarkMode,
  LightMode,
  Refresh,
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import { createMailMaestroTheme } from '../../theme/theme';
import SmartInbox from '../Inbox/SmartInbox';
import ThreadView from '../Thread/ThreadView';
import AIAssistantPanel from '../AIAssistant/AIAssistantPanel';
import { useSearch, useEmailSync } from '../../hooks/useApi';

// Theme context
export const ThemeContext = React.createContext({
  darkMode: false,
  toggleDarkMode: () => {},
});

const DRAWER_WIDTH = 280;

interface MainLayoutProps {
  children?: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  // State
  const [darkMode, setDarkMode] = useState(
    localStorage.getItem('darkMode') === 'true'
  );
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Theme
  const theme = createMailMaestroTheme(darkMode ? 'dark' : 'light');
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Hooks
  const { search, results: searchResults, clearSearch } = useSearch();
  const { startSync, loading: syncLoading } = useEmailSync();

  // Handlers
  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', newMode.toString());
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query.trim()) {
      search(query);
    } else {
      clearSearch();
    }
  };

  const handleEmailSelect = (emailId: string, threadId: string) => {
    setSelectedEmailId(emailId);
    setSelectedThreadId(threadId);
  };

  const handleRefresh = () => {
    startSync(24, true);
  };

  // Drawer content
  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* App Title */}
      <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Typography variant="h6" component="div" fontWeight="bold">
          MailMaestro
        </Typography>
        <Typography variant="caption" color="text.secondary">
          AI Email Assistant
        </Typography>
      </Box>

      {/* Smart Inbox */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <SmartInbox
          onEmailSelect={handleEmailSelect}
          selectedEmailId={selectedEmailId}
          searchResults={searchResults}
          searchQuery={searchQuery}
        />
      </Box>
    </Box>
  );

  return (
    <ThemeProvider theme={theme}>
      <ThemeContext.Provider value={{ darkMode, toggleDarkMode }}>
        <CssBaseline />
        <Box sx={{ display: 'flex', height: '100vh' }}>
          {/* App Bar */}
          <AppBar
            position="fixed"
            sx={{
              width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
              ml: { md: `${DRAWER_WIDTH}px` },
              zIndex: theme.zIndex.drawer + 1,
            }}
          >
            <Toolbar>
              {/* Mobile menu button */}
              <IconButton
                color="inherit"
                aria-label="open drawer"
                edge="start"
                onClick={handleDrawerToggle}
                sx={{ mr: 2, display: { md: 'none' } }}
              >
                <MenuIcon />
              </IconButton>

              {/* Search */}
              <TextField
                size="small"
                placeholder="Search emails..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                sx={{
                  flex: 1,
                  maxWidth: 400,
                  mr: 2,
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: 'background.paper',
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  },
                }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />

              {/* Actions */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {/* Refresh */}
                <IconButton
                  color="inherit"
                  onClick={handleRefresh}
                  disabled={syncLoading}
                  title="Sync emails"
                >
                  <Refresh />
                </IconButton>

                {/* Theme toggle */}
                <FormControlLabel
                  control={
                    <Switch
                      checked={darkMode}
                      onChange={toggleDarkMode}
                      icon={<LightMode />}
                      checkedIcon={<DarkMode />}
                    />
                  }
                  label=""
                  sx={{ ml: 1 }}
                />
              </Box>
            </Toolbar>
          </AppBar>

          {/* Drawer */}
          <Box
            component="nav"
            sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}
          >
            {/* Mobile drawer */}
            <Drawer
              variant="temporary"
              open={mobileOpen}
              onClose={handleDrawerToggle}
              ModalProps={{ keepMounted: true }}
              sx={{
                display: { xs: 'block', md: 'none' },
                '& .MuiDrawer-paper': {
                  boxSizing: 'border-box',
                  width: DRAWER_WIDTH,
                },
              }}
            >
              {drawerContent}
            </Drawer>

            {/* Desktop drawer */}
            <Drawer
              variant="permanent"
              sx={{
                display: { xs: 'none', md: 'block' },
                '& .MuiDrawer-paper': {
                  boxSizing: 'border-box',
                  width: DRAWER_WIDTH,
                },
              }}
              open
            >
              {drawerContent}
            </Drawer>
          </Box>

          {/* Main content */}
          <Box
            component="main"
            sx={{
              flexGrow: 1,
              width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
              height: '100vh',
              overflow: 'hidden',
            }}
          >
            <Toolbar /> {/* Spacer for AppBar */}
            
            <Grid container sx={{ height: 'calc(100vh - 64px)' }}>
              {/* Thread View */}
              <Grid 
                item 
                xs={12} 
                md={selectedEmailId ? 6 : 12} 
                lg={selectedEmailId ? 6 : 12}
                sx={{ height: '100%', overflow: 'hidden' }}
              >
                {selectedThreadId ? (
                  <ThreadView
                    threadId={selectedThreadId}
                    selectedEmailId={selectedEmailId}
                    onEmailSelect={setSelectedEmailId}
                  />
                ) : (
                  <Box
                    sx={{
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      textAlign: 'center',
                      p: 4,
                    }}
                  >
                    <Box>
                      <Typography variant="h5" color="text.secondary" gutterBottom>
                        Welcome to MailMaestro
                      </Typography>
                      <Typography variant="body1" color="text.secondary">
                        Select an email from the sidebar to get started with AI-powered assistance.
                      </Typography>
                    </Box>
                  </Box>
                )}
              </Grid>

              {/* AI Assistant Panel */}
              {selectedEmailId && (
                <Grid 
                  item 
                  xs={12} 
                  md={6} 
                  lg={6}
                  sx={{ 
                    height: '100%', 
                    borderLeft: '1px solid', 
                    borderColor: 'divider',
                    display: { xs: 'none', md: 'block' }
                  }}
                >
                  <AIAssistantPanel 
                    emailId={selectedEmailId}
                    threadId={selectedThreadId}
                  />
                </Grid>
              )}
            </Grid>
          </Box>
        </Box>
      </ThemeContext.Provider>
    </ThemeProvider>
  );
};

export default MainLayout;