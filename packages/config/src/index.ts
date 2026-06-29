export const eslintConfig = {
  extends: ['next/core-web-vitals', 'next/typescript'],
}

export const tailwindBase = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}', './app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
}
