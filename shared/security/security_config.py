"""
Security configuration for the event-driven architecture.
Provides TLS mutual authentication, RBAC, and security utilities.
"""

import os
import ssl
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
from functools import wraps
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption


class TLSConfig:
    """TLS configuration for secure communication."""
    
    def __init__(
        self,
        cert_dir: str = None,
        ca_cert_path: str = None,
        server_cert_path: str = None,
        server_key_path: str = None,
        client_cert_path: str = None,
        client_key_path: str = None,
        verify_mode: str = "CERT_REQUIRED"
    ):
        self.cert_dir = Path(cert_dir or os.getenv('CERT_DIR', './certs'))
        self.ca_cert_path = ca_cert_path or os.getenv('CA_CERT_PATH')
        self.server_cert_path = server_cert_path or os.getenv('SERVER_CERT_PATH')
        self.server_key_path = server_key_path or os.getenv('SERVER_KEY_PATH')
        self.client_cert_path = client_cert_path or os.getenv('CLIENT_CERT_PATH')
        self.client_key_path = client_key_path or os.getenv('CLIENT_KEY_PATH')
        
        # SSL verification mode
        verify_modes = {
            "CERT_NONE": ssl.CERT_NONE,
            "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
            "CERT_REQUIRED": ssl.CERT_REQUIRED
        }
        self.verify_mode = verify_modes.get(verify_mode, ssl.CERT_REQUIRED)
        
        self.logger = logging.getLogger(__name__)
    
    def create_ssl_context(self, context_type: str = "server") -> ssl.SSLContext:
        """Create SSL context for server or client."""
        if context_type == "server":
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.verify_mode = self.verify_mode
            
            # Load server certificate and key
            if self.server_cert_path and self.server_key_path:
                context.load_cert_chain(self.server_cert_path, self.server_key_path)
            
            # Load CA certificate for client verification
            if self.ca_cert_path:
                context.load_verify_locations(self.ca_cert_path)
                
        else:  # client
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.verify_mode = self.verify_mode
            
            # Load client certificate and key for mutual auth
            if self.client_cert_path and self.client_key_path:
                context.load_cert_chain(self.client_cert_path, self.client_key_path)
            
            # Load CA certificate for server verification
            if self.ca_cert_path:
                context.load_verify_locations(self.ca_cert_path)
        
        # Security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        return context
    
    def generate_self_signed_certs(
        self,
        common_name: str = "localhost",
        organization: str = "Event-Driven PoC",
        validity_days: int = 365
    ) -> None:
        """Generate self-signed certificates for development."""
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate CA private key
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Generate CA certificate
        ca_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{organization} CA"),
        ])
        
        ca_cert = x509.CertificateBuilder().subject_name(
            ca_name
        ).issuer_name(
            ca_name
        ).public_key(
            ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=validity_days)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(ca_key, hashes.SHA256())
        
        # Save CA certificate and key
        ca_cert_path = self.cert_dir / "ca.crt"
        ca_key_path = self.cert_dir / "ca.key"
        
        with open(ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(Encoding.PEM))
        
        with open(ca_key_path, "wb") as f:
            f.write(ca_key.private_bytes(
                Encoding.PEM,
                PrivateFormat.PKCS8,
                NoEncryption()
            ))
        
        # Generate server certificate
        self._generate_cert(ca_cert, ca_key, common_name, "server", validity_days)
        
        # Generate client certificate
        self._generate_cert(ca_cert, ca_key, "client", "client", validity_days)
        
        self.logger.info(f"Generated self-signed certificates in {self.cert_dir}")
    
    def _generate_cert(
        self,
        ca_cert: x509.Certificate,
        ca_key: rsa.RSAPrivateKey,
        common_name: str,
        cert_type: str,
        validity_days: int
    ) -> None:
        """Generate a certificate signed by the CA."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Create certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Event-Driven PoC"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        cert_builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=validity_days)
        )
        
        # Add extensions based on certificate type
        if cert_type == "server":
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.IPAddress("127.0.0.1"),
                ]),
                critical=False,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                ]),
                critical=True,
            )
        else:  # client
            cert_builder = cert_builder.add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=True,
            )
        
        cert = cert_builder.sign(ca_key, hashes.SHA256())
        
        # Save certificate and key
        cert_path = self.cert_dir / f"{cert_type}.crt"
        key_path = self.cert_dir / f"{cert_type}.key"
        
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(Encoding.PEM))
        
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                Encoding.PEM,
                PrivateFormat.PKCS8,
                NoEncryption()
            ))


class RBACConfig:
    """Role-Based Access Control configuration."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.getenv('RBAC_CONFIG_PATH', './rbac_config.json')
        self.roles: Dict[str, Dict[str, Any]] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.permissions: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load RBAC configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.roles = config.get('roles', {})
                    self.users = config.get('users', {})
                    self.permissions = config.get('permissions', {})
            else:
                self._create_default_config()
        except Exception as e:
            self.logger.error(f"Failed to load RBAC config: {e}")
            self._create_default_config()
    
    def _create_default_config(self) -> None:
        """Create default RBAC configuration."""
        self.roles = {
            "admin": {
                "description": "Full system access",
                "permissions": ["*"]
            },
            "service": {
                "description": "Service-to-service communication",
                "permissions": [
                    "events.publish",
                    "events.consume",
                    "api.call",
                    "metrics.read"
                ]
            },
            "readonly": {
                "description": "Read-only access",
                "permissions": [
                    "events.read",
                    "metrics.read",
                    "logs.read"
                ]
            }
        }
        
        self.users = {
            "api-service": {
                "role": "service",
                "description": "API service account"
            },
            "mailer-service": {
                "role": "service",
                "description": "Mailer service account"
            },
            "workflow-agent": {
                "role": "service",
                "description": "Workflow agent service account"
            },
            "admin": {
                "role": "admin",
                "description": "System administrator"
            }
        }
        
        self.permissions = {
            "events.publish": ["kafka:write:events.*"],
            "events.consume": ["kafka:read:events.*"],
            "events.read": ["kafka:read:events.*"],
            "api.call": ["http:*:api.*"],
            "metrics.read": ["http:get:metrics.*"],
            "logs.read": ["http:get:logs.*"]
        }
        
        self._save_config()
    
    def _save_config(self) -> None:
        """Save RBAC configuration to file."""
        try:
            config = {
                "roles": self.roles,
                "users": self.users,
                "permissions": self.permissions
            }
            
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save RBAC config: {e}")
    
    def check_permission(self, user: str, resource: str, action: str) -> bool:
        """Check if user has permission for resource and action."""
        if user not in self.users:
            return False
        
        user_role = self.users[user].get('role')
        if not user_role or user_role not in self.roles:
            return False
        
        role_permissions = self.roles[user_role].get('permissions', [])
        
        # Admin has all permissions
        if "*" in role_permissions:
            return True
        
        # Check specific permissions
        required_permission = f"{resource}.{action}"
        if required_permission in role_permissions:
            return True
        
        # Check wildcard permissions
        for permission in role_permissions:
            if permission.endswith('*'):
                prefix = permission[:-1]
                if required_permission.startswith(prefix):
                    return True
        
        return False
    
    def get_user_permissions(self, user: str) -> List[str]:
        """Get all permissions for a user."""
        if user not in self.users:
            return []
        
        user_role = self.users[user].get('role')
        if not user_role or user_role not in self.roles:
            return []
        
        return self.roles[user_role].get('permissions', [])
    
    def add_user(self, username: str, role: str, description: str = "") -> bool:
        """Add a new user."""
        if role not in self.roles:
            return False
        
        self.users[username] = {
            "role": role,
            "description": description
        }
        self._save_config()
        return True
    
    def add_role(self, role_name: str, permissions: List[str], description: str = "") -> None:
        """Add a new role."""
        self.roles[role_name] = {
            "description": description,
            "permissions": permissions
        }
        self._save_config()


