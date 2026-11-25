import { useEffect } from 'react'
import { CaseViewer } from './components/CaseViewer'
import { FallbackBanner } from './components/bits'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { InferencePage } from './pages/InferencePage'
import { IntroPage } from './pages/IntroPage'
import {SpatialInspectionPage} from './pages/SpatialInspectionPage'
import { navigate, useRoute, type RoutePath } from './router'
import { useStore } from './store'

const MENUS: Array<{ path: RoutePath; label: string }> = [
  { path: 'dashboard', label: '대시보드' },
  { path: 'spatial', label: '공간 검사' },
  { path: 'chat', label: '에이전트 챗봇' },
  { path: 'inference', label: '5시점 추론' },
]

function NavBar({ current }: { current: RoutePath }) {
  const readOnly=useStore(state=>state.readOnly)
  return (
    <header className="glass precision-nav sticky top-3 z-40 mb-4 flex flex-wrap items-center gap-3 border-line bg-panel/95 px-5 py-3 backdrop-blur-md">
      <button
        type="button"
        className="mr-2 text-left"
        onClick={() => navigate('#/')}
        title="인트로로 이동"
      >
        <span className="block font-mono text-[12px] font-semibold uppercase tracking-wide2 text-tx">
          INSPECT <span className="text-signal">AI</span>
        </span>
        <span className="block font-mono text-[8px] uppercase tracking-label text-faint">
          PRECISION INSPECTION STUDIO
        </span>
      </button>
      <nav className="ml-auto flex flex-wrap gap-2" aria-label="주 메뉴">
        {MENUS.map((m) => (
          <button
            key={m.path}
            disabled={readOnly&&m.path==='inference'}
            type="button"
            className={`btn px-3 py-1 text-[10px] uppercase tracking-label ${current === m.path ? 'btn-active' : ''}`}
            onClick={() => navigate(`#/${m.path}`)}
          >
            {m.label}
          </button>
        ))}
      </nav>
    </header>
  )
}

export default function App() {
  const route = useRoute()
  const setFocusCase = useStore((s) => s.setFocusCase)

  useEffect(() => {
    if (route.path !== 'dashboard') return
    const focus = route.params.get('focus')
    if (focus) {
      setFocusCase({ productId: focus, cameraId: route.params.get('camera') ?? undefined })
    }
    const item = route.params.get('item')
    if (item && useStore.getState().items.includes(item)) {
      useStore.getState().setItem(item)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route])

  return (
    <div className="precision-shell min-h-screen bg-bg" data-inspection-theme="precision">
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col p-3">
        {route.path !== 'intro' && <NavBar current={route.path} />}
        {route.path !== 'intro' && <FallbackBanner />}
        {route.path === 'intro' && <IntroPage />}
        {route.path === 'dashboard' && <DashboardPage />}
        {route.path === 'spatial' && <SpatialInspectionPage />}
        {route.path === 'chat' && <ChatPage />}
        {route.path === 'inference' && <InferencePage />}
      </div>
      <CaseViewer />
    </div>
  )
}
