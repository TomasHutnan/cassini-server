"""Password hashing and verification utilities."""

import secrets
from passlib.context import CryptContext

# Configure bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> tuple[str, str]:
    """
    Hash a password with a random salt using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    # Generate a random salt
    salt = secrets.token_hex(32)
    
    # Combine password with salt and hash
    salted_password = password + salt
    hashed = pwd_context.hash(salted_password)
    
    return hashed, salt


def verify_password(plain_password: str, salt: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        salt: Salt used when creating the hash
        hashed_password: The hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    salted_password = plain_password + salt
    return pwd_context.verify(salted_password, hashed_password)
