import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { getUserInfo, syncGrowthContext } from '@/api/loginapi'
import { UserInfo } from '@/models/LoginModels'
import { getAnalyticsGrowthContext, identifyAnalyticsUser, resetAnalyticsUser } from '@/utils/analytics'

type UserContextType = {
  userInfo: UserInfo | null
  loading: boolean
  refresh: (attempts?: number, baseDelay?: number) => Promise<void>
  setUserInfo: React.Dispatch<React.SetStateAction<UserInfo | null>>
}

const UserContext = createContext<UserContextType | null>(null)

export function UserProvider({ children }: { children: ReactNode }) {
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(false)

  const hasToken = () => !!localStorage.getItem('session_token')

  const refresh = async (attempts = 1, baseDelay = 500) => {
    setLoading(true)
    for (let i = 0; i < attempts; i++) {
      try {
        const info = await getUserInfo()
        setUserInfo(info)
        break
      } catch {
        if (i < attempts - 1) {
          await new Promise(r => setTimeout(r, baseDelay * (i + 1)))
          continue
        }
      }
    }
    setLoading(false)
  }

  useEffect(() => {
    if (hasToken()) {
      refresh(1, 500)
    } else {
      setUserInfo(null)
    }
    const onLogin = () => refresh(2, 500)
    const onLogout = () => setUserInfo(null)
    const onRefresh = (evt: Event) => {
      const detailPhone = (evt as CustomEvent)?.detail?.phone as string | undefined
      if (detailPhone) {
        setUserInfo(prev => prev ? { ...prev, phone: detailPhone } as UserInfo : prev)
      }
      refresh(4, 700)
    }
    window.addEventListener('user-login', onLogin)
    window.addEventListener('user-logout', onLogout)
    window.addEventListener('refresh-user-info', onRefresh as EventListener)
    return () => {
      window.removeEventListener('user-login', onLogin)
      window.removeEventListener('user-logout', onLogout)
      window.removeEventListener('refresh-user-info', onRefresh as EventListener)
    }
  }, [])

  useEffect(() => {
    if (userInfo) {
      identifyAnalyticsUser(userInfo)
      const growthContext = getAnalyticsGrowthContext()
      const syncKey = `api35:growth-context-synced:${userInfo.user_no}`
      if (growthContext && !sessionStorage.getItem(syncKey)) {
        void syncGrowthContext(growthContext)
          .then(() => {
            sessionStorage.setItem(syncKey, '1')
          })
          .catch(() => undefined)
      }
      return
    }
    resetAnalyticsUser()
  }, [userInfo])

  return (
    <UserContext.Provider value={{ userInfo, loading, refresh, setUserInfo }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const ctx = useContext(UserContext)
  if (!ctx) {
    throw new Error('useUser 必须在 UserProvider 内部使用')
  }
  return ctx
}
