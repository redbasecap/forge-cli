//! Read Claude Code OAuth credentials from macOS Keychain.
//!
//! Priority: Keychain → FORGE_API_KEY → ANTHROPIC_API_KEY

use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Deserialize;
// Logging via eprintln since tracing is not in runtime deps.
macro_rules! debug { ($($t:tt)*) => { /* silent */ }; }
macro_rules! info { ($($t:tt)*) => { eprintln!("[forge-auth] {}", format!($($t)*)); }; }
macro_rules! warn { ($($t:tt)*) => { eprintln!("[forge-auth] WARN: {}", format!($($t)*)); }; }

const KEYCHAIN_SERVICE: &str = "Claude Code-credentials";
const EXPIRY_BUFFER_MS: u64 = 300_000; // 5 min buffer

#[derive(Debug, Clone, Deserialize)]
struct KeychainData {
    #[serde(rename = "claudeAiOauth")]
    claude_ai_oauth: Option<OAuthData>,
}

#[derive(Debug, Clone, Deserialize)]
struct OAuthData {
    #[serde(rename = "accessToken")]
    access_token: String,
    #[serde(rename = "refreshToken")]
    refresh_token: Option<String>,
    #[serde(rename = "expiresAt")]
    expires_at: Option<u64>,
    #[serde(rename = "subscriptionType")]
    subscription_type: Option<String>,
    #[serde(rename = "rateLimitTier")]
    rate_limit_tier: Option<String>,
}

/// Authentication source and credentials for Forge CLI.
#[derive(Debug, Clone)]
pub struct ForgeAuth {
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub expires_at: Option<u64>,
    pub source: AuthSource,
    pub plan: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum AuthSource {
    Keychain,
    EnvForgeApiKey,
    EnvAnthropicApiKey,
}

impl std::fmt::Display for AuthSource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AuthSource::Keychain => write!(f, "keychain"),
            AuthSource::EnvForgeApiKey => write!(f, "env:FORGE_API_KEY"),
            AuthSource::EnvAnthropicApiKey => write!(f, "env:ANTHROPIC_API_KEY"),
        }
    }
}

impl ForgeAuth {
    /// Load credentials from Keychain or environment variables.
    pub fn load() -> Option<Self> {
        // 1. Try macOS Keychain
        #[cfg(target_os = "macos")]
        if let Some(auth) = Self::from_keychain() {
            info!("Auth: loaded from macOS Keychain (plan: {})",
                auth.plan.as_deref().unwrap_or("unknown"));
            return Some(auth);
        }

        // 2. Try FORGE_API_KEY
        if let Ok(key) = std::env::var("FORGE_API_KEY") {
            if !key.is_empty() {
                info!("Auth: using FORGE_API_KEY");
                return Some(Self {
                    access_token: key,
                    refresh_token: None,
                    expires_at: None,
                    source: AuthSource::EnvForgeApiKey,
                    plan: None,
                });
            }
        }

        // 3. Try ANTHROPIC_API_KEY
        if let Ok(key) = std::env::var("ANTHROPIC_API_KEY") {
            if !key.is_empty() {
                info!("Auth: using ANTHROPIC_API_KEY");
                return Some(Self {
                    access_token: key,
                    refresh_token: None,
                    expires_at: None,
                    source: AuthSource::EnvAnthropicApiKey,
                    plan: None,
                });
            }
        }

        warn!("Auth: no credentials found");
        None
    }

    /// Read from macOS Keychain.
    #[cfg(target_os = "macos")]
    fn from_keychain() -> Option<Self> {
        let username = std::env::var("USER").ok()?;

        let output = Command::new("security")
            .args([
                "find-generic-password",
                "-s", KEYCHAIN_SERVICE,
                "-a", &username,
                "-w",
            ])
            .output()
            .ok()?;

        if !output.status.success() {
            debug!("No Claude Code credentials in Keychain");
            return None;
        }

        let json_str = String::from_utf8(output.stdout).ok()?;
        let data: KeychainData = serde_json::from_str(json_str.trim()).ok()?;
        let oauth = data.claude_ai_oauth?;

        Some(Self {
            access_token: oauth.access_token,
            refresh_token: oauth.refresh_token,
            expires_at: oauth.expires_at,
            source: AuthSource::Keychain,
            plan: oauth.subscription_type,
        })
    }

    /// Check if the token is expired or about to expire.
    pub fn is_expired(&self) -> bool {
        match self.expires_at {
            Some(exp) => {
                let now_ms = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_millis() as u64;
                now_ms >= exp.saturating_sub(EXPIRY_BUFFER_MS)
            }
            None => false,
        }
    }

    /// Get the access token, checking expiry.
    pub fn get_token(&self) -> &str {
        if self.is_expired() {
            warn!("Auth token is expired or expiring soon");
        }
        &self.access_token
    }

    /// Return a masked version of the token for display.
    pub fn masked_token(&self) -> String {
        let t = &self.access_token;
        if t.len() > 12 {
            format!("{}...{}", &t[..8], &t[t.len()-4..])
        } else {
            "****".to_string()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_masked_token() {
        let auth = ForgeAuth {
            access_token: "sk-ant-oat01-abcdefghijklmnop".into(),
            refresh_token: None,
            expires_at: None,
            source: AuthSource::EnvForgeApiKey,
            plan: None,
        };
        let masked = auth.masked_token();
        assert!(masked.starts_with("sk-ant-o"));
        assert!(masked.contains("..."));
        assert!(!masked.contains("abcdefgh"));
    }

    #[test]
    fn test_not_expired_when_no_expiry() {
        let auth = ForgeAuth {
            access_token: "test".into(),
            refresh_token: None,
            expires_at: None,
            source: AuthSource::EnvForgeApiKey,
            plan: None,
        };
        assert!(!auth.is_expired());
    }

    #[test]
    fn test_expired_when_past() {
        let auth = ForgeAuth {
            access_token: "test".into(),
            refresh_token: None,
            expires_at: Some(1000), // way in the past
            source: AuthSource::Keychain,
            plan: None,
        };
        assert!(auth.is_expired());
    }
}
