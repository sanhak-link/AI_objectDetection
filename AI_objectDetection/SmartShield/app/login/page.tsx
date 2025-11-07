"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { login } from "@/lib/api"
import { useAuth } from "@/contexts/auth-context"

export default function LoginPage() {
  const router = useRouter()
  const { refreshUser } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      const response = await login({ email, password })

      if (response.success) {
        await refreshUser()
        router.push("/")
      } else {
        setError(response.message || "로그인에 실패했습니다.")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인 중 오류가 발생했습니다.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-sm p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="w-32 h-32 mb-6">
            <img
              src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/image-dwPacRWBvE3z0NsBvLB2Zmc9v1nY8h.png"
              alt="SMARTSHIELD Mascot"
              className="w-full h-full object-contain"
            />
          </div>
          <h1 className="text-2xl font-bold">SMARTSHIELD</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">
              이메일
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="이메일을 입력하세요"
              className="h-12 bg-gray-50 border-0"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium">
              비밀번호
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="········"
              className="h-12 bg-gray-50 border-0"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <Button
            type="submit"
            className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl mt-6"
            disabled={loading}
          >
            {loading ? "로그인 중..." : "로그인"}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm">
          <span className="text-gray-600">계정이 없으신가요?</span>{" "}
          <Link href="/signup" className="text-blue-600 font-medium hover:underline">
            회원가입
          </Link>
        </div>
      </div>
    </div>
  )
}
