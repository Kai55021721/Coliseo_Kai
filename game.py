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
        self.eliminated_this_round = []
        self.first_round = True
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            print(f"Error al configurar Gemini: {e}")
            self.model = None

    def load_players(self, player_rows):
        """Carga los jugadores desde la base de datos al inicio del juego."""
        self.active_players = []
        for row in player_rows:
            # Tupla de la DB: (user_id, user_name, character_name, specialty, absurd_skill, is_champion, is_approved)
            player = Player(row[0], row[1], row[2], row[3], row[4], row[5])
            self.active_players.append(player)
        random.shuffle(self.active_players)
        self.is_running = True
        self.first_round = True

    def start_new_round(self):
        """Prepara el texto del panel de estado para una nueva ronda."""
        self.eliminated_this_round = []
        all_players_this_round = sorted(self.active_players, key=lambda p: p.character_name)
        
        header = f"--- **RONDA CON {len(all_players_this_round)} GUERREROS** ---\n\n"
        player_lines = []
        for player in all_players_this_round:
            title = "👑" if player.is_champion else "🔥"
            player_lines.append(f"• {title} {player.character_name} ({player.mention()})")
        
        return header + "\n".join(player_lines)

    def update_status_text(self, original_text, loser):
        """Actualiza el texto del panel de estado tachando al perdedor."""
        self.eliminated_this_round.append(loser)
        
        lines = original_text.split('\n')
        header = lines[0]
        player_lines = lines[2:] # Omitir header y línea en blanco

        new_player_lines = []
        for line in player_lines:
            is_eliminated = any(eliminated.character_name in line for eliminated in self.eliminated_this_round)
            if is_eliminated and not line.startswith("• ~"):
                new_player_lines.append(f"• ~{line[2:]}~ (Eliminado)")
            else:
                new_player_lines.append(line)
        
        return f"{header}\n\n" + "\n".join(new_player_lines)

    def play_next_round_pairings(self):
        """Genera los emparejamientos y supervivientes para la ronda."""
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
        """Genera la narración de un combate y determina ganador/perdedor."""
        if not self.model:
            winner, loser = random.choice([(player1, player2), (player2, player1)])
            fallback = f"⚡ ¡Una energía divina ciega la arena! Cuando la luz se disipa, **{winner.character_name}** sigue en pie. ¡Ha ganado!"
            return fallback, winner, loser

        trials = ["el Juicio del Laberinto de Espejos", "la Carga del Minotauro Espectral", "el Duelo Celestial en el Puente Bifrost", "la Furia del Volcán de Sombras"]
        trial = random.choice(trials)

        prompt = (f"Actúa como narrador épico del Coliseo de Kai. Narra un combate a muerte en un párrafo corto y conciso (máximo 4 frases). La prueba es: '{trial}'.\n"
                  f"Combatientes:\n- '{player1.character_name}' (@{player1.user_name}), dominio '{player1.specialty}', habilidad extraña '{player1.absurd_skill}'.\n"
                  f"- '{player2.character_name}' (@{player2.user_name}), dominio '{player2.specialty}', habilidad extraña '{player2.absurd_skill}'.\n\n"
                  f"Incorpora de forma humorística cómo sus inútiles habilidades afectan el combate. La narración debe ser rápida y directa. Concluye declarando inequívocamente al ganador.")
        
        try:
            response = self.model.generate_content(prompt)
            text_response = response.text
            # Lógica robusta para determinar ganador
            if player1.character_name.lower() in text_response and player2.character_name.lower() not in text_response:
                winner, loser = player1, player2
            elif player2.character_name.lower() in text_response and player1.character_name.lower() not in text_response:
                winner, loser = player2, player1
            else: # Si ambos son mencionados, o ninguno, decidir al azar
                winner, loser = random.choice([(player1, player2), (player2, player1)])
            
            return text_response, winner, loser

        except Exception as e:
            print(f"Error en la llamada a la API de Gemini: {e}")
            winner, loser = random.choice([(player1, player2), (player2, player1)])
            fallback = f"⚡ ¡Una energía divina ciega la arena! Cuando la luz se disipa, **{winner.character_name}** sigue en pie. ¡Ha ganado!"
            return fallback, winner, loser

    def end_game(self):
        """Resetea el estado del juego."""
        self.is_running = False
        self.active_players = []