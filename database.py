# database.py
import sqlite3

DB_NAME = "coliseum.db"

def initialize_db():
    """Crea la tabla de jugadores si no existe."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            character_name TEXT,
            specialty TEXT,
            absurd_skill TEXT,
            is_champion BOOLEAN,
            is_approved BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# <--- CAMBIO: La función ya no necesita saber si es campeón al añadir la solicitud.
def add_player_submission(user_id, user_name, character_name, specialty, absurd_skill):
    """Añade una nueva solicitud de jugador a la base de datos, pendiente de aprobación."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO players (user_id, user_name, character_name, specialty, absurd_skill, is_approved)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
            character_name=excluded.character_name,
            specialty=excluded.specialty,
            absurd_skill=excluded.absurd_skill,
            is_approved=0
        ''', (user_id, user_name, character_name, specialty, absurd_skill))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error en la base de datos al añadir solicitud: {e}")
    finally:
        conn.close()

# <--- CAMBIO: Ahora la función de aprobar acepta el estatus de campeón.
def approve_player(user_id, is_champion):
    """Marca a un jugador como aprobado y asigna su estatus."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE players SET is_approved = 1, is_champion = ? WHERE user_id = ?', (is_champion, user_id))
    conn.commit()
    conn.close()

def reject_player(user_id):
    """Elimina una solicitud de jugador de la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM players WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_player_info(user_id):
    """Obtiene la información de un jugador específico."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT character_name, specialty FROM players WHERE user_id = ?', (user_id,))
    player = cursor.fetchone()
    conn.close()
    return player

# ... (El resto de funciones de database.py no cambian)
def get_approved_players():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE is_approved = 1')
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_all_players():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM players')
    conn.commit()
    conn.close()

def player_exists(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM players WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists