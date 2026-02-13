"""
Security validation utilities for startup checks.

This module enforces security requirements at application startup
to prevent insecure runtime defaults.
"""
import logging
import os

logger = logging.getLogger(__name__)


class SecurityValidationError(Exception):
    """Raised when a security validation check fails."""
    pass


def is_local_environment():
    """
    Determine if running in local/development environment.
    
    Returns:
        bool: True if local environment (localhost/127.0.0.1), False otherwise
    """
    # Check if APP_URL indicates local environment
    app_url = os.environ.get('APP_URL', '')
    is_localhost = 'localhost' in app_url or '127.0.0.1' in app_url
    
    # Check DEBUG flag
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # Check for pytest
    is_test = 'PYTEST_CURRENT_TEST' in os.environ
    
    return is_localhost or debug_mode or is_test


def validate_app_secret_key(secret_key: str, environment: str = "production") -> None:
    """
    Validate that APP_SECRET_KEY is properly configured.
    
    Args:
        secret_key: The secret key to validate
        environment: Environment descriptor for error messages
        
    Raises:
        SecurityValidationError: If secret key is invalid for the environment
    """
    # Allow empty secret in test environment only
    if 'PYTEST_CURRENT_TEST' in os.environ:
        logger.info("Security validation: Skipping APP_SECRET_KEY check (test environment)")
        return
    
    # In local/dev, warn but don't fail
    if is_local_environment():
        if not secret_key or secret_key.strip() == '':
            logger.warning(
                "Security validation: APP_SECRET_KEY is empty in development environment. "
                "This is acceptable for local testing but MUST be set for production."
            )
        return
    
    # In production, enforce non-empty secret
    if not secret_key or secret_key.strip() == '':
        raise SecurityValidationError(
            "APP_SECRET_KEY must be set to a non-empty value in production. "
            "Generate a secure random secret and set it via environment variable. "
            "Example: export APP_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
        )
    
    # Warn if secret is suspiciously short
    if len(secret_key) < 16:
        logger.warning(
            f"Security validation: APP_SECRET_KEY is only {len(secret_key)} characters. "
            "Consider using a longer secret (32+ characters recommended)."
        )
    
    logger.info("Security validation: APP_SECRET_KEY is properly configured")


def should_allow_insecure_oauth_transport() -> bool:
    """
    Determine if insecure OAuth transport should be allowed.
    
    Insecure transport (HTTP instead of HTTPS) should only be enabled
    for local development or test environments.
    
    Returns:
        bool: True if insecure transport is allowed, False otherwise
    """
    # Always allow in test environment
    if 'PYTEST_CURRENT_TEST' in os.environ:
        return True
    
    # Check if we're in a local environment
    if is_local_environment():
        logger.info(
            "Security validation: Allowing insecure OAuth transport (local/development environment)"
        )
        return True
    
    # Production environment - enforce secure transport
    logger.info(
        "Security validation: Enforcing secure OAuth transport (production environment)"
    )
    return False


def validate_oauth_security() -> None:
    """
    Validate OAuth security configuration at startup.
    
    Raises:
        SecurityValidationError: If OAuth configuration is insecure for the environment
    """
    if not should_allow_insecure_oauth_transport():
        app_url = os.environ.get('APP_URL', '')
        if app_url and not app_url.startswith('https://'):
            raise SecurityValidationError(
                f"APP_URL must use HTTPS in production environment. Current value: {app_url}"
            )


def run_startup_security_validation(config) -> dict:
    """
    Run all security validations at application startup.
    
    Args:
        config: Configuration module or object
        
    Returns:
        dict: Validation results for observability
        
    Raises:
        SecurityValidationError: If critical security validations fail
    """
    results = {
        'is_local_environment': is_local_environment(),
        'insecure_transport_allowed': should_allow_insecure_oauth_transport(),
        'checks_passed': []
    }
    
    logger.info("Starting security validation checks...")
    
    try:
        # Validate APP_SECRET_KEY
        app_secret = getattr(config, 'APP_SECRET_KEY', '')
        validate_app_secret_key(app_secret)
        results['checks_passed'].append('app_secret_key')
        
        # Validate OAuth security
        validate_oauth_security()
        results['checks_passed'].append('oauth_transport')
        
        logger.info(
            f"Security validation complete. Environment: "
            f"{'local/dev' if results['is_local_environment'] else 'production'}, "
            f"Checks passed: {', '.join(results['checks_passed'])}"
        )
        
        return results
        
    except SecurityValidationError as e:
        logger.error(f"Security validation failed: {e}")
        raise
