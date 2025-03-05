import sqlite3

def get_db_connection():
    conn = sqlite3.connect(r'W:\.shortcut-targets-by-id\1-1D2HTD7zuv4Z2Dem_VT9aK7ymJ-nItv\3 SA\Consigo Cred\Banco de Dados\DB_Consigocred.db')
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se a tabela existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        # Verificar se as colunas recipient e answered existem
        cursor.execute("PRAGMA table_info(messages)")
        columns = {col[1] for col in cursor.fetchall()}
        
        # Adicionar colunas faltantes se necessário
        if 'recipient' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN recipient TEXT")
        
        if 'answered' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN answered INTEGER DEFAULT 0")
    else:
        # Criar tabela com todas as colunas necessárias
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whatsapp_id TEXT UNIQUE NOT NULL,
            sender TEXT NOT NULL,
            recipient TEXT,
            message TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            status TEXT DEFAULT 'received',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            conversation_status TEXT DEFAULT 'pending',
            answered INTEGER DEFAULT 0
        )
        ''')
    
    conn.commit()
    conn.close()
    print("Banco de dados e tabela atualizados com sucesso!")

if __name__ == '__main__':
    create_tables()
