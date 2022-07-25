import threading, socket, time, os, random
#from screen import ScreenBuffers # comment for linux
from util import *

class ScreenBuffers:

    def __init__(self):
        pass

    def begin_draw(self):
        self.log = open(f'{os.path.dirname(__file__)}/connection_log.txt', "w")

    def end_draw(self):
        self.log.close()

    def draw(self, *_str, end='\n'):
        s = ' '.join([str(s) for s in [*_str]]) + end
        self.log.write(s)


ROOM_LIMIT = 10

class Server:
    def __init__(self, screen_buffer):
        self.host = ''
        self.port = PORT_NUMBER
        self.connections = {}
        self.lock = threading.Lock()
        self.screen_buffer = screen_buffer
        self.clear_state()
        
    def clear_state(self):
        self.arena = ' ' * ARENA_WIDTH * ARENA_HEIGHT
        self.treasure = ['♥', '╗', '╔']
        self.players_data = {}
        self.game_stage = LOBBY
        self.current_player = ''
        self.last_player = ''
        self.winner = UNRESOLVED

    @Thread
    def build_connection(self):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_socket.bind((self.host, self.port))
        self.listening_socket.listen()
        while True:
            connection, address = self.listening_socket.accept()
            self.listening_socket.setblocking(True)
            name = connection.recv(MSG_SIZE).decode("UTF-8")

            def request_close(err_msg):
                connection.sendall(err_msg.encode())
                connection.recv(MSG_SIZE)
                connection.close()

            if name in self.connections:
                request_close("name exists")
                continue
            if self.game_stage == GAME:
                if not name in self.players_data:
                    request_close("game already started")
                    continue
            if len(self.connections) == ROOM_LIMIT:
                request_close("room full")
                continue

            # establish connection
            connection.sendall("OK".encode())
            with self.lock:
                if self.game_stage == GAME:
                    assert(name in self.players_data)
                assert(not name in self.connections)

                self.connections[name] = {
                    'connection': connection, 
                    'address': address, 
                    'ready': False,
                }
            self.ongoing_connection(name)
            
    def serialize_connections_data(self, name):
        with self.lock:
            conn_data = (''.join([f"{_name},{int(_conn['ready'])}|" for _name, _conn in self.connections.items()]))[:-1]
        data = f'{self.game_stage}||{conn_data}'
        if self.game_stage == END:
            if self.winner == SABOTEUR:
                data = f"{data}||saboteurs win: {', '.join(self.saboteur_list)}||{self.arena}"
            elif self.winner == MINER:
                data = f"{data}||miners win: {', '.join(self.miner_list)}||{self.arena}"
            else:
                assert(False)
        elif self.game_stage == GAME:
            with self.lock:
                _players_data = (''.join([
                    f"{_name},{int(_data['U'])},{int(_data['O'])},{int(_data['I'])}|" \
                    for _name, _data in self.players_data.items()
                ]))[:-1]
            player_data = self.players_data[name]
            data = f"{data}||{_players_data}||{self.current_player}||{self.arena}" + \
                f"||{int(player_data['identity'])}||{player_data['cards']}" + \
                f"||{player_data['visibility'][0]},{player_data['visibility'][1]},{player_data['visibility'][2]}"

        return data.encode("UTF-8")

    def is_connected_to_start(self, card, x, y):
        self.truth_table = [False for _ in range(len(self.arena))]
        self.is_connected_to_start_dfs(card, x, y, self.truth_table)
        return self.truth_table[to_linear(0, ARENA_HEIGHT // 2)]

    def is_connected_to_start_dfs(self, card, x, y, truth_table):
        up, down, left, right = ' ', ' ', ' ', ' '
        if y != 0:
            if not truth_table[to_linear(x, y - 1)]:
                up = self.arena[to_linear(x, y - 1)]
                if up in char_info:
                    if char_info[up][CENTER] and char_info[up][DOWN] and char_info[card][UP]:
                        truth_table[to_linear(x, y - 1)] = True
                        self.is_connected_to_start_dfs(up, x, y - 1, truth_table)
        if y != ARENA_HEIGHT - 1:
            if not truth_table[to_linear(x, y + 1)]:
                down = self.arena[to_linear(x, y + 1)]
                if down in char_info:
                    if char_info[down][CENTER] and char_info[down][UP] and char_info[card][DOWN]:
                        truth_table[to_linear(x, y + 1)] = True
                        self.is_connected_to_start_dfs(down, x, y + 1, truth_table)
        if x != 0: 
            if not truth_table[to_linear(x - 1, y)]:
                left = self.arena[to_linear(x - 1, y)]
                if left in char_info:
                    if char_info[left][CENTER] and char_info[left][RIGHT] and char_info[card][LEFT]:
                        truth_table[to_linear(x - 1, y)] = True
                        self.is_connected_to_start_dfs(left, x - 1, y, truth_table)
        if x != ARENA_WIDTH - 1: 
            if not truth_table[to_linear(x + 1, y)]:
                right = self.arena[to_linear(x + 1, y)]
                if right in char_info:
                    if char_info[right][CENTER] and char_info[right][LEFT] and char_info[card][RIGHT]:
                        truth_table[to_linear(x + 1, y)] = True
                        self.is_connected_to_start_dfs(right, x + 1, y, truth_table)


    def can_put_card(self, card, x, y):
        if not self.is_connected_to_start(card, x, y):
            return False
        up, down, left, right, center = ' ', ' ', ' ', ' ', self.arena[to_linear(x, y)]
        if center != ' ':
            return False
        if y != 0:
            up = self.arena[to_linear(x, y - 1)]
        if y != ARENA_HEIGHT - 1:
            down = self.arena[to_linear(x, y + 1)]
        if x != 0: 
            left = self.arena[to_linear(x - 1, y)]
        if x != ARENA_WIDTH - 1: 
            right = self.arena[to_linear(x + 1, y)]
        if all(char == ' ' for char in [up, down, left, right]):
            return False
        #if not any((not (char == ' ' or char == '?') and char_info[char][CENTER]) for char in [up, down, left, right]):
        #    return False
        if up != ' ' and up != '?':
            assert(up in char_info)
            if char_info[up][DOWN] != char_info[card][UP]:
                return False
        if down != ' ' and down != '?':
            assert(down in char_info)
            if char_info[down][UP] != char_info[card][DOWN]:
                return False
        if left != ' ' and left != '?':
            assert(left in char_info)
            if char_info[left][RIGHT] != char_info[card][LEFT]:
                return False
        if right != ' ' and right != '?':
            assert(right in char_info)
            if char_info[right][LEFT] != char_info[card][RIGHT]:
                return False
        return True


    def check_winning(self, x, y):
        def treasure_state(cursor_x, cursor_y):
            if cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2 - 2:
                return 1
            if cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2:
                return 2
            if cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2 + 2:
                return 3
            return 0
        char = self.arena[to_linear(x, y)]
        if x == ARENA_WIDTH - 2:
            t = treasure_state(x + 1, y)
            if t and char_info[char][RIGHT]:
                treasure = self.treasure[t - 1]
                if treasure == '♥':
                    self.winner = MINER
                    self.update_arena(x + 1, y, treasure)
                    return True
                if not char_info[treasure][LEFT]:
                    treasure = mirror_char[treasure]
                self.update_arena(x + 1, y, treasure)
        elif x == ARENA_WIDTH - 1 and y > 0 and y < ARENA_HEIGHT - 1:
            t_up = treasure_state(x, y - 1)
            if t_up and char_info[char][UP]:
                treasure = self.treasure[t_up - 1]
                if treasure == '♥':
                    self.winner = MINER
                    self.update_arena(x, y - 1, treasure)
                    return True
                if not char_info[treasure][DOWN]:
                    treasure = mirror_char[treasure]
                self.update_arena(x, y - 1, treasure)
            t_down = treasure_state(x, y + 1)
            if t_down and char_info[char][DOWN]:
                treasure = self.treasure[t_down - 1]
                if treasure == '♥':
                    self.winner = MINER
                    self.update_arena(x, y + 1, treasure)
                    return True
                if not char_info[treasure][UP]:
                    treasure = mirror_char[treasure]
                self.update_arena(x, y + 1, treasure)

        return False

    def resolve_operation(self, name, operation_str):
        card_cursor, flipped, cursor_x, cursor_y, \
            player_cursor, uoi_cursor, discard = operation_str.split(',')

        def draw_new_card():
            new_card = ' '
            if self.cards:
                new_card = self.cards.pop(0)
            self.players_data[name]['cards'] = update_str(self.players_data[name]['cards'],
                int(card_cursor), new_card)
                

        card = self.players_data[name]['cards'][int(card_cursor)]
        if card != ' ' and bool(int(discard)):
            draw_new_card()
            return True

        if (card in mirror_char) and bool(int(flipped)):
            card = mirror_char[card]

        if card in char_info:
            if self.can_put_card(card, int(cursor_x), int(cursor_y)):
                self.update_arena(int(cursor_x), int(cursor_y), card)
                if self.check_winning(int(cursor_x), int(cursor_y)):
                    return False
                draw_new_card()
                return True
        elif card == '╳':
            cursor_x, cursor_y = int(cursor_x), int(cursor_y)
            if not any([
                cursor_x == 0 and cursor_y == ARENA_HEIGHT // 2,
                cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2,
                cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2 - 2,
                cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2 + 2,
            ]) and self.arena[to_linear(cursor_x, cursor_y)] != ' ':
                self.update_arena(int(cursor_x), int(cursor_y), ' ')
                draw_new_card()
                return True
        elif card == 'Θ':
            visibility = self.players_data[name]['visibility']
            cursor_x, cursor_y = int(cursor_x), int(cursor_y)
            if cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2 - 2:
                if visibility[0] == '?':
                    visibility[0] = self.treasure[0]
                    draw_new_card()
                    return True
            elif cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2:
                if visibility[1] == '?':
                    visibility[1] = self.treasure[1]
                    draw_new_card()
                    return True
            elif cursor_x == ARENA_WIDTH - 1 and cursor_y == ARENA_HEIGHT // 2 + 2:
                if visibility[2] == '?':
                    visibility[2] = self.treasure[2]
                    draw_new_card()
                    return True
        elif card in 'ŬŎĬUOI':
            player_data = self.players_data[self.player_name_list[int(player_cursor)]]
            if card == 'Ŭ' and player_data['U']:
                player_data['U'] = False
                draw_new_card()
                return True
            elif card == 'Ŏ' and player_data['O']:
                player_data['O'] = False
                draw_new_card()
                return True
            elif card == 'Ĭ' and player_data['I']:
                player_data['I'] = False
                draw_new_card()
                return True
            if card == 'U' and not player_data['U']:
                player_data['U'] = True
                draw_new_card()
                return True
            elif card == 'O' and not player_data['O']:
                player_data['O'] = True
                draw_new_card()
                return True
            elif card == 'I' and not player_data['I']:
                player_data['I'] = True
                draw_new_card()
                return True
        elif card in 'ΦΩΨ':
            player_data = self.players_data[self.player_name_list[int(player_cursor)]]
            uoi_cursor = int(uoi_cursor)
            # cute OwO my genious symbolic design
            if card == 'Φ':
                if uoi_cursor == O_O and not player_data['O']:
                    player_data['O'] = True
                    draw_new_card()
                    return True
                elif uoi_cursor == I_I and not player_data['I']:
                    player_data['I'] = True
                    draw_new_card()
                    return True
            elif card == 'Ω':
                if uoi_cursor == O_O and not player_data['O']:
                    player_data['O'] = True
                    draw_new_card()
                    return True
                elif uoi_cursor == U_U and not player_data['U']:
                    player_data['U'] = True
                    draw_new_card()
                    return True
            elif card == 'Ψ':
                if uoi_cursor == I_I and not player_data['I']:
                    player_data['I'] = True
                    draw_new_card()
                    return True
                elif uoi_cursor == U_U and not player_data['U']:
                    player_data['U'] = True
                    draw_new_card()
                    return True

        return False

    def next_player(self):
        def get_next(current_player):
            return self.player_name_list[(self.player_name_list.index(current_player) + 1) % len(self.player_name_list)]
        def has_no_cards(player):
            return all(card == ' ' for card in self.players_data[player]['cards'])
        self.last_player = self.current_player
        self.current_player = get_next(self.current_player)

        while has_no_cards(self.current_player) and self.last_player != self.current_player:
            self.current_player = get_next(self.current_player)
        # effect of last card has been resolved. If last player who has cards is current player, 
        # and current player runs out of cards, and if miners don't win, saboteurs win
        if has_no_cards(self.current_player) and self.last_player == self.current_player:
            if self.winner != MINER:
                self.winner = SABOTEUR

    def update_player_data(self, name, data):
        ready, operation_str = data.split('|')
        with self.lock:
            self.connections[name]['ready'] = bool(int(ready))
            if self.current_player == name and operation_str != 'None' and self.resolve_operation(name, operation_str):
                self.next_player()

    @Thread
    def ongoing_connection(self, name):
        while True:
            connection = self.connections[name]['connection']
            try:
                connection.sendall(self.serialize_connections_data(name)) # the news is propagated to players
                connection.settimeout(5.0)
                data = connection.recv(MSG_SIZE).decode("UTF-8")
            except:
                break
            if data == 'end connection':
                break
            self.update_player_data(name, data) # saboteur may win here
            time.sleep(0.05)

        # disconnect
        connection.close()
        with self.lock:
            self.connections.pop(name)

    def update_arena(self, x, y, c):
        self.arena = update_rect(self.arena, x, y, c)

    def deal_cards(self):
        self.cards = list(card_pool)
        random.shuffle(self.cards)
        num_cards_per_player = hand_size[len(self.players_data)]
        for name in self.players_data:
            self.players_data[name]['cards'] = ''.join(self.cards[:num_cards_per_player])
            self.cards = self.cards[num_cards_per_player:]

    def clear_arena(self):
        self.arena = ' ' * ARENA_WIDTH * ARENA_HEIGHT
        self.update_arena(0, ARENA_HEIGHT // 2, '╬')
        self.update_arena(ARENA_WIDTH - 1, ARENA_HEIGHT // 2, '?')
        self.update_arena(ARENA_WIDTH - 1, ARENA_HEIGHT // 2 - 2, '?')
        self.update_arena(ARENA_WIDTH - 1, ARENA_HEIGHT // 2 + 2, '?')

    def show_connections(self):
        self.screen_buffer.draw('ongoing connections')
        with self.lock:
            for name, conn in self.connections.items():
                self.screen_buffer.draw(name, conn['address'])

    @Thread
    def query_connection(self):
        while True:
            # if all players are ready go to game stage
            with self.lock:
                connection_states = [self.connections[name]['ready'] for name in self.connections]
                if self.game_stage == LOBBY and connection_states.count(True) >= 3 and all(connection_states):
                    self.game_stage = GAME
                    self.clear_arena()
                    random.shuffle(self.treasure)
                    self.player_name_list = []
                    self.saboteur_list = []
                    self.miner_list = []
                    identity_list = get_identity_list(len(self.connections))
                    for idx, name in enumerate(self.connections):
                        self.players_data[name] = {
                            'U': True,
                            'O': True,
                            'I': True,
                            'identity': identity_list[idx],
                            'visibility': ['?', '?', '?']
                        }
                        if identity_list[idx]:
                            self.saboteur_list.append(name)
                        else:
                            self.miner_list.append(name)
                        self.player_name_list.append(name)
                    self.deal_cards()
                    self.current_player = random.choice(self.player_name_list)
                if self.game_stage == GAME:
                    if self.winner != UNRESOLVED:
                        self.game_stage = END
                if self.game_stage == GAME or self.game_stage == END:
                    if not self.connections:
                        self.clear_state()
            time.sleep(0.05)

    @Thread
    def log(self):
        while True:
            # show connections and player state
            self.screen_buffer.begin_draw()
            self.screen_buffer.draw(f'game stage {self.game_stage}, current player {self.current_player},'
                + f' winner {self.winner}, last player {self.last_player}')
            self.screen_buffer.draw('collected info')
            with self.lock:
                for name, data in self.connections.items():
                    self.screen_buffer.draw(name, 'READY' if data['ready'] else 'NOT READY')
            self.show_connections()
            self.screen_buffer.end_draw()
            time.sleep(1)

screen_buffer = ScreenBuffers()
server = Server(screen_buffer)
server.build_connection()
server.query_connection()
server.log()
while True:
    time.sleep(10)