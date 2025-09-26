# game.py
import random
import google.generativeai as genai

ABSURD_SKILLS = [
    "Narcolepsia repentina", "Atraer mariposas en momentos inoportunos", "Bailar polka sin control",
    "Gritos de cabra incontrolables", "Llorar purpurina bajo presión", "Todo lo que tocas huele a ajo",
    "Hablar solo con preguntas", "Atraer palomas agresivas", "Un hipo increíblemente sonoro",
    "Narrar tus propias acciones en tercera persona", "Tus rodillas se doblan hacia atrás",
    "Incapacidad para susurrar", "Sudoración de color azul neón"
]

class Player:
    def __init__(self, user_id, user_name, character_name, specialty, absurd_skill, is_champion):
        self.user_id = user_id
        self.user_name = user_name
        self.character_name = character_name
        self.specialty = specialty
        self.is_champion = is_champion
        self.absurd_skill = absurd_skill

    def mention(self):
        return f"@{self.user_name}" if self.user_name else self.character_name

class Game:
    def __init__(self, api_key):
        self.is_running = False
        self.active_players = []
        self.first_round = True
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            print(f"Error al configurar Gemini: {e}")
            self.model = None

    def load_players(self, player_rows):
        """Carga los jugadores desde la base de datos."""
        self.active_players = []
        for row in player_rows:
            # (user_id, user_name, character_name, specialty, absurd_skill, is_champion, is_approved)
            player = Player(row[0], row[1], row[2], row[3], row[4], row[5])
            self.active_players.append(player)
        random.shuffle(self.active_players)
        self.is_running = True
        self.first_round = True

    def get_player_list_text(self, eliminated_player=None):
        """Genera el texto para el panel de estado."""
        if not self.active_players:
            return "No quedan guerreros en la arena."
        
        # Si se pasa un jugador eliminado, lo eliminamos de la lista activa
        if eliminated_player:
            self.active_players = [p for p in self.active_players if p.user_id != eliminated_player.user_id]
        
        message = "✨ **Guerreros en la Arena de Kai** ✨\n\n"
        for player in self.active_players:
            title = "👑 Campeón" if player.is_champion else "🔥 Aspirante"
            message += f"• {title} **{player.character_name}** (@{player.user_name})\n"
        return message

    def play_next_round(self):
        if not self.is_running or len(self.active_players) <= 1:
            return [], []

        pairings = []
        survivors = []
        round_players = self.active_players[:]
        random.shuffle(round_players)

        if self.first_round:
            self.first_round = False
            champions = [p for p in round_players if p.is_champion]
            aspirants = [p for p in round_players if not p.is_champion]
            survivors.extend(champions)
            round_players = aspirants

        if len(round_players) % 2 != 0:
            survivors.append(round_players.pop())

        while round_players:
            pairings.append((round_players.pop(), round_players.pop()))
            
        return pairings, survivors

    def simulate_combat(self, player1, player2):
        if not self.model:
            return "La voz de Kai se ha silenciado. El combate no puede ser narrado.", None, None

        trials = [
            "el Juicio del Laberinto de Espejos", "la Carga del Minotauro Espectral",
            "el Duelo Celestial en el Puente Bifrost", "la Furia del Volcán de Sombras"
        ]
        trial = random.choice(trials)

        prompt = (
            f"Actúa como un narrador épico del Coliseo del Templo de Kai. "
            f"Narra un combate a muerte en un párrafo corto y conciso (máximo 4 frases). La prueba es: '{trial}'.\n"
            f"Los combatientes son:\n"
            f"- '{player1.character_name}' (@{player1.user_name}), dominio '{player1.specialty}', habilidad extraña '{player1.absurd_skill}'.\n"
            f"- '{player2.character_name}' (@{player2.user_name}), dominio '{player2.specialty}', habilidad extraña '{player2.absurd_skill}'.\n\n"
            f"Incorpora de manera humorística cómo sus inútiles habilidades podrían afectar el combate. "
            f"La narración debe ser rápida y directa. Concluye declarando inequívocamente al ganador."
        )
        
        try:
            response = self.model.generate_content(prompt)
            # Determinar ganador (lógica simplificada para robustez)
            winner, loser = (player1, player2) if player1.character_name in response.text else (player2, player1)
            return response.text, winner, loser
        except Exception as e:
            print(f"Error en la llamada a la API de Gemini: {e}")
            winner, loser = random.choice([(player1, player2), (player2, player1)])
            fallback = f"⚡ Una energía divina ciega la arena! Cuando la luz se disipa, **{winner.character_name}** sigue en pie, mientras que **{loser.character_name}** ha caído. ¡La victoria es para **{winner.character_name}**!"
            return fallback, winner, loser

    def end_game(self):
        self.is_running = False
        self.active_players = []