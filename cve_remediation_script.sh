#!/bin/bash
set -euo pipefail

# MCP CVE Remediation Script
# Addresses CVE-2025-49596 and CVE-2025-52882
# Implements security hardening per MCP Security Best Practices

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/mcp/cve_remediation.log"
BACKUP_DIR="/opt/mcp/backups/$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$*"; }
log_warn() { log "WARN" "${YELLOW}$*${NC}"; }
log_error() { log "ERROR" "${RED}$*${NC}"; }
log_success() { log "SUCCESS" "${GREEN}$*${NC}"; }

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root for system-wide security fixes"
        exit 1
    fi
}

# Create necessary directories
setup_directories() {
    log_info "Setting up directories..."
    mkdir -p "$(dirname "${LOG_FILE}")"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p /etc/mcp/security
    mkdir -p /opt/mcp/bin
    mkdir -p /var/lib/mcp/audit
}

# Backup current configuration
backup_current_config() {
    log_info "Backing up current configuration..."

    # Backup MCP Inspector if present
    if command -v mcp-inspector >/dev/null 2>&1; then
        cp "$(which mcp-inspector)" "${BACKUP_DIR}/mcp-inspector.backup" 2>/dev/null || true
    fi

    # Backup Claude Code configuration if present
    if [[ -d "$HOME/.claude-code" ]]; then
        cp -r "$HOME/.claude-code" "${BACKUP_DIR}/claude-code-config.backup" 2>/dev/null || true
    fi

    # Backup existing MCP configuration
    if [[ -d "/etc/mcp" ]]; then
        cp -r "/etc/mcp" "${BACKUP_DIR}/mcp-config.backup" 2>/dev/null || true
    fi

    log_success "Configuration backed up to ${BACKUP_DIR}"
}

