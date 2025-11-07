const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api"

export interface SignupData {
  email: string
  password: string
  name?: string
  phoneNumber?: string
  managementCode?: string
}

export interface LoginData {
  email: string
  password: string
}

export interface AuthResponse {
  success: boolean
  message: string
  accessToken?: string
  user?: {
    id: number
    email: string
    name: string
    role: string
  }
}

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
}

// AccessToken을 localStorage에 저장/조회/삭제
export const tokenStorage = {
  get: () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("accessToken")
    }
    return null
  },
  set: (token: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("accessToken", token)
    }
  },
  remove: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("accessToken")
    }
  },
}

// API 요청 헬퍼
async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = tokenStorage.get()

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: "include", // 쿠키 포함
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "Network error" }))
    throw new Error(error.message || "API request failed")
  }

  return response.json()
}

// 회원가입
export async function signup(data: SignupData): Promise<AuthResponse> {
  const response = await apiRequest<AuthResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(data),
  })

  if (response.success && response.accessToken) {
    tokenStorage.set(response.accessToken)
  }

  return response
}

// 로그인
export async function login(data: LoginData): Promise<AuthResponse> {
  const response = await apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  })

  if (response.success && response.accessToken) {
    tokenStorage.set(response.accessToken)
  }

  return response
}

// 로그아웃
export async function logout(): Promise<ApiResponse> {
  const response = await apiRequest<ApiResponse>("/auth/logout", {
    method: "POST",
  })

  tokenStorage.remove()
  return response
}

// AccessToken 재발급
export async function refreshToken(): Promise<AuthResponse> {
  const response = await apiRequest<AuthResponse>("/auth/refresh", {
    method: "POST",
  })

  if (response.success && response.accessToken) {
    tokenStorage.set(response.accessToken)
  }

  return response
}

// 현재 사용자 정보 조회
export async function getCurrentUser(): Promise<ApiResponse> {
  return apiRequest<ApiResponse>("/auth/me")
}

// 영상 저장 내역 조회
export async function getVideos(): Promise<ApiResponse> {
  return apiRequest<ApiResponse>("/users/videos")
}

// 영상 분석 내역 조회
export async function getAnalysis(): Promise<ApiResponse> {
  return apiRequest<ApiResponse>("/users/analysis")
}
