"""
Authlib-based Discord OAuth2 client wrapper.

This module provides the canonical Discord OAuth implementation for the API.

Structured Log Events:
- auth_flow_started: OAuth login initiated (scope, has_redirect_data)
- auth_callback_success: OAuth callback completed (token_type, has_access_token)
- auth_callback_error: OAuth callback received error (error, description)
- auth_callback_failed: OAuth token exchange failed (error)
- auth_fetch_user_success: User info fetched successfully (user_id)
- auth_fetch_user_no_token: User fetch attempted without session token
- auth_fetch_user_failed: User fetch failed (error)
- auth_token_revoked: Token cleared from session
- auth_required_redirect: Authorization required, redirecting to login (original_path)
"""

import logging
from typing import Optional, List, Any, Dict
from functools import wraps
import secrets

from quart import session, redirect, url_for, request
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749.errors import OAuth2Error

logger = logging.getLogger(__name__)


class AuthlibDiscordOAuth:
    """
    Authlib-based Discord OAuth2 client wrapper.
    
    Provides behavior parity with Quart-Discord for Discord OAuth operations:
    - OAuth authorize redirect (login)
    - OAuth callback token exchange
    - User fetch from Discord API
    - Session token storage/retrieval
    - Authorization decorator
    """
    
    # Discord OAuth2 endpoints
    AUTHORIZE_URL = 'https://discord.com/api/oauth2/authorize'
    TOKEN_URL = 'https://discord.com/api/oauth2/token'
    API_BASE_URL = 'https://discord.com/api/v10'
    
    def __init__(self, app, client_id: int, client_secret: str, redirect_uri: str):
        """
        Initialize Authlib Discord OAuth client.
        
        Args:
            app: Quart application instance
            client_id: Discord application client ID
            client_secret: Discord application client secret
            redirect_uri: Full OAuth callback URL
        """
        self.app = app
        self.client_id = str(client_id)
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        logger.info("AuthlibDiscordOAuth initialized (Phase 1 scaffolding)")
    
    def _create_client(self) -> AsyncOAuth2Client:
        """Create a new OAuth2 client instance."""
        return AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_endpoint=self.TOKEN_URL,
        )
    
    async def create_session(self, scope: Optional[List[str]] = None, data: Optional[dict] = None):
        """
        Create OAuth authorization redirect (login flow initiation).
        
        Args:
            scope: OAuth scopes to request (e.g., ['identify'])
            data: Additional data to preserve through OAuth flow (e.g., redirect path)
        
        Returns:
            Redirect response to Discord OAuth authorize URL
        """
        # Store additional data in session for retrieval after callback
        if data:
            session['oauth_flow_data'] = data
        
        # Override scope if provided
        if scope:
            scope_str = ' '.join(scope)
        else:
            scope_str = 'identify'
        
        # Generate and store CSRF state token
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Log auth initiation
        logger.info("auth_flow_started", extra={
            'scope': scope_str,
            'has_redirect_data': bool(data)
        })
        
        # Build authorization URL
        # Note: create_authorization_url returns (url, state) tuple
        # We manage state separately, so the returned state is unused
        client = self._create_client()
        auth_url, _ = client.create_authorization_url(
            self.AUTHORIZE_URL,
            redirect_uri=self.redirect_uri,
            scope=scope_str,
            state=state
        )
        
        return redirect(auth_url)
    
    async def callback(self) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange authorization code for token.
        
        Stores token in session and returns preserved flow data.
        
        Returns:
            dict: Data preserved from create_session call (e.g., {'redirect': '/me/'})
        
        Raises:
            OAuth2Error: On OAuth errors (denial, invalid grant, etc.)
            AccessDenied: On user denial of authorization
        """
        # Check for OAuth error response
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', '')
            logger.warning("auth_callback_error", extra={
                'error': error,
                'description': error_description
            })
            
            if error == 'access_denied':
                raise AccessDenied(error_description)
            
            raise OAuth2Error(description=error_description)
        
        # Validate CSRF state
        returned_state = request.args.get('state')
        stored_state = session.pop('oauth_state', None)
        
        if not returned_state or returned_state != stored_state:
            logger.error("auth_callback_state_mismatch", extra={
                'has_returned_state': bool(returned_state),
                'has_stored_state': bool(stored_state),
                'states_match': returned_state == stored_state if returned_state and stored_state else False
            })
            raise OAuth2Error(description="CSRF state validation failed")
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            logger.error("auth_callback_no_code", extra={
                'query_params': list(request.args.keys())
            })
            raise OAuth2Error(description="No authorization code received")
        
        try:
            # Exchange authorization code for access token
            client = self._create_client()
            token = await client.fetch_token(
                self.TOKEN_URL,
                authorization_response=str(request.url),
                redirect_uri=self.redirect_uri,
                code=code
            )
            
            # Store token in session
            session['discord_oauth_token'] = token
            
            # Log successful auth
            logger.info("auth_callback_success", extra={
                'token_type': token.get('token_type'),
                'has_access_token': bool(token.get('access_token'))
            })
            
            # Retrieve and return preserved flow data
            flow_data = session.pop('oauth_flow_data', {})
            return flow_data
            
        except OAuth2Error as e:
            logger.error("auth_callback_failed", extra={
                'error': str(e)
            })
            raise
    
    async def fetch_user(self):
        """
        Fetch Discord user information using stored access token.
        
        Returns:
            User object from Discord API (/users/@me endpoint)
        
        Raises:
            Unauthorized: If no valid token in session
        """
        token = session.get('discord_oauth_token')
        
        if not token:
            logger.warning("auth_fetch_user_no_token")
            raise Unauthorized("No OAuth token in session")
        
        try:
            # Create client and fetch user info
            client = self._create_client()
            client.token = token
            
            resp = await client.get(f"{self.API_BASE_URL}/users/@me")
            resp.raise_for_status()
            user_data = resp.json()
            
            logger.debug("auth_fetch_user_success", extra={
                'user_id': user_data.get('id')
            })
            
            return DiscordUser(user_data)
            
        except Exception as e:
            logger.error("auth_fetch_user_failed", extra={
                'error': str(e)
            })
            raise Unauthorized("Failed to fetch user") from e
    
    def revoke(self):
        """
        Revoke OAuth token by clearing session.
        
        Note: Like Quart-Discord, this only clears the local session.
        It does not call Discord's token revocation endpoint.
        """
        if 'discord_oauth_token' in session:
            session.pop('discord_oauth_token')
            logger.info("auth_token_revoked")
        
        if 'oauth_flow_data' in session:
            session.pop('oauth_flow_data')


class DiscordUser:
    """
    Discord user object wrapper for Authlib response parity.
    
    Provides attribute access compatible with Quart-Discord User object.
    """
    
    def __init__(self, data: dict):
        self._data = data
    
    def __getattr__(self, name: str):
        """Allow attribute-style access to user data."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"DiscordUser has no attribute '{name}'")
    
    def __repr__(self):
        return f"<DiscordUser id={self._data.get('id')} username={self._data.get('username')}>"


class Unauthorized(Exception):
    """Exception raised when OAuth token is missing or invalid."""


class AccessDenied(Exception):
    """Exception raised when user denies OAuth authorization."""


def requires_authorization(func):
    """
    Decorator to require Discord OAuth authorization for route access.
    
    Require a Discord OAuth session token for route access.
    Redirects to /login/ if no valid session token exists.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        token = session.get('discord_oauth_token')
        
        if not token:
            # Store original path for post-login redirect
            session['login_original_path'] = request.full_path
            logger.info("auth_required_redirect", extra={
                'original_path': request.full_path
            })
            return redirect(url_for('login'))
        
        return await func(*args, **kwargs)
    
    return wrapper
