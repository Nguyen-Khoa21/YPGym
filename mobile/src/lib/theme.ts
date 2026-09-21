export const colors = {
  background: '#FFFFFF',
  surface: '#F3F7F4',
  surfaceStrong: '#E4EFE7',
  card: '#FFFFFF',
  border: '#D5E2D9',
  primary: '#0E4D2B',
  primaryPressed: '#0A3B21',
  primarySurface: '#E8F4EC',
  positive: '#4EA96B',
  positiveSurface: '#EAF6ED',
  positiveBorder: '#BFD8C7',
  text: '#142019',
  muted: '#526159',
  dim: '#6F7D75',
  danger: '#B42318',
  dangerSurface: '#FEF3F2',
  dangerSurfaceStrong: '#FEE4E2',
  dangerBorder: '#F2B8B5',
  warning: '#8A4B08',
  warningSurface: '#FFF7E8',
  white: '#FFFFFF',
  qrInk: '#101512',
} as const;

export const radii = { sm: 10, md: 16, lg: 22, pill: 999 } as const;
export const spacing = { xs: 6, sm: 10, md: 16, lg: 22, xl: 30 } as const;
export const shadows = {
  card: {
    shadowColor: '#0B2F1D',
    shadowOffset: { width: 0, height: 7 },
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 3,
  },
} as const;
