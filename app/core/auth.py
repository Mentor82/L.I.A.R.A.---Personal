from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import hashlib
import base64

security = HTTPBasic()
HTPASSWD_PATH = '/opt/liara/.htpasswd'

def verify_apr1_md5(password: str, hash_str: str) -> bool:
    """
    Verifiziere Apache APR1 MD5 Hash.
    Format: $apr1$salt$hash
    """
    if not hash_str.startswith('$apr1$'):
        return False
    
    parts = hash_str.split('$')
    if len(parts) < 4:
        return False
    
    salt = parts[2]
    
    # APR1 MD5 Algorithm (simplified - für production besser library nutzen)
    # Für jetzt: einfach die passlib ohne bcrypt dependency nutzen
    from passlib.hash import apr_md5_crypt
    return apr_md5_crypt.verify(password, hash_str)


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verifiziere HTTP Basic Auth Credentials gegen .htpasswd.
    
    Verwendet Apache htpasswd Format (apr1 MD5).
    """
    if not os.path.exists(HTPASSWD_PATH):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system not configured"
        )
    
    try:
        with open(HTPASSWD_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                
                username, password_hash = line.split(':', 1)
                
                if username == credentials.username:
                    if verify_apr1_md5(credentials.password, password_hash):
                        return username
                    else:
                        break
        
        # User nicht gefunden oder falsches Passwort
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic realm='Liara Access'"},
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )
