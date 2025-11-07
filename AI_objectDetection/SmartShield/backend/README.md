# SmartShield Backend

Spring Boot 3.3 + Spring Security 6 + JWT 기반 인증 시스템

## 기술 스택

- **Spring Boot**: 3.3.0
- **Spring Security**: 6.x
- **JWT**: jjwt 0.12.5
- **Database**: H2 (개발용), JPA/Hibernate
- **Java**: 17

## 주요 기능

### 인증 시스템
- ✅ 이메일/비밀번호 기반 로그인
- ✅ BCrypt 비밀번호 암호화
- ✅ JWT AccessToken (JSON 응답)
- ✅ JWT RefreshToken (HttpOnly 쿠키)
- ✅ RefreshToken 회전(Rotation) 전략
- ✅ RefreshToken DB 저장 및 무효화
- ✅ 완전 무상태(Stateless) 세션 관리

### 보안 기능
- ✅ CORS 설정 (localhost:3000 허용)
- ✅ CSRF 비활성화 (JWT 사용)
- ✅ HttpOnly/Secure 쿠키
- ✅ 역할 기반 접근 제어 (ROLE_USER, ROLE_ADMIN)
- ✅ 시크릿 외부화 (환경 변수)

## API 엔드포인트

### 인증 API (`/api/auth`)

#### 회원가입
\`\`\`http
POST /api/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "name": "홍길동",
  "phoneNumber": "010-1234-5678",
  "managementCode": "ABC123"
}
\`\`\`

#### 로그인
\`\`\`http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
\`\`\`

**응답:**
\`\`\`json
{
  "success": true,
  "message": "로그인 성공",
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동",
    "role": "USER"
  }
}
\`\`\`

#### AccessToken 재발급
\`\`\`http
POST /api/auth/refresh
Cookie: refreshToken=<refresh_token>
\`\`\`

#### 로그아웃
\`\`\`http
POST /api/auth/logout
Authorization: Bearer <access_token>
\`\`\`

#### 현재 사용자 정보
\`\`\`http
GET /api/auth/me
Authorization: Bearer <access_token>
\`\`\`

### 사용자 API (`/api/users`)

#### 영상 저장 내역
\`\`\`http
GET /api/users/videos
Authorization: Bearer <access_token>
\`\`\`

#### 영상 분석 내역
\`\`\`http
GET /api/users/analysis
Authorization: Bearer <access_token>
\`\`\`

### 관리자 API (`/api/admin`)

#### 긴급 요청 내역
\`\`\`http
GET /api/admin/emergency
Authorization: Bearer <access_token>
\`\`\`
*ROLE_ADMIN 권한 필요*

## 실행 방법

### 1. 환경 변수 설정

\`\`\`bash
# JWT 시크릿 (256비트 이상)
export JWT_SECRET=your-256-bit-secret-key-change-this-in-production-environment
\`\`\`

### 2. 애플리케이션 실행

\`\`\`bash
cd backend
./mvnw spring-boot:run
\`\`\`

서버는 `http://localhost:8080`에서 실행됩니다.

### 3. H2 Console 접속

개발 중 데이터베이스 확인:
- URL: http://localhost:8080/h2-console
- JDBC URL: `jdbc:h2:mem:smartshield`
- Username: `sa`
- Password: (비어있음)

## 설정 파일

### application.properties

```properties
# JWT 설정
jwt.secret=${JWT_SECRET}
jwt.access-token-expiration=900000        # 15분
jwt.refresh-token-expiration=604800000    # 7일

# 쿠키 설정
cookie.refresh-token-name=refreshToken
cookie.http-only=true
cookie.secure=false                        # 프로덕션에서는 true
cookie.same-site=Lax
cookie.max-age=604800                      # 7일

# CORS 설정
cors.allowed-origins=http://localhost:3000
