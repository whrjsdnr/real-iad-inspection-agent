/** @type {import('tailwindcss').Config} */
const rgb = (name) => `rgb(var(${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        /* 시맨틱 토큰 (styles/tokens.css RGB 트리플릿 참조) */
        bg: rgb('--c-bg'),
        panel: rgb('--c-panel'),
        'panel-raised': rgb('--c-panel-raised'),
        line: rgb('--c-line'),
        signal: rgb('--c-signal'),
        ok: rgb('--c-ok'),
        warn: rgb('--c-warn'),
        fail: rgb('--c-fail'),
        tx: {
          DEFAULT: rgb('--c-text'),
          muted: rgb('--c-muted'),
          faint: rgb('--c-faint'),
        },
        muted: rgb('--c-muted'),
        faint: rgb('--c-faint'),
        white: rgb('--c-white'),
        /* 하위 호환 별칭 — 값은 전부 토큰에서 파생 */
        ink: {
          950: rgb('--c-bg'),
          900: rgb('--c-panel'),
          800: rgb('--c-panel-raised'),
        },
        accent: {
          cyan: rgb('--c-signal'),
          amber: rgb('--c-warn'),
        },
        slate: {
          100: rgb('--c-text'),
          200: rgb('--c-muted'),
          300: rgb('--c-muted'),
          400: rgb('--c-muted'),
          500: rgb('--c-faint'),
          600: rgb('--c-faint'),
        },
      },
      fontFamily: {
        sans: ['Inter', 'Pretendard', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      letterSpacing: {
        label: '0.14em',
        wide2: '0.22em',
      },
    },
  },
  plugins: [],
}
