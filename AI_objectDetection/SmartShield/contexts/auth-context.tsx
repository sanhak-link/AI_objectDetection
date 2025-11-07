"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { getCurrentUser, logout as apiLogout, tokenStorage } from "@/lib/api"

interface User {
  id: number
  email: string
  name: string
  role: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = async () => {
    const token = tokenStorage.get()

    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const response = await getCurrentUser()
      if (response.success && response.data) {
        setUser(response.data)
      } else {
        setUser(null)
        tokenStorage.remove()
      }
    } catch (error) {
      console.error("Failed to fetch user:", error)
      setUser(null)
      tokenStorage.remove()
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    try {
      await apiLogout()
    } catch (error) {
      console.error("Logout error:", error)
    } finally {
      setUser(null)
      tokenStorage.remove()
    }
  }

  useEffect(() => {
    refreshUser()
  }, [])

  return <AuthContext.Provider value={{ user, loading, logout, refreshUser }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