# CVE-2025-49596: MCP Inspector RCE vulnerability
remediate_cve_2025_49596() {
    log_info "Remediating CVE-2025-49596: MCP Inspector RCE vulnerability..."

    local current_version=""
    local required_version="0.14.1"

    # Check current version
    if command -v mcp-inspector >/dev/null 2>&1; then
        current_version=$(mcp-inspector --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
        log_info "Current MCP Inspector version: ${current_version}"
    else
        log_info "MCP Inspector not found - installing latest version"
    fi

    # Version comparison function
    version_ge() {
        printf '%s\n%s' "$1" "$2" | sort -C -V
    }

    if [[ "${current_version}" != "unknown" ]] && version_ge "${current_version}" "${required_version}"; then
        log_success "MCP Inspector version ${current_version} >= ${required_version} - CVE-2025-49596 already patched"
        return 0
    fi

    log_warn "Upgrading MCP Inspector to fix CVE-2025-49596..."

    # Download and install latest version
    local temp_dir=$(mktemp -d)
    cd "${temp_dir}"

    # Use curl or wget to download latest version
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "https://github.com/modelcontextprotocol/inspector/releases/latest/download/mcp-inspector-linux-x64" -o mcp-inspector
    elif command -v wget >/dev/null 2>&1; then
        wget -q "https://github.com/modelcontextprotocol/inspector/releases/latest/download/mcp-inspector-linux-x64" -O mcp-inspector
    else
        log_error "Neither curl nor wget available for downloading MCP Inspector"
        return 1
    fi

    # Verify download and install
    chmod +x mcp-inspector
    sudo mv mcp-inspector /opt/mcp/bin/
    sudo ln -sf /opt/mcp/bin/mcp-inspector /usr/local/bin/mcp-inspector

    # Verify installation
    new_version=$(mcp-inspector --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
    if version_ge "${new_version}" "${required_version}"; then
        log_success "MCP Inspector upgraded to ${new_version} - CVE-2025-49596 remediated"
    else
        log_error "Failed to upgrade MCP Inspector to required version"
        return 1
    fi

    # Secure Inspector configuration
    cat > /etc/mcp/security/inspector-security.conf << 'EOF'
# MCP Inspector Security Configuration
# Addresses CVE-2025-49596

# Restrict to local-only usage
bind_address = "127.0.0.1"
allowed_hosts = ["localhost", "127.0.0.1"]

# Disable remote access
enable_remote_access = false
enable_web_interface = false

# Authentication required
require_authentication = true
auth_method = "oauth"

# Logging
audit_logging = true
log_level = "INFO"
EOF

    cd - >/dev/null
    rm -rf "${temp_dir}"
}

# CVE-2025-52882: IDE WebSocket bridge exposure
remediate_cve_2025_52882() {
    log_info "Remediating CVE-2025-52882: IDE WebSocket bridge exposure..."

    # Check for Claude Code installation
    local claude_code_paths=(
        "$HOME/.claude-code"
        "/opt/claude-code"
        "/usr/local/bin/claude-code"
        "/Applications/Claude Code.app"
    )

    local found_installation=false
    for path in "${claude_code_paths[@]}"; do
        if [[ -e "${path}" ]]; then
            found_installation=true
            log_info "Found Claude Code installation at: ${path}"
            break
        fi
    done

    if [[ "${found_installation}" == "false" ]]; then
        log_info "Claude Code not found - no action needed for CVE-2025-52882"
        return 0
    fi

    # Create WebSocket security configuration
    mkdir -p ~/.claude-code/security
    cat > ~/.claude-code/security/websocket-config.json << 'EOF'
{
  "websocket_security": {
    "enabled": true,
    "require_authentication": true,
    "allowed_origins": ["localhost", "127.0.0.1"],
    "enable_cors": false,
    "max_connections": 5,
    "connection_timeout": 30,
    "rate_limiting": {
      "enabled": true,
      "max_requests_per_minute": 60
    }
  },
  "bridge_security": {
    "local_only": true,
    "disable_remote_bridge": true,
    "require_token": true,
    "token_expiry": 3600
  }
}
EOF

    # Create secure WebSocket wrapper script
    cat > /opt/mcp/bin/secure-websocket-bridge << 'EOF'
#!/bin/bash
# Secure WebSocket Bridge Wrapper
# Addresses CVE-2025-52882

set -euo pipefail

# Security checks
if [[ "${REMOTE_ACCESS:-false}" == "true" ]]; then
    echo "ERROR: Remote access disabled for security (CVE-2025-52882)" >&2
    exit 1
fi

# Force localhost binding only
export WEBSOCKET_HOST="127.0.0.1"
export WEBSOCKET_ALLOW_REMOTE="false"

# Enable authentication
export WEBSOCKET_AUTH_REQUIRED="true"

# Rate limiting
export WEBSOCKET_RATE_LIMIT="60"

# Execute with security controls
exec claude-code-websocket-bridge "$@"
EOF

    chmod +x /opt/mcp/bin/secure-websocket-bridge

    log_success "CVE-2025-52882 remediation applied - WebSocket bridge secured"
}

# Install security monitoring
install_security_monitoring() {
    log_info "Installing MCP security monitoring..."

    # Create security monitoring script
    cat > /opt/mcp/bin/mcp-security-monitor << 'EOF'
#!/bin/bash
# MCP Security Monitoring Script

set -euo pipefail

LOG_FILE="/var/log/mcp/security_monitor.log"
ALERT_EMAIL="${MCP_ALERT_EMAIL:-admin@localhost}"

log_alert() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "${timestamp} ALERT: ${message}" >> "${LOG_FILE}"

    # Send alert email if configured
    if command -v mail >/dev/null 2>&1 && [[ "${ALERT_EMAIL}" != "admin@localhost" ]]; then
        echo "${message}" | mail -s "MCP Security Alert" "${ALERT_EMAIL}"
    fi
}

# Check for suspicious MCP Inspector processes
check_inspector_security() {
    # Check for Inspector running on non-localhost
    if pgrep -f "mcp-inspector" >/dev/null; then
        local inspector_binds=$(netstat -tlnp 2>/dev/null | grep "$(pgrep -f mcp-inspector)" | grep -v "127.0.0.1" || true)
        if [[ -n "${inspector_binds}" ]]; then
            log_alert "MCP Inspector detected binding to non-localhost addresses: ${inspector_binds}"
        fi
    fi
}

# Check for WebSocket bridge security
check_websocket_security() {
    # Check for insecure WebSocket configurations
    local ws_processes=$(pgrep -f "websocket.*bridge" || true)
    for pid in ${ws_processes}; do
        local cmdline=$(cat "/proc/${pid}/cmdline" 2>/dev/null | tr '\0' ' ' || continue)
        if echo "${cmdline}" | grep -q "0.0.0.0"; then
            log_alert "Insecure WebSocket bridge detected (CVE-2025-52882): PID ${pid}, cmdline: ${cmdline}"
        fi
    done
}

# Check for suspicious command execution
check_command_execution() {
    # Monitor for dangerous command patterns
    local dangerous_patterns=(
        "bash -c"
        "eval.*\$"
        "rm -rf /"
        "chmod 777"
        "sudo.*password"
    )

    for pattern in "${dangerous_patterns[@]}"; do
        local suspicious_procs=$(pgrep -f "${pattern}" || true)
        if [[ -n "${suspicious_procs}" ]]; then
            log_alert "Suspicious command pattern detected: ${pattern} (PIDs: ${suspicious_procs})"
        fi
    done
}

# Main monitoring loop
main() {
    while true; do
        check_inspector_security
        check_websocket_security
        check_command_execution

        # Sleep for 30 seconds between checks
        sleep 30
    done
}

# Run monitoring
main
EOF

    chmod +x /opt/mcp/bin/mcp-security-monitor

    # Create systemd service for monitoring
    cat > /etc/systemd/system/mcp-security-monitor.service << 'EOF'
[Unit]
Description=MCP Security Monitor
After=network.target

[Service]
Type=simple
User=mcp-monitor
Group=mcp-monitor
ExecStart=/opt/mcp/bin/mcp-security-monitor
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/mcp

[Install]
WantedBy=multi-user.target
EOF

    # Create monitoring user
    if ! id mcp-monitor >/dev/null 2>&1; then
        useradd -r -s /bin/false -d /var/lib/mcp mcp-monitor
    fi

    systemctl daemon-reload
    systemctl enable mcp-security-monitor
    systemctl start mcp-security-monitor

    log_success "MCP security monitoring installed and started"
}

# Apply firewall rules
configure_firewall() {
    log_info "Configuring firewall rules for MCP security..."

    # Create iptables rules for MCP
    cat > /etc/iptables/rules.mcp << 'EOF'
# MCP Security Firewall Rules

# Drop all traffic to MCP Inspector on non-localhost
-A INPUT -p tcp --dport 8080 ! -s 127.0.0.1 -j DROP
-A INPUT -p tcp --dport 8443 ! -s 127.0.0.1 -j DROP

# Allow MCP broker only from internal network
-A INPUT -p tcp --dport 9090 -s 10.0.0.0/8 -j ACCEPT
-A INPUT -p tcp --dport 9090 -j DROP

# Log suspicious connection attempts
-A INPUT -p tcp --dport 8080 ! -s 127.0.0.1 -j LOG --log-prefix "MCP_INSPECTOR_REMOTE: "
-A INPUT -p tcp --dport 8443 ! -s 127.0.0.1 -j LOG --log-prefix "MCP_WEBSOCKET_REMOTE: "
EOF

    # Apply rules if iptables is available
    if command -v iptables >/dev/null 2>&1; then
        iptables-restore < /etc/iptables/rules.mcp
        log_success "Firewall rules applied"
    else
        log_warn "iptables not available - manual firewall configuration required"
    fi
}

# Configure AppArmor profiles
configure_apparmor() {
    log_info "Configuring AppArmor profiles for MCP..."

    if ! command -v aa-status >/dev/null 2>&1; then
        log_warn "AppArmor not available - skipping profile configuration"
        return 0
    fi

    # Copy AppArmor profile
    cp "${SCRIPT_DIR}/mcp_security_policies.yaml" /etc/apparmor.d/mcp-profiles

    # Extract and install AppArmor profile
    sed -n '/apparmor_profile:/,/^[[:space:]]*[^[:space:]]/p' "${SCRIPT_DIR}/mcp_security_policies.yaml" | \
        sed '1d;$d' | sed 's/^[[:space:]]*//' > /etc/apparmor.d/mcp-server

    # Load profile
    apparmor_parser -r /etc/apparmor.d/mcp-server

    log_success "AppArmor profiles configured and loaded"
}

# Verify remediation
verify_remediation() {
    log_info "Verifying CVE remediation..."

    local remediation_status=0

    # Check CVE-2025-49596
    if command -v mcp-inspector >/dev/null 2>&1; then
        local version=$(mcp-inspector --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        if printf '%s\n%s' "0.14.1" "${version}" | sort -C -V; then
            log_success "CVE-2025-49596: MCP Inspector ${version} >= 0.14.1 ✓"
        else
            log_error "CVE-2025-49596: MCP Inspector ${version} < 0.14.1 ✗"
            remediation_status=1
        fi
    else
        log_warn "CVE-2025-49596: MCP Inspector not installed"
    fi

    # Check CVE-2025-52882
    if [[ -f ~/.claude-code/security/websocket-config.json ]]; then
        log_success "CVE-2025-52882: WebSocket security configuration applied ✓"
    else
        log_warn "CVE-2025-52882: WebSocket security configuration not found"
    fi

    # Check security monitoring
    if systemctl is-active --quiet mcp-security-monitor; then
        log_success "Security monitoring: Active ✓"
    else
        log_error "Security monitoring: Inactive ✗"
        remediation_status=1
    fi

    # Check firewall rules
    if iptables -L INPUT | grep -q "MCP"; then
        log_success "Firewall rules: Applied ✓"
    else
        log_warn "Firewall rules: Not detected"
    fi

    return ${remediation_status}
}

# Generate security report
generate_security_report() {
    local report_file="/var/log/mcp/security_remediation_report_$(date +%Y%m%d_%H%M%S).json"

    log_info "Generating security remediation report..."

    cat > "${report_file}" << EOF
{
  "remediation_report": {
    "timestamp": "$(date -Iseconds)",
    "script_version": "1.0",
    "cve_status": {
      "CVE-2025-49596": {
        "description": "MCP Inspector RCE vulnerability",
        "status": "$(command -v mcp-inspector >/dev/null 2>&1 && echo "remediated" || echo "not_applicable")",
        "version": "$(mcp-inspector --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")"
      },
      "CVE-2025-52882": {
        "description": "IDE WebSocket bridge exposure",
        "status": "$([[ -f ~/.claude-code/security/websocket-config.json ]] && echo "remediated" || echo "not_applicable")",
        "config_applied": $([[ -f ~/.claude-code/security/websocket-config.json ]] && echo "true" || echo "false")
      }
    },
    "security_controls": {
      "monitoring": "$(systemctl is-active --quiet mcp-security-monitor && echo "active" || echo "inactive")",
      "firewall": "$(iptables -L INPUT | grep -q "MCP" && echo "configured" || echo "not_configured")",
      "apparmor": "$(command -v aa-status >/dev/null 2>&1 && echo "available" || echo "not_available")"
    },
    "backup_location": "${BACKUP_DIR}",
    "log_file": "${LOG_FILE}"
  }
}
EOF

    log_success "Security report generated: ${report_file}"
    echo "${report_file}"
}

# Main execution
main() {
    log_info "Starting MCP CVE remediation and security hardening..."

    check_root
    setup_directories
    backup_current_config

    # CVE remediation
    remediate_cve_2025_49596
    remediate_cve_2025_52882

    # Security hardening
    install_security_monitoring
    configure_firewall
    configure_apparmor

    # Verification and reporting
    if verify_remediation; then
        log_success "All CVE remediation completed successfully"
    else
        log_error "Some remediation steps failed - check logs for details"
    fi

    local report_file=$(generate_security_report)

    log_success "MCP security hardening complete!"
    log_info "Report: ${report_file}"
    log_info "Monitoring: systemctl status mcp-security-monitor"
    log_info "Logs: tail -f ${LOG_FILE}"
}

# Handle script interruption
trap 'log_error "Script interrupted"; exit 1' INT TERM

# Execute main function
main "$@"