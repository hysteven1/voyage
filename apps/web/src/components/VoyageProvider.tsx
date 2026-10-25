"use client";

import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#174e43",
      light: "#e8f1ec",
      dark: "#103b33",
      contrastText: "#fffdf8",
    },
    secondary: { main: "#d3764f" },
    background: { default: "#f7f6f1", paper: "#ffffff" },
    text: { primary: "#203b36", secondary: "#6a7772" },
    divider: "#e5e9e2",
    error: { main: "#b4403d" },
  },
  typography: {
    fontFamily:
      '"Segoe UI", -apple-system, BlinkMacSystemFont, Arial, sans-serif',
    h1: { fontWeight: 600, letterSpacing: "-0.055em" },
    h2: { fontWeight: 600, letterSpacing: "-0.04em" },
    h3: { fontWeight: 600, letterSpacing: "-0.025em" },
    button: { textTransform: "none", fontWeight: 600, letterSpacing: "0.01em" },
    body2: { fontSize: "0.9375rem", lineHeight: 1.5 },
    caption: { fontSize: "0.8125rem", lineHeight: 1.5 },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 12, padding: "11px 20px" } },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: "#fff",
          borderRadius: 12,
          minHeight: 56,
          "&.Mui-focused": { boxShadow: "none" },
          "& fieldset": { borderColor: "#dce3db" },
        },
      },
    },
    MuiTextField: { defaultProps: { fullWidth: true, variant: "outlined" } },
    MuiFormHelperText: { styleOverrides: { root: { fontSize: "0.8125rem" } } },
    MuiPaper: { defaultProps: { elevation: 0 } },
    MuiChip: { styleOverrides: { root: { fontWeight: 500 } } },
    MuiAlert: { styleOverrides: { root: { borderRadius: 12 } } },
  },
});

export default function VoyageProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        {children}
      </LocalizationProvider>
    </ThemeProvider>
  );
}
