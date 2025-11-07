package com.smartshield.security.jwt;

import com.smartshield.config.CookieProperties;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.Optional;

@Component
@RequiredArgsConstructor
public class CookieUtil {
    
    private final CookieProperties cookieProperties;
    
    /**
     * RefreshToken 쿠키 생성
     */
    public void addRefreshTokenCookie(HttpServletResponse response, String refreshToken) {
        Cookie cookie = new Cookie(cookieProperties.getRefreshTokenName(), refreshToken);
        cookie.setHttpOnly(cookieProperties.getHttpOnly());
        cookie.setSecure(cookieProperties.getSecure());
        cookie.setPath("/");
        cookie.setMaxAge(cookieProperties.getMaxAge());
        
        response.addCookie(cookie);
    }
    
    /**
     * Request에서 RefreshToken 쿠키 추출
     */
    public Optional<String> getRefreshTokenFromCookie(HttpServletRequest request) {
        Cookie[] cookies = request.getCookies();
        
        if (cookies == null) {
            return Optional.empty();
        }
        
        return Arrays.stream(cookies)
            .filter(cookie -> cookieProperties.getRefreshTokenName().equals(cookie.getName()))
            .map(Cookie::getValue)
            .findFirst();
    }
    
    /**
     * RefreshToken 쿠키 삭제
     */
    public void deleteRefreshTokenCookie(HttpServletResponse response) {
        Cookie cookie = new Cookie(cookieProperties.getRefreshTokenName(), null);
        cookie.setHttpOnly(true);
        cookie.setSecure(cookieProperties.getSecure());
        cookie.setPath("/");
        cookie.setMaxAge(0);
        
        response.addCookie(cookie);
    }
}
