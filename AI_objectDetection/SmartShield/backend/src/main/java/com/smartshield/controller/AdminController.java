package com.smartshield.controller;

import com.smartshield.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {
    
    /**
     * 긴급 요청 내역 (관리자 전용)
     */
    @GetMapping("/emergency")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<ApiResponse> getEmergencyRequests() {
        return ResponseEntity.ok(ApiResponse.builder()
            .success(true)
            .message("긴급 요청 내역 조회 성공")
            .data("긴급 요청 목록 데이터")
            .build());
    }
}
