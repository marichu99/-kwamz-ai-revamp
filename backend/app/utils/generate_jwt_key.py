import secrets

def generate_jwt_secret(length=64):
    return secrets.token_urlsafe(length)

def update_env_file(env_path=".env", key="JWT_SECRET_KEY"):
    secret = generate_jwt_secret()

    try:
        with open(env_path, "r") as file:
            lines = file.readlines()
    except FileNotFoundError:
        lines = []

    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={secret}\n"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={secret}\n")

    with open(env_path, "w") as file:
        file.writelines(lines)

    print(f"{key} updated in {env_path}")

if __name__ == "__main__":
    update_env_file()
