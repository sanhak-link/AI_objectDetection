package com.smartshield.service;

import com.smartshield.config.JwtProperties;
import com.smartshield.dto.AuthResponse;
import com.smartshield.dto.LoginRequest;
import com.smartshield.dto.SignupRequest;
import com.smartshield.entity.RefreshToken;
import com.smartshield.entity.Role;
import com.smartshield.entity.User;
import com.smartshield.repository.RefreshTokenRepository;
import com.smartshield.repository.UserRepository;
import com.smartshield.security.jwt.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final AuthenticationManager authenticationManager;
    private final JwtProperties jwtProperties;

    /**
     * 회원가입
     */
    @Transactional
    public AuthResponse signup(SignupRequest request) {
        try {
            // 이메일 중복 검사
            if (userRepository.existsByEmail(request.getEmail())) {
                return AuthResponse.builder()
                        .success(false)
                        .message("이미 사용 중인 이메일입니다.")
                        .build();
            }

            // 사용자 생성
            User user = User.builder()
                    .email(request.getEmail())
                    .password(passwordEncoder.encode(request.getPassword()))
                    .name(request.getName())
                    .phoneNumber(request.getPhoneNumber())
                    .managementCode(request.getManagementCode())
                    .role(Role.USER)
                    .enabled(true)
                    .build();

            User savedUser = userRepository.save(user);

            // 인증 및 토큰 생성
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(
                            request.getEmail(),
                            request.getPassword()
                    )
            );

            String accessToken = jwtTokenProvider.generateAccessToken(authentication);
            String refreshToken = jwtTokenProvider.generateRefreshToken(savedUser.getEmail());

            // RefreshToken DB 저장
            saveRefreshToken(savedUser, refreshToken);

            return AuthResponse.builder()
                    .success(true)
                    .message("회원가입이 완료되었습니다.")
                    .accessToken(accessToken)
                    .user(AuthResponse.UserInfo.builder()
                            .id(savedUser.getId())
                            .email(savedUser.getEmail())
                            .name(savedUser.getName())
                            .role(savedUser.getRole().name())
                            .build())
                    .build();

        } catch (Exception e) {
            log.error("회원가입 중 오류 발생: {}", e.getMessage(), e);
            return AuthResponse.builder()
                    .success(false)
                    .message("회원가입 실패: " + e.getMessage())
                    .build();
        }
    }

    /**
     * 로그인
     */
    @Transactional(noRollbackFor = { BadCredentialsException.class })
    public AuthResponse login(LoginRequest request) {
        try {
            // 인증 시도
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(
                            request.getEmail(),
                            request.getPassword()
                    )
            );

            User user = userRepository.findByEmail(request.getEmail())
                    .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));

            // 토큰 생성
            String accessToken = jwtTokenProvider.generateAccessToken(authentication);
            String refreshToken = jwtTokenProvider.generateRefreshToken(user.getEmail());

            // RefreshToken DB 저장
            saveRefreshToken(user, refreshToken);

            return AuthResponse.builder()
                    .success(true)
                    .message("로그인 성공")
                    .accessToken(accessToken)
                    .user(AuthResponse.UserInfo.builder()
                            .id(user.getId())
                            .email(user.getEmail())
                            .name(user.getName())
                            .role(user.getRole().name())
                            .build())
                    .build();

        } catch (BadCredentialsException e) {
            log.warn("잘못된 로그인 시도: {}", e.getMessage());
            return AuthResponse.builder()
                    .success(false)
                    .message("이메일 또는 비밀번호가 올바르지 않습니다.")
                    .build();

        } catch (Exception e) {
            log.error("로그인 중 예외 발생: {}", e.getMessage(), e);
            return AuthResponse.builder()
                    .success(false)
                    .message("로그인 실패: " + e.getMessage())
                    .build();
        }
    }

    /**
     * AccessToken 재발급 (RefreshToken 회전)
     */
    @Transactional
    public AuthResponse refreshAccessToken(String refreshTokenValue) {
        try {
            // RefreshToken 검증
            if (!jwtTokenProvider.validateToken(refreshTokenValue)) {
                return AuthResponse.builder()
                        .success(false)
                        .message("유효하지 않은 RefreshToken입니다.")
                        .build();
            }

            // DB에서 RefreshToken 조회
            RefreshToken refreshToken = refreshTokenRepository.findByToken(refreshTokenValue)
                    .orElseThrow(() -> new RuntimeException("RefreshToken을 찾을 수 없습니다."));

            // 만료 또는 무효화 확인
            if (refreshToken.isExpired() || refreshToken.getRevoked()) {
                return AuthResponse.builder()
                        .success(false)
                        .message("만료되거나 무효화된 RefreshToken입니다.")
                        .build();
            }

            User user = refreshToken.getUser();

            // 새로운 AccessToken 생성
            Authentication authentication = new UsernamePasswordAuthenticationToken(
                    user, null, user.getAuthorities()
            );
            String newAccessToken = jwtTokenProvider.generateAccessToken(authentication);

            // 새로운 RefreshToken 생성 (회전)
            String newRefreshToken = jwtTokenProvider.generateRefreshToken(user.getEmail());

            // 기존 RefreshToken 무효화
            refreshToken.revoke();

            // 새로운 RefreshToken 저장
            saveRefreshToken(user, newRefreshToken);

            return AuthResponse.builder()
                    .success(true)
                    .message("토큰 재발급 성공")
                    .accessToken(newAccessToken)
                    .user(AuthResponse.UserInfo.builder()
                            .id(user.getId())
                            .email(user.getEmail())
                            .name(user.getName())
                            .role(user.getRole().name())
                            .build())
                    .build();

        } catch (Exception e) {
            log.error("토큰 재발급 중 오류: {}", e.getMessage(), e);
            return AuthResponse.builder()
                    .success(false)
                    .message("토큰 재발급 실패: " + e.getMessage())
                    .build();
        }
    }

    /**
     * 로그아웃 (모든 RefreshToken 무효화)
     */
    @Transactional
    public void logout(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        refreshTokenRepository.revokeAllByUser(user);
    }

    /**
     * RefreshToken DB 저장
     */
    private void saveRefreshToken(User user, String tokenValue) {
        LocalDateTime expiryDate = LocalDateTime.now()
                .plusSeconds(jwtProperties.getRefreshTokenExpiration() / 1000);

        RefreshToken refreshToken = RefreshToken.builder()
                .token(tokenValue)
                .user(user)
                .expiryDate(expiryDate)
                .revoked(false)
                .build();

        refreshTokenRepository.save(refreshToken);
    }
}
