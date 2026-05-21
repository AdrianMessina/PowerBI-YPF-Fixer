"""
Sistema de Autenticación Modular para YPF BI Monitor
Soporta múltiples backends: Local, LDAP/AD, OAuth, Cloudera
"""

import os
import streamlit as st
from typing import Optional, Dict, Any, List
from enum import Enum
import re


class AuthBackend(Enum):
    """Tipos de backend de autenticación soportados"""
    LOCAL = "local"  # Usuario Windows + whitelist
    LDAP = "ldap"  # LDAP/Active Directory
    OAUTH = "oauth"  # OAuth2/SSO (Google, Microsoft, etc.)
    CLOUDERA = "cloudera"  # Cloudera SSO/Kerberos
    NONE = "none"  # Sin autenticación (desarrollo)


class AuthConfig:
    """Configuración de autenticación desde variables de entorno"""

    def __init__(self):
        # Backend de autenticación
        self.backend = AuthBackend(os.getenv('AUTH_BACKEND', 'local').lower())

        # Whitelist de usuarios autorizados (vacío = acceso libre para todos)
        whitelist_str = os.getenv('AUTH_WHITELIST', '')
        self.whitelist = [u.strip().lower() for u in whitelist_str.split(',') if u.strip()]

        # LDAP/AD Configuration
        self.ldap_server = os.getenv('LDAP_SERVER', '')
        self.ldap_port = int(os.getenv('LDAP_PORT', '389'))
        self.ldap_base_dn = os.getenv('LDAP_BASE_DN', '')
        self.ldap_user_dn_template = os.getenv('LDAP_USER_DN_TEMPLATE', 'cn={username},{base_dn}')
        self.ldap_use_ssl = os.getenv('LDAP_USE_SSL', 'false').lower() == 'true'

        # OAuth Configuration
        self.oauth_client_id = os.getenv('OAUTH_CLIENT_ID', '')
        self.oauth_client_secret = os.getenv('OAUTH_CLIENT_SECRET', '')
        self.oauth_redirect_uri = os.getenv('OAUTH_REDIRECT_URI', '')
        self.oauth_provider = os.getenv('OAUTH_PROVIDER', 'microsoft')  # microsoft, google, etc.

        # Cloudera Configuration
        self.cloudera_auth_endpoint = os.getenv('CLOUDERA_AUTH_ENDPOINT', '')
        self.cloudera_verify_ssl = os.getenv('CLOUDERA_VERIFY_SSL', 'true').lower() == 'true'

        # Admin users (full access to dashboard)
        admin_str = os.getenv('AUTH_ADMIN_USERS', '')
        self.admin_users = [u.strip().lower() for u in admin_str.split(',') if u.strip()]

        # Bypass authentication for development
        self.dev_mode = os.getenv('AUTH_DEV_MODE', 'false').lower() == 'true'


def _get_current_windows_user() -> str:
    """Obtener usuario Windows actual (local)"""
    return os.environ.get('USERNAME', os.environ.get('USER', '')).lower()


def _normalize_email(email: str) -> str:
    """Normalizar email para comparación (extraer username)"""
    email = email.strip().lower()
    if '@' in email:
        return email.split('@')[0]
    return email


def _validate_ldap_user(username: str, password: str, config: AuthConfig) -> bool:
    """
    Validar usuario contra LDAP/Active Directory

    Args:
        username: Username a validar
        password: Password del usuario
        config: Configuración de autenticación

    Returns:
        True si autenticación exitosa, False en caso contrario
    """
    try:
        import ldap3
        from ldap3 import Server, Connection, ALL
    except ImportError:
        st.error("⚠️ LDAP no configurado. Instalar: pip install ldap3")
        return False

    if not config.ldap_server or not config.ldap_base_dn:
        st.error("⚠️ Configuración LDAP incompleta (LDAP_SERVER, LDAP_BASE_DN)")
        return False

    try:
        # Construir DN del usuario
        user_dn = config.ldap_user_dn_template.format(
            username=username,
            base_dn=config.ldap_base_dn
        )

        # Conectar al servidor LDAP
        server = Server(
            config.ldap_server,
            port=config.ldap_port,
            use_ssl=config.ldap_use_ssl,
            get_info=ALL
        )

        conn = Connection(server, user=user_dn, password=password, auto_bind=True)

        # Si llegamos aquí, autenticación exitosa
        conn.unbind()
        return True

    except Exception as e:
        st.error(f"Error en autenticación LDAP: {str(e)}")
        return False