class SecurityMiddleware:
    """Security middleware for authentication and authorization."""
    
    def __init__(self, rbac_config: RBACConfig):
        self.rbac = rbac_config
        self.logger = logging.getLogger(__name__)
    
    def require_permission(self, resource: str, action: str):
        """Decorator to require specific permission."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user from request context (implementation depends on framework)
                user = self._get_current_user()
                
                if not user:
                    raise PermissionError("Authentication required")
                
                if not self.rbac.check_permission(user, resource, action):
                    raise PermissionError(f"Permission denied: {resource}.{action}")
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def _get_current_user(self) -> Optional[str]:
        """Get current user from request context."""
        # This would be implemented based on the authentication mechanism
        # For example, extracting from JWT token, session, or certificate
        return os.getenv('CURRENT_USER', 'anonymous')


class APIKeyManager:
    """Manager for API key authentication."""
    
    def __init__(self, keys_file: str = None):
        self.keys_file = keys_file or os.getenv('API_KEYS_FILE', './api_keys.json')
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        self._load_keys()
    
    def _load_keys(self) -> None:
        """Load API keys from file."""
        try:
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r') as f:
                    self.api_keys = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
    
    def _save_keys(self) -> None:
        """Save API keys to file."""
        try:
            os.makedirs(os.path.dirname(self.keys_file), exist_ok=True)
            with open(self.keys_file, 'w') as f:
                json.dump(self.api_keys, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save API keys: {e}")
    
    def generate_api_key(self, user: str, description: str = "") -> str:
        """Generate a new API key for a user."""
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        self.api_keys[key_hash] = {
            "user": user,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "active": True
        }
        
        self._save_keys()
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[str]:
        """Validate API key and return associated user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self.api_keys:
            key_info = self.api_keys[key_hash]
            if key_info.get('active', False):
                # Update last used timestamp
                key_info['last_used'] = datetime.now(timezone.utc).isoformat()
                self._save_keys()
                return key_info['user']
        
        return None
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self.api_keys:
            self.api_keys[key_hash]['active'] = False
            self._save_keys()
            return True
        
        return False


# Utility functions
def setup_security(
    cert_dir: str = None,
    rbac_config_path: str = None,
    generate_certs: bool = False
) -> Tuple[TLSConfig, RBACConfig, APIKeyManager]:
    """Set up security components."""
    # TLS configuration
    tls_config = TLSConfig(cert_dir=cert_dir)
    
    if generate_certs:
        tls_config.generate_self_signed_certs()
    
    # RBAC configuration
    rbac_config = RBACConfig(config_path=rbac_config_path)
    
    # API key manager
    api_key_manager = APIKeyManager()
    
    return tls_config, rbac_config, api_key_manager


def create_security_headers() -> Dict[str, str]:
    """Create security headers for HTTP responses."""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }

