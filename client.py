from distutils.util import change_root
from re import L
import threading, socket, time, os, keyboard
from screen import ScreenBuffers, change_font
from util import *

KEYBOARD_STALL_CNT = 3
HOST =  "localhost"

class Client:
    def __init__(self, screen_buffer):
        #os.system('cls')
        self.screen_buffer = screen_buffer
        self.clear_states()

    def clear_states(self):
        self.name = ''
        self.ready = False
        self.server_state = None
        self.width = WIDTH
        self.height = HEIGHT
        self.canvas = ' ' * self.width * self.height
        self.send_operation_impulse = False
        self.arena = ''
        self.cursor_x = ARENA_WIDTH // 2
        self.cursor_y = ARENA_HEIGHT // 2
        self.card_cursor = 0
        self.player_cursor = 0
        self.uoi_cursor = 0
        self.player_names = ['']
        self.current_player = ''
        self.flip_table = []
        self.cards = ' '
        self.game_stage = LOBBY
        self.discard = False
        self.end_game_message = ''
        self.visibility = ['?', '?', '?']
        
    def update_arena(self, x, y, c):
        self.arena = update_rect(self.arena, x, y, c)

    def parse_server_data(self, _server_data):
        state = {}
        state['online players'] = {}
        state['players data'] = {}

        server_data = _server_data.split('||')
        
        state['game stage'] = int(server_data[0])
        self.game_stage = int(server_data[0])
            
        conn_data = server_data[1]
        for _player_info in conn_data.split('|'):
            player_info = _player_info.split(',')
            state['online players'][player_info[0]] = {'ready': bool(int(player_info[1]))}

        if state['game stage'] == END:
            self.end_game_message = server_data[2]
            self.current_player = ''
            self.arena = server_data[3]
            return state

        if state['game stage'] == GAME:
            players_data = server_data[2]
            for _player_data in players_data.split('|'):
                player_data = _player_data.split(',')
                state['players data'][player_data[0]] = {
                    'U': bool(int(player_data[1])),
                    'O': bool(int(player_data[2])),
                    'I': bool(int(player_data[3]))
                }

            self.player_names = []
            for name in state['players data']:
                state['players data'][name]['online'] = name in state['online players']
                self.player_names.append(name)

            self.current_player = server_data[3]
            self.arena = server_data[4]
            self.identity = bool(int(server_data[5]))
            self.cards = server_data[6]
            if not self.flip_table:
                self.flip_table = [False for _ in range(len(self.cards))]
            self.visibility = server_data[7].split(',')
        return state

    def serialize_client_data(self):
        data = f'{int(self.ready)}|'
        if self.send_operation_impulse:
            data += f'{self.card_cursor},{int(self.flip_table[self.card_cursor])},'\
                + f'{self.cursor_x},{self.cursor_y},{self.player_cursor},{self.uoi_cursor},{int(self.discard)}'
            self.send_operation_impulse = False
            self.discard = False
        else:
            data += 'None'
        return data.encode("UTF-8")

    @Thread
    def connection(self):
        connection_state = ''

        while connection_state != 'OK':
            self.name = input('name: ').strip()
            while not self.name:
                self.name = input('name empty. name: ').strip()
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT_NUMBER))
            self.client_socket.sendall(self.name.encode("UTF-8"))
            connection_state = self.client_socket.recv(MSG_SIZE).decode("UTF-8")
            if any(connection_state == error for error in ["name exists", "game already started", "room full"]):
                print(connection_state)
                self.client_socket.sendall("".encode("UTF-8"))
                self.client_socket.close()

        while True:
            data = self.client_socket.recv(MSG_SIZE).decode("UTF-8")
            self.server_state = self.parse_server_data(data)
            if self.end_game_message:
                self.draw(lim_rjust(self.end_game_message, 20), (self.width - 21, self.height - 4))
                self.client_socket.sendall('end connection'.encode("UTF-8"))
                self.client_socket.close()
                break
            self.client_socket.sendall(self.serialize_client_data())

    def flip(self):
        if self.flip_table:
            self.flip_table[self.card_cursor] = not self.flip_table[self.card_cursor]

    @Thread
    def control(self):
        keyboard_stall = 0
        while True:
            if not self.name:
                continue
            if keyboard_stall:
                keyboard_stall -= 1
            if self.game_stage == LOBBY:
                if keyboard.is_pressed('r'):
                    self.ready = True
                elif keyboard.is_pressed('e'):
                    self.ready = False
            elif self.game_stage == GAME and self.my_turn():
                if keyboard.is_pressed('space'):
                    self.send_operation_impulse = True
                if not keyboard_stall:
                    if keyboard.is_pressed('w'):
                        self.cursor_y = (self.cursor_y - 1) % ARENA_HEIGHT
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('s'):
                        self.cursor_y = (self.cursor_y + 1) % ARENA_HEIGHT
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('a'):
                        self.cursor_x = (self.cursor_x - 1) % ARENA_WIDTH
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('d'):
                        self.cursor_x = (self.cursor_x + 1) % ARENA_WIDTH
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('q'):
                        self.card_cursor = (self.card_cursor - 1) % len(self.cards)
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('e'):
                        self.card_cursor = (self.card_cursor + 1) % len(self.cards)
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('g'):
                        self.player_cursor = (self.player_cursor + 1) % len(self.player_names)
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('t'):
                        self.player_cursor = (self.player_cursor - 1) % len(self.player_names)
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('f'):
                        self.flip()
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('z'):
                        self.uoi_cursor = (self.uoi_cursor - 1) % 3
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('x'):
                        self.uoi_cursor = (self.uoi_cursor + 1) % 3
                        keyboard_stall = KEYBOARD_STALL_CNT
                    if keyboard.is_pressed('p'):
                        self.discard = not self.discard
                        keyboard_stall = KEYBOARD_STALL_CNT
            time.sleep(0.05)


    def draw(self, s, pos):
        location = pos[1] * self.width + pos[0]
        size = min(self.width - pos[0], len(s))
        self.canvas = self.canvas[:location] + s[:size] + self.canvas[location + size:]

    def draw_list(self, list, pos):
        for i, s in enumerate(list):
            if pos[1] + i >= self.height:
                break
            self.draw(s, (pos[0], pos[1] + i))

    def draw_mask(self, symbol, pos, size):
        self.draw_list([symbol * size[0] for _ in range(size[1])], pos)

    def draw_marginal_mask(self, symbol, pos, size):
        self.draw_mask(symbol, pos, size)
        self.draw_mask(' ', (pos[0] + 1, pos[1] + 1), (size[0] - 2, size[1] - 2))

    def draw_player_board(self):
        #self.draw_marginal_mask('*', (12, 1), (50, 13))
        s_list = []
        if self.server_state['game stage'] == LOBBY:
            s_list = [lim_ljust('NAME', 10) + lim_ljust('IS_READY', 10)]
            for name, data in self.server_state['online players'].items():
                s = lim_ljust(name, 10) + lim_ljust('READY' if data['ready'] else 'NOT READY', 10)
                s_list.append(s)
        elif self.server_state['game stage'] == GAME or self.game_stage == END:
            s_list = [' ' * 21 + lim_ljust(' ' * self.uoi_cursor * 2 + 'v', 6),
                '    ' + lim_ljust('NAME', 10) + lim_ljust('       ', 7) + 'U O I ']
            for name, data in self.server_state['players data'].items():
                s = ('>' if self.my_turn() and name == self.player_names[self.player_cursor] else ' ') \
                    + ('‡' if self.current_player == name else ' ') \
                    + ('* ' if self.name == name else '  ') \
                    + lim_ljust(name, 10) \
                    + lim_ljust('ONLINE' if data['online'] else 'OFFLINE', 7) \
                    + lim_ljust((' ' if data['U'] else 'X'), 2) \
                    + lim_ljust((' ' if data['O'] else 'X'), 2) \
                    + lim_ljust((' ' if data['I'] else 'X'), 2)
                s_list.append(s)
            if self.my_turn():
                self.update_arena(self.cursor_x, self.cursor_y, '+')
            if self.visibility[0] != '?' and self.arena[to_linear(ARENA_WIDTH - 1, ARENA_HEIGHT // 2 - 2)] == '?':
                self.update_arena(ARENA_WIDTH - 1, ARENA_HEIGHT // 2 - 2, self.visibility[0])
            if self.visibility[1] != '?' and self.arena[to_linear(ARENA_WIDTH - 1, ARENA_HEIGHT // 2)] == '?':
                self.update_arena(ARENA_WIDTH - 1, ARENA_HEIGHT // 2, self.visibility[1])
            if self.visibility[2] != '?' and self.arena[to_linear(ARENA_WIDTH - 1, ARENA_HEIGHT // 2 + 2)] == '?':
                self.update_arena(ARENA_WIDTH - 1, ARENA_HEIGHT // 2 + 2, self.visibility[2])

            self.draw_list(self.str_to_rect(self.arena, ARENA_WIDTH, ARENA_HEIGHT), (2, 3))
        self.draw_list(s_list, (13, 2))

    def my_turn(self):
        return self.current_player == self.name

    def draw_loop(self):
        edge = 16
        if self.game_stage == GAME or self.game_stage == END:
            self.draw('SABOTEUR', (1, 1))
            self.draw(lim_rjust('Saboteur', 8) if self.identity else lim_rjust('Miner', 8), (self.width - 11, self.height - 3))
            self.draw(lim_ljust(''.join([\
                f'{mirror_char[card] if (card in mirror_char) and self.flip_table[idx] else card} '\
                for idx, card in enumerate(self.cards)]), 12), 
                (edge, self.height - 2))
            self.draw('DISCARD' if self.discard else '       ', (edge, self.height - 3))
            self.draw(lim_ljust(' ' * self.card_cursor * 2 \
                 + ('^' if self.my_turn() else ' '), 12), (edge, self.height - 1))
        self.draw(('    READY' if self.ready else 'NOT READY') if self.game_stage == LOBBY else '         ', (self.width - 11, self.height - 2))
        self.draw_player_board()

    def str_to_rect(self, s, width, height):
        return [s[h * width : (h + 1) * width] for h in range(height)]

    @Thread
    def render(self):
        while True:
            if self.server_state:
                self.screen_buffer.begin_draw()
                self.draw_loop()
                self.screen_buffer.draw('\n'.join(self.str_to_rect(self.canvas, self.width, self.height)))
                self.screen_buffer.end_draw()
            time.sleep(0.01)

screen_buffer = ScreenBuffers(True)
client = Client(screen_buffer)
client.connection()
client.control()
client.render()
while True:
    time.sleep(10)