def _validate_oauth_token(token: str, config: AuthConfig) -> Optional[Dict[str, Any]]:
    """
    Validar token OAuth y obtener información del usuario

    Args:
        token: Token OAuth a validar
        config: Configuración de autenticación

    Returns:
        Dict con info del usuario si válido, None en caso contrario
    """
    # Placeholder - implementación depende del provider
    # En producción, esto haría una llamada al endpoint de validación del provider
    st.warning("⚠️ OAuth aún no implementado completamente. Contactar al administrador.")
    return None


def _validate_cloudera_user(username: str, password: str, config: AuthConfig) -> bool:
    """
    Validar usuario contra Cloudera SSO/Kerberos

    Args:
        username: Username a validar
        password: Password del usuario
        config: Configuración de autenticación

    Returns:
        True si autenticación exitosa, False en caso contrario
    """
    if not config.cloudera_auth_endpoint:
        st.error("⚠️ Cloudera no configurado (CLOUDERA_AUTH_ENDPOINT)")
        return False

    try:
        import requests
    except ImportError:
        st.error("⚠️ Requests no instalado. Instalar: pip install requests")
        return False

    try:
        # Llamar al endpoint de autenticación de Cloudera
        response = requests.post(
            config.cloudera_auth_endpoint,
            json={'username': username, 'password': password},
            verify=config.cloudera_verify_ssl,
            timeout=10
        )

        if response.status_code == 200:
            return True
        else:
            st.error(f"Autenticación Cloudera falló: {response.status_code}")
            return False

    except Exception as e:
        st.error(f"Error en autenticación Cloudera: {str(e)}")
        return False


