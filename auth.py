# auth.py

import os
import hashlib
import sqlite3
import hmac
from datetime import datetime

DB_PATH = os.getenv("USERS_DB_PATH", "users.db")
ITERATIONS = 600000

def get_db_connection():
    """Retorna uma conexão aberta com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """
    Gera um salt aleatório se não fornecido e faz o hash da senha usando PBKDF2 com SHA-256.
    Retorna uma tupla (password_hash_hex, salt_hex).
    """
    if salt is None:
        salt = os.urandom(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        ITERATIONS
    )
    return pwd_hash.hex(), salt.hex()

def verify_password(password: str, password_hash_hex: str, salt_hex: str) -> bool:
    """
    Verifica se a senha fornecida corresponde ao hash armazenado usando comparação em tempo constante.
    """
    try:
        salt = bytes.fromhex(salt_hex)
        pwd_hash = bytes.fromhex(password_hash_hex)
        input_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            ITERATIONS
        )
        return hmac.compare_digest(input_hash, pwd_hash)
    except Exception:
        return False

def init_db():
    """
    Cria a tabela de usuários se ela não existir e cria
    o superusuário padrão 'admin' com a senha 'admin123' se a tabela estiver vazia.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT 0,
            needs_password_change BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Migração segura para bancos existentes que não possuem a coluna 'needs_password_change'
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN needs_password_change BOOLEAN NOT NULL DEFAULT 1")
        conn.commit()
    except sqlite3.OperationalError:
        # A coluna já existe
        pass
    
    # Verifica se já existe um usuário administrador padrão
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = 'admin'")
    row = cursor.fetchone()
    if row['count'] == 0:
        # Cria o superusuário administrador padrão com senha 'admin123' e marca que ele precisa trocar de senha
        hash_hex, salt_hex = hash_password("admin123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, is_admin, needs_password_change) VALUES (?, ?, ?, 1, 1)",
            ("admin", hash_hex, salt_hex)
        )
        conn.commit()
    conn.close()

def authenticate_user(username: str, password: str) -> dict | None:
    """
    Autentica o usuário pelo nome de usuário e senha.
    Retorna um dicionário com os dados públicos do usuário se autenticado, caso contrário None.
    """
    if not username or not password:
        return None
        
    username = username.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, salt, is_admin, needs_password_change FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        if verify_password(password, row['password_hash'], row['salt']):
            return {
                'id': row['id'],
                'username': row['username'],
                'is_admin': bool(row['is_admin']),
                'needs_password_change': bool(row['needs_password_change'])
            }
    return None

def create_user(username: str, is_admin: bool = False) -> tuple[bool, str]:
    """
    Cadastra um novo usuário no sistema com a senha padrão '123456'
    e marca como obrigatória a troca no primeiro acesso.
    """
    if not username:
        return False, "O nome de usuário é obrigatório."
    
    username = username.strip()
    if len(username) < 3:
        return False, "O nome de usuário deve ter pelo menos 3 caracteres."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Senha padrão no primeiro acesso é sempre "123456"
        hash_hex, salt_hex = hash_password("123456")
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, is_admin, needs_password_change) VALUES (?, ?, ?, ?, 1)",
            (username, hash_hex, salt_hex, 1 if is_admin else 0)
        )
        conn.commit()
        return True, "Usuário criado com sucesso! Senha temporária: 123456"
    except sqlite3.IntegrityError:
        return False, "Este nome de usuário já está em uso."
    except Exception as e:
        return False, f"Erro ao criar usuário: {str(e)}"
    finally:
        conn.close()

def update_user(user_id: int, username: str, is_admin: bool) -> tuple[bool, str]:
    """
    Atualiza o nome de usuário e o cargo (admin ou usuário) de um registro.
    Previne que o último administrador perca suas credenciais.
    """
    if not username:
        return False, "O nome de usuário é obrigatório."
    
    username = username.strip()
    if len(username) < 3:
        return False, "O nome de usuário deve ter pelo menos 3 caracteres."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Regra de negócio: não podemos remover privilégios de admin se for o único admin ativo
        cursor.execute("SELECT username, is_admin FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return False, "Usuário não encontrado."
            
        if user['is_admin'] and not is_admin:
            # Conta se existem outros administradores
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = 1 AND id != ?", (user_id,))
            other_admin_count = cursor.fetchone()['count']
            if other_admin_count == 0:
                return False, "Não é permitido remover o privilégio de administrador do único administrador restante."
        
        cursor.execute(
            "UPDATE users SET username = ?, is_admin = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (username, 1 if is_admin else 0, user_id)
        )
        conn.commit()
        return True, "Usuário atualizado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Este nome de usuário já está em uso."
    except Exception as e:
        return False, f"Erro ao atualizar usuário: {str(e)}"
    finally:
        conn.close()

def reset_password(user_id: int, new_password: str) -> tuple[bool, str]:
    """
    Redefine a senha de um usuário gerando um novo hash e salt único.
    Força a obrigação de trocar a senha no próximo acesso.
    """
    if len(new_password) < 4:
        return False, "A nova senha deve ter pelo menos 4 caracteres."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hash_hex, salt_hex = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = ?, salt = ?, needs_password_change = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (hash_hex, salt_hex, user_id)
        )
        conn.commit()
        return True, "Senha redefinida com sucesso! O usuário deverá alterá-la no próximo acesso."
    except Exception as e:
        return False, f"Erro ao redefinir senha: {str(e)}"
    finally:
        conn.close()

def change_password_on_first_login(user_id: int, new_password: str) -> tuple[bool, str]:
    """
    Redefine a senha no primeiro acesso/senha forçada.
    Salva o novo hash, atualiza o salt e marca a flag 'needs_password_change' como 0 (False).
    """
    if len(new_password) < 6:
        return False, "A nova senha deve ter pelo menos 6 caracteres."
    if new_password == "123456":
        return False, "A senha não pode ser a senha padrão '123456'. Defina uma senha mais segura."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hash_hex, salt_hex = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = ?, salt = ?, needs_password_change = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (hash_hex, salt_hex, user_id)
        )
        conn.commit()
        return True, "Senha atualizada com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar senha: {str(e)}"
    finally:
        conn.close()

def delete_user(user_id: int, current_admin_username: str) -> tuple[bool, str]:
    """
    Exclui um usuário do sistema de forma segura.
    Bloqueia exclusão própria ou do único administrador remanescente do sistema.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username, is_admin FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return False, "Usuário não encontrado."
            
        if user['username'] == current_admin_username:
            return False, "Não é permitido excluir seu próprio usuário logado."
            
        if user['is_admin']:
            # Verifica se é o último administrador
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = 1 AND id != ?", (user_id,))
            other_admin_count = cursor.fetchone()['count']
            if other_admin_count == 0:
                return False, "Não é permitido excluir o único administrador restante."
                
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True, "Usuário excluído com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir usuário: {str(e)}"
    finally:
        conn.close()

def list_users() -> list[dict]:
    """
    Retorna uma lista contendo todos os usuários cadastrados e seus metadados.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, is_admin, needs_password_change, created_at, updated_at FROM users ORDER BY username ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
