import { createTheme, ThemeOptions } from '@mui/material/styles';

// MailMaestro theme with professional dark/light modes
const getDesignTokens = (mode: 'light' | 'dark'): ThemeOptions => ({
  palette: {
    mode,
    ...(mode === 'light'
      ? {
          // Light mode palette
          primary: {
            main: '#6750A4',
            light: '#8B7BC7',
            dark: '#4F378B',
            contrastText: '#FFFFFF',
          },
          secondary: {
            main: '#00B0FF',
            light: '#33C1FF',
            dark: '#007AC1',
            contrastText: '#FFFFFF',
          },
          background: {
            default: '#FAFBFF',
            paper: '#FFFFFF',
          },
          text: {
            primary: '#1C1B1F',
            secondary: '#49454F',
          },
          divider: '#E7E0EC',
          action: {
            hover: 'rgba(103, 80, 164, 0.04)',
          },
        }
      : {
          // Dark mode palette
          primary: {
            main: '#D0BCFF',
            light: '#EADDFF',
            dark: '#9A82DB',
            contrastText: '#381E72',
          },
          secondary: {
            main: '#40CAFF',
            light: '#73DBFF',
            dark: '#007AC1',
            contrastText: '#003549',
          },
          background: {
            default: '#141218',
            paper: '#1D1B20',
          },
          text: {
            primary: '#E6E0E9',
            secondary: '#CAC4D0',
          },
          divider: '#49454F',
          action: {
            hover: 'rgba(208, 188, 255, 0.08)',
          },
        }),
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      lineHeight: 1.25,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 500,
      lineHeight: 1.35,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
      lineHeight: 1.4,
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 500,
      lineHeight: 1.45,
    },
    body1: {
      fontSize: '1rem',
      fontWeight: 400,
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.875rem',
      fontWeight: 400,
      lineHeight: 1.43,
    },
    caption: {
      fontSize: '0.75rem',
      fontWeight: 400,
      lineHeight: 1.33,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: mode === 'dark' 
            ? '0px 4px 8px rgba(0, 0, 0, 0.12), 0px 2px 4px rgba(0, 0, 0, 0.08)'
            : '0px 2px 8px rgba(0, 0, 0, 0.04), 0px 1px 4px rgba(0, 0, 0, 0.06)',
          border: mode === 'dark' ? '1px solid #49454F' : '1px solid #E7E0EC',
          backgroundImage: 'none',
          backdropFilter: 'blur(20px)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderRadius: 20,
          padding: '8px 24px',
        },
        contained: {
          boxShadow: '0px 1px 2px rgba(0, 0, 0, 0.3), 0px 1px 3px 1px rgba(0, 0, 0, 0.15)',
          '&:hover': {
            boxShadow: '0px 1px 2px rgba(0, 0, 0, 0.3), 0px 2px 6px 2px rgba(0, 0, 0, 0.15)',
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: mode === 'dark' ? '#1D1B20' : '#FFFFFF',
          color: mode === 'dark' ? '#E6E0E9' : '#1C1B1F',
          boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: mode === 'dark' ? '#1D1B20' : '#FFFFFF',
          borderRight: `1px solid ${mode === 'dark' ? '#49454F' : '#E7E0EC'}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          fontWeight: 500,
        },
        filled: {
          backgroundColor: mode === 'dark' ? '#381E72' : '#E8DEF8',
          color: mode === 'dark' ? '#D0BCFF' : '#6750A4',
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        root: {
          '& .MuiTabs-indicator': {
            height: 3,
            borderRadius: '3px 3px 0 0',
          },
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          fontSize: '0.875rem',
          minHeight: 48,
        },
      },
    },
  },
});

export const createMailMaestroTheme = (mode: 'light' | 'dark') => 
  createTheme(getDesignTokens(mode));

export default createMailMaestroTheme;