class Authenticator:
    """Gestor de autenticación con soporte para múltiples backends"""

    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()

    def is_authenticated(self) -> bool:
        """Verificar si el usuario actual está autenticado"""
        return st.session_state.get('authenticated', False)

    def get_current_user(self) -> Optional[str]:
        """Obtener username del usuario autenticado"""
        return st.session_state.get('username', None)

    def is_admin(self) -> bool:
        """Verificar si el usuario actual es administrador"""
        if not self.is_authenticated():
            return False

        username = self.get_current_user()
        return username in self.config.admin_users

    def authenticate_local(self) -> bool:
        """
        Autenticación local usando Windows username + whitelist

        Returns:
            True si autenticado, False si necesita login manual
        """
        # Dev mode - bypass authentication
        if self.config.dev_mode:
            st.session_state.authenticated = True
            st.session_state.username = 'dev_user'
            st.session_state.auth_backend = 'dev'
            return True

        # Auto-authenticate con Windows username
        current_user = _get_current_windows_user()

        if current_user and (not self.config.whitelist or current_user in self.config.whitelist):
            st.session_state.authenticated = True
            st.session_state.username = current_user
            st.session_state.auth_backend = 'local'
            return True

        # Si no auto-detecta, permitir login manual
        return False

    def render_login_form(self) -> bool:
        """
        Renderizar formulario de login según el backend configurado

        Returns:
            True si se autenticó exitosamente, False en caso contrario
        """
        st.markdown("""
        <div style="max-width: 450px; margin: 2rem auto; padding: 2rem;
                    background: #f8f9fa; border-radius: 10px;
                    border: 1px solid #E2E8F0; text-align: center;">
            <h3 style="color: #1E293B; margin-bottom: 0.5rem;
                       font-family: 'Fira Sans', sans-serif;">🔐 Acceso Restringido</h3>
            <p style="color: #666; font-size: 0.9rem; font-family: 'Fira Sans', sans-serif;">
                Ingresa tus credenciales corporativas para continuar.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            # Campos de login
            if self.config.backend in [AuthBackend.LOCAL, AuthBackend.LDAP]:
                username = st.text_input(
                    "Usuario / Email",
                    key="login_username",
                    placeholder="seXXXXX o seXXXXX@grupo.ypf.com"
                )

            if self.config.backend in [AuthBackend.LDAP, AuthBackend.CLOUDERA]:
                password = st.text_input(
                    "Contraseña",
                    type="password",
                    key="login_password"
                )

            if st.button("Iniciar sesión", use_container_width=True, key="login_btn"):
                # Normalizar username
                username_normalized = _normalize_email(username) if username else ""

                # Validar según backend
                authenticated = False

                if self.config.backend == AuthBackend.LOCAL:
                    # Validar contra whitelist
                    if not self.config.whitelist or username_normalized in self.config.whitelist:
                        authenticated = True
                    else:
                        st.error("❌ Tu usuario no tiene acceso a esta herramienta.")

                elif self.config.backend == AuthBackend.LDAP:
                    authenticated = _validate_ldap_user(username_normalized, password, self.config)
                    if not authenticated:
                        st.error("❌ Credenciales inválidas.")

                elif self.config.backend == AuthBackend.CLOUDERA:
                    authenticated = _validate_cloudera_user(username_normalized, password, self.config)
                    if not authenticated:
                        st.error("❌ Autenticación Cloudera falló.")

                elif self.config.backend == AuthBackend.OAUTH:
                    st.warning("⚠️ OAuth requiere configuración adicional. Contactar al administrador.")

                elif self.config.backend == AuthBackend.NONE:
                    authenticated = True
                    username_normalized = username_normalized or 'anonymous'

                # Si autenticación exitosa, guardar en session state
                if authenticated:
                    # Verificar whitelist adicional si está configurada
                    if self.config.whitelist and username_normalized not in self.config.whitelist:
                        st.error("❌ Tu usuario no está en la lista de acceso autorizado.")
                        return False

                    st.session_state.authenticated = True
                    st.session_state.username = username_normalized
                    st.session_state.auth_backend = self.config.backend.value
                    st.rerun()
                    return True

        return False

    def logout(self):
        """Cerrar sesión del usuario actual"""
        st.session_state.authenticated = False
        st.session_state.pop('username', None)
        st.session_state.pop('auth_backend', None)
        st.rerun()

    def require_auth(self, admin_only: bool = False) -> bool:
        """
        Requerir autenticación antes de continuar

        Args:
            admin_only: Si True, requiere que el usuario sea admin

        Returns:
            True si autenticado (y admin si requerido), False en caso contrario
        """
        # Intentar auto-autenticación local primero
        if not self.is_authenticated():
            if self.config.backend == AuthBackend.LOCAL:
                self.authenticate_local()

        # Si aún no está autenticado, mostrar formulario
        if not self.is_authenticated():
            self.render_login_form()
            return False

        # Si requiere admin, verificar
        if admin_only and not self.is_admin():
            st.error("❌ Esta sección requiere permisos de administrador.")
            return False

        return True

    def render_user_info(self):
        """Renderizar información del usuario y botón de logout"""
        if not self.is_authenticated():
            return

        username = self.get_current_user()
        backend = st.session_state.get('auth_backend', 'unknown')
        is_admin = self.is_admin()

        col1, col2, col3 = st.columns([4, 2, 1])

        with col2:
            admin_badge = " 👑" if is_admin else ""
            st.markdown(
                f"<p style='color: #666; font-size: 0.85rem; padding-top: 0.5rem; "
                f"text-align: right;'>Usuario: <strong>{username}</strong>{admin_badge}</p>",
                unsafe_allow_html=True
            )

        with col3:
            if st.button("Cerrar sesión", key="logout_btn"):
                self.logout()
