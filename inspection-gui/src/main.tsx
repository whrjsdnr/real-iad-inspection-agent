import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { useStore } from './store'
import './index.css'
import {parseHash} from './router'

if(parseHash(window.location.hash).path==='spatial')useStore.setState({readOnly:true})
else useStore.getState().init()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
