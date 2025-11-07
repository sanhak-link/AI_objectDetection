"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ChevronLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/contexts/auth-context"

export default function ProfileEditPage() {
  const router = useRouter()
  const { user, loading } = useAuth()
  const [formData, setFormData] = useState({
    name: "",
    phoneNumber: "",
    managementCode: "",
    password: "",
    passwordConfirm: "",
  })
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login")
    } else if (user) {
      setFormData((prev) => ({
        ...prev,
        name: user.name || "",
        // phoneNumber와 managementCode는 백엔드에서 가져와야 함
      }))
    }
  }, [user, loading, router])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccess("")

    // 비밀번호 변경 시 확인
    if (formData.password || formData.passwordConfirm) {
      if (formData.password !== formData.passwordConfirm) {
        setError("비밀번호가 일치하지 않습니다.")
        return
      }
      if (formData.password.length < 6) {
        setError("비밀번호는 최소 6자 이상이어야 합니다.")
        return
      }
    }

    setSubmitting(true)

    try {
      // TODO: 백엔드 API 연동 필요
      // const response = await updateProfile(formData)

      // 임시 성공 메시지
      setSuccess("회원정보가 수정되었습니다.")
      setTimeout(() => {
        router.push("/profile")
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : "수정 중 오류가 발생했습니다.")
    } finally {
      setSubmitting(false)
    }
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
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/profile" className="text-gray-600">
            <ChevronLeft className="w-6 h-6" />
          </Link>
          <h1 className="text-xl font-bold">회원 정보 수정</h1>
        </div>
      </header>

      <main className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}
          {success && <div className="bg-green-50 text-green-600 p-3 rounded-lg text-sm">{success}</div>}

          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">
              이메일
            </Label>
            <Input id="email" type="email" className="h-12 bg-gray-100 border-gray-200" value={user.email} disabled />
            <p className="text-xs text-gray-500">이메일은 변경할 수 없습니다.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="name" className="text-sm font-medium">
              이름
            </Label>
            <Input
              id="name"
              name="name"
              type="text"
              className="h-12 bg-white border-gray-200"
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
              className="h-12 bg-white border-gray-200"
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
              className="h-12 bg-white border-gray-200"
              value={formData.managementCode}
              onChange={handleChange}
            />
          </div>

          <div className="pt-4 border-t border-gray-200">
            <p className="text-sm font-medium mb-4">비밀번호 변경 (선택사항)</p>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  새 비밀번호
                </Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  placeholder="········"
                  className="h-12 bg-white border-gray-200"
                  value={formData.password}
                  onChange={handleChange}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="passwordConfirm" className="text-sm font-medium">
                  새 비밀번호 확인
                </Label>
                <Input
                  id="passwordConfirm"
                  name="passwordConfirm"
                  type="password"
                  placeholder="········"
                  className="h-12 bg-white border-gray-200"
                  value={formData.passwordConfirm}
                  onChange={handleChange}
                />
              </div>
            </div>
          </div>

          <Button
            type="submit"
            className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl mt-6"
            disabled={submitting}
          >
            {submitting ? "처리 중..." : "수정완료"}
          </Button>
        </form>
      </main>
    </div>
  )
}
