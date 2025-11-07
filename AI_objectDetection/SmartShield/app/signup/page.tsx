"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { signup } from "@/lib/api"
import { useAuth } from "@/contexts/auth-context"

export default function SignupPage() {
  const router = useRouter()
  const { refreshUser } = useAuth()
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    passwordConfirm: "",
    name: "",
    phoneNumber: "",
    managementCode: "",
  })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    // 비밀번호 확인
    if (formData.password !== formData.passwordConfirm) {
      setError("비밀번호가 일치하지 않습니다.")
      return
    }

    if (formData.password.length < 6) {
      setError("비밀번호는 최소 6자 이상이어야 합니다.")
      return
    }

    setLoading(true)

    try {
      const response = await signup({
        email: formData.email,
        password: formData.password,
        name: formData.name,
        phoneNumber: formData.phoneNumber,
        managementCode: formData.managementCode,
      })

      if (response.success) {
        await refreshUser()
        router.push("/")
      } else {
        setError(response.message || "회원가입에 실패했습니다.")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "회원가입 중 오류가 발생했습니다.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-sm p-8">
        <h1 className="text-2xl font-bold mb-8">회원가입</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">
              이메일
            </Label>
            <Input
              id="email"
              name="email"
              type="email"
              className="h-12 bg-gray-50 border-0"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="name" className="text-sm font-medium">
              이름
            </Label>
            <Input
              id="name"
              name="name"
              type="text"
              className="h-12 bg-gray-50 border-0"
              value={formData.name}
              onChange={handleChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phoneNumber" className="text-sm font-medium">
              전화번호
            </Label>
            <Input
              id="phoneNumber"
              name="phoneNumber"
              type="tel"
              className="h-12 bg-gray-50 border-0"
              value={formData.phoneNumber}
              onChange={handleChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="managementCode" className="text-sm font-medium">
              관리 코드
            </Label>
            <Input
              id="managementCode"
              name="managementCode"
              type="text"
              className="h-12 bg-gray-50 border-0"
              value={formData.managementCode}
              onChange={handleChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium">
              비밀번호
            </Label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="········"
              className="h-12 bg-gray-50 border-0"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="passwordConfirm" className="text-sm font-medium">
              비밀번호 확인
            </Label>
            <Input
              id="passwordConfirm"
              name="passwordConfirm"
              type="password"
              placeholder="········"
              className="h-12 bg-gray-50 border-0"
              value={formData.passwordConfirm}
              onChange={handleChange}
              required
            />
          </div>

          <Button
            type="submit"
            className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl mt-6"
            disabled={loading}
          >
            {loading ? "처리 중..." : "확인"}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm">
          <span className="text-gray-600">계정이 있으신가요?</span>{" "}
          <Link href="/login" className="text-blue-600 font-medium hover:underline">
            로그인
          </Link>
        </div>
      </div>
    </div>
  )
}
