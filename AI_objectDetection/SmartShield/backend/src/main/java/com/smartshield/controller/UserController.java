package com.smartshield.controller;

import com.smartshield.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {
    
    /**
     * 영상 저장 내역 (인증 필요)
     */
    @GetMapping("/videos")
    @PreAuthorize("hasRole('USER')")
    public ResponseEntity<ApiResponse> getVideos(Authentication authentication) {
        return ResponseEntity.ok(ApiResponse.builder()
            .success(true)
            .message("영상 저장 내역 조회 성공")
            .data("영상 목록 데이터")
            .build());
    }
    
    /**
     * 영상 분석 내역 (인증 필요)
     */
    @GetMapping("/analysis")
    @PreAuthorize("hasRole('USER')")
    public ResponseEntity<ApiResponse> getAnalysis(Authentication authentication) {
        return ResponseEntity.ok(ApiResponse.builder()
            .success(true)
            .message("영상 분석 내역 조회 성공")
            .data("분석 목록 데이터")
            .build());
    }
}
