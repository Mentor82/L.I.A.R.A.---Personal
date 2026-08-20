from passlib.context import CryptContext

# Argon2id-Konfiguration wie im Backend
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4
)

hashed = "$argon2id$v=19$m=65536,t=3,p=4$2TundK6VUgpBSInx3ntv7Q$2rMwkjHdecYBRv9SrkOixdMnAK1YvDd3Ozwk/469lLQ"
plain = "liaras_own"

if pwd_context.verify(plain, hashed):
    print("Passwort stimmt!")
else:
    print("Passwort falsch!")
