import jwt
import time

# Caminho para sua chave privada RSA
PRIVATE_KEY_PATH = "private_key.pem"

# Issuer que você definiu no IdentityPropagationTrust
ISSUER = "my-jwt-issuer"

# Audience deve ser o domínio do seu IDCS (geralmente igual ao seu issuer URL ou IDCS URL)
AUDIENCE = "https://idcs-c3fbb3ae829b4af0a98995e5f1549f09.identity.oraclecloud.com"

# Subject (usuário ou client_id dependendo da configuração do trust)
SUBJECT = "usuario_test"  # ou o OCID se o mapeamento for com OCID

# Claim opcional se você configurou `clientClaimName = client_id`
CLIENT_ID = "ocid1.oauth2client.oc1..aaaaaaaaxxxxyyyyzzz"

# Tempo atual em segundos desde epoch
now = int(time.time())

# Monta o payload
payload = {
    "iss": ISSUER,
    "sub": SUBJECT,
    "aud": AUDIENCE,
    "exp": now + 300,  # expira em 5 minutos
    "iat": now,
    "client_id": CLIENT_ID
}

# Carrega a chave privada
with open(PRIVATE_KEY_PATH, "r") as f:
    private_key = f.read()

# Gera o JWT assinado
encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

# Exibe
print("JWT:")
print(encoded_jwt)
