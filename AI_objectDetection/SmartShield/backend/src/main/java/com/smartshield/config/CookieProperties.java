package com.smartshield.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "cookie")
public class CookieProperties {
    private String refreshTokenName;
    private Boolean httpOnly;
    private Boolean secure;
    private String sameSite;
    private Integer maxAge;
}
