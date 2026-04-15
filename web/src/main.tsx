import React from 'react'
import ReactDOM from 'react-dom/client'
import AppRouter from './router/router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import './main.scss'
import { initializeAnalytics } from './utils/analytics'
import { APP_ROUTER_BASENAME } from './utils/appBase'

initializeAnalytics()

NProgress.configure({ showSpinner: true, trickleSpeed: 100 })

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppRouter basename={APP_ROUTER_BASENAME} />
  </React.StrictMode>,
)
