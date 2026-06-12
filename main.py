#!/usr/bin/env python3
import sys
import time
from connection import wait_for_client, connect_to_server

# Wartości figur dla heurystyki (podstawa oceny pozycji)
PIECE_VALUES = {
    'P': 100,   # Pion
    'N': 320,   # Skoczek
    'B': 330,   # Goniec
    'R': 500,   # Wieża
    'Q': 900,   # Hetman
    'K': 20000  # Król
}

class ChessEngine:
    def __init__(self, color):
        self.color = color  # "white" (Serwer) lub "black" (Klient)
        self.board = self.setup_initial_board()
        self.files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    def setup_initial_board(self):
        """Inicjalizacja planszy jako słownika, gdzie klucz to pole (np. 'e2'),
        a wartość to para (kolor, figura), np. ('white', 'P').
        """
        board = {}
        back_row = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        
        for i, f in enumerate(files):
            board[f"{f}1"] = ("white", back_row[i])
            board[f"{f}2"] = ("white", "P")
            board[f"{f}7"] = ("black", "P")
            board[f"{f}8"] = ("black", back_row[i])
        return board

    def apply_move(self, move_frame):
        """Aktualizuje lokalny stan planszy na podstawie otrzymanej ramki ruchu."""
        start_pos = move_frame["from"]
        end_pos = move_frame["to"]
        
        if start_pos not in self.board:
            return

        side, piece = self.board[start_pos]
        
        # Obsługa promocji pionka
        if "promotion" in move_frame:
            piece = move_frame["promotion"]

        # Wykonanie przesunięcia i usunięcie starej pozycji
        self.board[end_pos] = (side, piece)
        del self.board[start_pos]

        # Logika roszady (jeśli król rusza się o 2 pola, przesuwamy też wieżę)
        if piece == 'K':
            if start_pos == 'e1':
                if end_pos == 'g1' and 'h1' in self.board:
                    self.board['f1'] = self.board['h1']
                    del self.board['h1']
                elif end_pos == 'c1' and 'a1' in self.board:
                    self.board['d1'] = self.board['a1']
                    del self.board['a1']
            elif start_pos == 'e8':
                if end_pos == 'g8' and 'h8' in self.board:
                    self.board['f8'] = self.board['h8']
                    del self.board['h8']
                elif end_pos == 'c8' and 'a8' in self.board:
                    self.board['d8'] = self.board['a8']
                    del self.board['a8']

    def evaluate_board(self):
        """Funkcja oceniająca (Heurystyka) oparta o materiał i kontrolę centrum."""
        score = 0
        for pos, (side, piece) in self.board.items():
            val = PIECE_VALUES.get(piece, 0)
            
            # Bonus za zajęcie/kontrolę centrum (d4, d5, e4, e5)
            if pos in ['d4', 'd5', 'e4', 'e5']:
                val += 15
                
            if side == self.color:
                score += val
            else:
                score -= val
        return score

    def generate_all_legal_moves(self, side):
        """Generuje listę wszystkich legalnych ruchów dla danej strony."""
        moves = []
        for pos, (p_side, piece) in list(self.board.items()):
            if p_side != side:
                continue
                
            if piece == 'P':
                moves.extend(self.get_pawn_moves(pos, side))
            elif piece == 'N':
                moves.extend(self.get_knight_moves(pos, side))
            elif piece == 'B':
                moves.extend(self.get_sliding_moves(pos, side, piece, [(1,1), (1,-1), (-1,1), (-1,-1)]))
            elif piece == 'R':
                moves.extend(self.get_sliding_moves(pos, side, piece, [(0,1), (0,-1), (1,0), (-1,0)]))
            elif piece == 'Q':
                moves.extend(self.get_sliding_moves(pos, side, piece, [(1,1), (1,-1), (-1,1), (-1,-1), (0,1), (0,-1), (1,0), (-1,0)]))
            elif piece == 'K':
                moves.extend(self.get_king_moves(pos, side))
        return moves

    def get_pawn_moves(self, pos, side):
        """Zasady ruchu dla Piona (P)."""
        moves = []
        f_idx = self.files.index(pos[0])
        rank = int(pos[1])
        
        # Kierunek ruchu: Białe idą w górę (+1), Czarne w dół (-1)
        direction = 1 if side == "white" else -1
        start_rank = 2 if side == "white" else 7
        promo_rank = 8 if side == "white" else 1

        # 1. Ruch o jedno pole w przód
        next_rank = rank + direction
        if 1 <= next_rank <= 8:
            one_square = f"{pos[0]}{next_rank}"
            if one_square not in self.board:
                move = {"piece": "P", "from": pos, "to": one_square}
                if next_rank == promo_rank:
                    move["promotion"] = "Q"
                moves.append(move)
                
                # 2. Ruch o dwa pola w przód (tylko z linii startowej)
                if rank == start_rank:
                    two_squares = f"{pos[0]}{rank + 2 * direction}"
                    if two_squares not in self.board:
                        moves.append({"piece": "P", "from": pos, "to": two_squares})

        # 3. Standardowe bicia po skosie
        for df in [-1, 1]:
            new_f_idx = f_idx + df
            if 0 <= new_f_idx < 8:
                target_pos = f"{self.files[new_f_idx]}{rank + direction}"
                if target_pos in self.board:
                    target_side, _ = self.board[target_pos]
                    if target_side != side:
                        move = {"piece": "P", "from": pos, "to": target_pos}
                        if rank + direction == promo_rank:
                            move["promotion"] = "Q"
                        moves.append(move)
        return moves

    def get_knight_moves(self, pos, side):
        """Zasady ruchu dla Skoczka (N)."""
        moves = []
        f_idx = self.files.index(pos[0])
        rank = int(pos[1])
        offsets = [(1,2), (1,-2), (-1,2), (-1,-2), (2,1), (2,-1), (-2,1), (-2,-1)]
        
        for df, dr in offsets:
            new_f = f_idx + df
            new_r = rank + dr
            if 0 <= new_f < 8 and 1 <= new_r <= 8:
                target_pos = f"{self.files[new_f]}{new_r}"
                if target_pos not in self.board or self.board[target_pos][0] != side:
                    moves.append({"piece": "N", "from": pos, "to": target_pos})
        return moves

    def get_sliding_moves(self, pos, side, piece, directions):
        """Wspólna logika dla Wieży (R), Gońca (B) i Hetmana (Q) - ruchy liniowe."""
        moves = []
        f_idx = self.files.index(pos[0])
        rank = int(pos[1])
        
        for df, dr in directions:
            new_f = f_idx
            new_r = rank
            while True:
                new_f += df
                new_r += dr
                if not (0 <= new_f < 8 and 1 <= new_r <= 8):
                    break  # Wyjście poza planszę
                
                target_pos = f"{self.files[new_f]}{new_r}"
                if target_pos not in self.board:
                    moves.append({"piece": piece, "from": pos, "to": target_pos})
                else:
                    target_side, _ = self.board[target_pos]
                    if target_side != side:
                        moves.append({"piece": piece, "from": pos, "to": target_pos})  # Bicie wroga
                    break  # Linia zablokowana (własna figura lub wróg z bicia)
        return moves

    def get_king_moves(self, pos, side):
        """Zasady ruchu dla Króla (K) - ruch o 1 pole."""
        moves = []
        f_idx = self.files.index(pos[0])
        rank = int(pos[1])
        directions = [(1,1), (1,-1), (-1,1), (-1,-1), (0,1), (0,-1), (1,0), (-1,0)]
        
        for df, dr in directions:
            new_f = f_idx + df
            new_r = rank + dr
            if 0 <= new_f < 8 and 1 <= new_r <= 8:
                target_pos = f"{self.files[new_f]}{new_r}"
                if target_pos not in self.board or self.board[target_pos][0] != side:
                    moves.append({"piece": "K", "from": pos, "to": target_pos})
        return moves

    def alpha_beta(self, depth, alpha, beta, maximizing_player, start_time, time_limit):
        """Algorytm Min-Max z odcinaniem Alfa-Beta oraz bezpiecznikiem czasowym."""
        if time.time() - start_time > time_limit:
            raise TimeoutError()

        if depth == 0:
            return self.evaluate_board(), None

        current_side = self.color if maximizing_player else ("black" if self.color == "white" else "white")
        legal_moves = self.generate_all_legal_moves(current_side)
        
        if not legal_moves:
            return self.evaluate_board(), None

        best_move = legal_moves[0]

        if maximizing_player:
            max_eval = -float('inf')
            for move in legal_moves:
                saved_board = self.board.copy()
                self.apply_move(move)
                
                evaluation, _ = self.alpha_beta(depth - 1, alpha, beta, False, start_time, time_limit)
                self.board = saved_board
                
                if evaluation > max_eval:
                    max_eval = evaluation
                    best_move = move
                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in legal_moves:
                saved_board = self.board.copy()
                self.apply_move(move)
                
                evaluation, _ = self.alpha_beta(depth - 1, alpha, beta, True, start_time, time_limit)
                self.board = saved_board
                
                if evaluation < min_eval:
                    min_eval = evaluation
                    best_move = move
                beta = min(beta, evaluation)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def get_best_move(self):
        start_time = time.time()
        time_limit = 2
        
        legal_moves = self.generate_all_legal_moves(self.color)
        if not legal_moves:
            return None
            
        best_move_so_far = legal_moves[0]

        for depth in range(1, 15):
            try:
                _, move = self.alpha_beta(depth, -float('inf'), float('inf'), True, start_time, time_limit)
                if move:
                    best_move_so_far = move
            except TimeoutError:
                break  
        return best_move_so_far


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ["server", "client"]:
        print("Użycie: python main.py [server/client]")
        return

    mode = sys.argv[1]
    HOST = "127.0.0.1"
    PORT = 5050

    if mode == "server":
        print("Uruchamianie serwera (Białe). Oczekiwanie na przeciwnika...")
        peer, address = wait_for_client("0.0.0.0", PORT)
        bot = ChessEngine(color="white")
        
        print("Mój ruch (Białe)...")
        my_move = bot.get_best_move()
        if my_move:
            bot.apply_move(my_move)
            peer.send(my_move)
    else:
        print(f"Uruchamianie klienta (Czarne). Łączenie z {HOST}:{PORT}...")
        peer = connect_to_server(HOST, PORT)
        bot = ChessEngine(color="black")

    try:
        while True:
            print("Oczekiwanie na ruch przeciwnika...")
            enemy_frame = peer.recv()
            print(f"Otrzymano ruch wroga: {enemy_frame}")
            bot.apply_move(enemy_frame)

            print("Obliczanie najlepszej odpowiedzi...")
            my_move = bot.get_best_move()
            
            if my_move is None:
                print("Koniec gry lub brak legalnych ruchów.")
                break

            print(f"Wysyłam mój ruch: {my_move}")
            bot.apply_move(my_move)
            peer.send(my_move)

    except ConnectionError:
        print("\nPołączenie sieciowe zostało zamknięte.")
    finally:
        peer.close()
        print("Koniec rozgrywki.")

if __name__ == "__main__":
    main()