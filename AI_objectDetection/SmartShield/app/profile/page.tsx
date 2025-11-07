"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ChevronRight, Home, MessageCircle, User, LogOut } from "lucide-react"
import { useAuth } from "@/contexts/auth-context"
import { Button } from "@/components/ui/button"

export default function ProfilePage() {
  const router = useRouter()
  const { user, loading, logout } = useAuth()

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login")
    }
  }, [user, loading, router])

  const handleLogout = async () => {
    await logout()
    router.push("/login")
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">로딩 중...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <main className="flex-1 p-6">
        <h1 className="text-2xl font-bold mb-8">회원 정보</h1>

        <div className="bg-white rounded-xl p-6 mb-6 max-w-md">
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-500">이메일</p>
              <p className="font-medium">{user.email}</p>
            </div>
            {user.name && (
              <div>
                <p className="text-sm text-gray-500">이름</p>
                <p className="font-medium">{user.name}</p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-500">권한</p>
              <p className="font-medium">{user.role === "ADMIN" ? "관리자" : "사용자"}</p>
            </div>
          </div>
        </div>

        <div className="space-y-3 max-w-md">
          <Link
            href="/profile/edit"
            className="flex items-center justify-between bg-white p-4 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <span className="font-medium">회원정보 수정</span>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </Link>

          <Link
            href="/business-storage"
            className="flex items-center justify-between bg-white p-4 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <span className="font-medium">영상 저장 내역</span>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </Link>

          <Link
            href="/business-analysis-history"
            className="flex items-center justify-between bg-white p-4 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <span className="font-medium">영상 분석 내역</span>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </Link>

          <Link
            href="/emergency-history"
            className="flex items-center justify-between bg-white p-4 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <span className="font-medium">긴급 요청 내역</span>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </Link>

          <Button
            onClick={handleLogout}
            variant="outline"
            className="w-full flex items-center justify-center gap-2 p-4 rounded-xl border-red-200 text-red-600 hover:bg-red-50 bg-transparent"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">로그아웃</span>
          </Button>
        </div>
      </main>

      <nav className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="flex justify-around items-center max-w-md mx-auto">
          <Link href="/" className="flex flex-col items-center gap-1 text-gray-400">
            <Home className="w-6 h-6" />
            <span className="text-xs font-medium">홈</span>
          </Link>
          <Link href="/chat" className="flex flex-col items-center gap-1 text-gray-400">
            <MessageCircle className="w-6 h-6" />
            <span className="text-xs font-medium">채팅</span>
          </Link>
          <Link href="/profile" className="flex flex-col items-center gap-1 text-blue-600">
            <User className="w-6 h-6" />
            <span className="text-xs font-medium">회원정보</span>
          </Link>
        </div>
      </nav>
    </div>
  )
}
