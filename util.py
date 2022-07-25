import threading, random, copy
def Thread(func):
    def start_thread(self, *args):
        thread = threading.Thread(target=lambda: func(self, *args))
        thread.daemon = True
        thread.start()
    return start_thread

MSG_SIZE = 4096
WIDTH, HEIGHT = 43, 17
PORT_NUMBER = 14514

def lim_ljust(s, cnt):
    return s[:cnt].ljust(cnt)
    
def lim_rjust(s, cnt):
    return s[:cnt].rjust(cnt)

ARENA_WIDTH, ARENA_HEIGHT = 9, 13

def to_linear(x, y):
    return y * ARENA_WIDTH + x

def update_rect(s, x, y, c):
    idx = to_linear(x, y)
    return update_str(s, idx, c)

def update_str(s, idx, c):
    return s[:idx] + c + s[idx + 1:]

# ---
def truth_list(nt, nf):
    return [True] * nt + [False] * nf

identity_distribution = {
    3: truth_list(1, 3),
    4: truth_list(1, 4),
    5: truth_list(2, 4),
    6: truth_list(2, 5),
    7: truth_list(3, 5),
    8: truth_list(3, 6),
    9: truth_list(3, 7),
    10: truth_list(4, 7)
}

def get_identity_list(num_players):
    ret = copy.copy(identity_distribution[num_players])
    random.shuffle(ret)
    return ret[0:num_players]

# ---
hand_size = {
    3: 6,
    4: 6,
    5: 6,
    6: 5,
    7: 5,
    8: 4,
    9: 4,
    10: 4
}
# ---
U_U = 0
O_O = 1
I_I = 2
card_pool = 'Θ' * 6 + '╠╬╩╗' * 5 + '║╔' * 4 + '═╳ŬŎĬ' * 3 + 'UOI' * 2 + '↓┃┣╋┻━┏┓←ΦΩΨ'
mirror_char = {
    '╠': '╣',
    '╬': '╬',
    '╩': '╦',
    '╗': '╚', # 5
    '║': '║',
    '╔': '╝', # 4
    '═': '═', # 3
    '↓': '↑',
    '┃': '┃',
    '┣': '┫',
    '╋': '╋',
    '┻': '┳',
    '━': '━',
    '┏': '┛',
    '┓': '┗',
    '←': '→', # 1
}
CENTER = 0
UP = 1
DOWN = 2
LEFT = 3
RIGHT = 4
char_info = {
    '╠': [True, True, True, False, True],
    '╣': [True, True, True, True, False],
    '╬': [True, True, True, True, True],
    '╩': [True, True, False, True, True],
    '╦': [True, False, True, True, True],
    '╗': [True, False, True, True, False],
    '╚': [True, True, False, False, True],
    '║': [True, True, True, False, False],
    '╔': [True, False, True, False, True],
    '╝': [True, True, False, True, False],
    '═': [True, False, False, True, True],
    '↓': [False, False, True, False, False],
    '↑': [False, True, False, False, False],
    '┃': [False, True, True, False, False],
    '┣': [False, True, True, False, True],
    '┫': [False, True, True, True, False],
    '╋': [False, True, True, True, True],
    '┻': [False, True, False, True, True],
    '┳': [False, False, True, True, True],
    '━': [False, False, False, True, True],
    '┏': [False, False, True, False, True],
    '┛': [False, True, False, True, False],
    '┓': [False, False, True, True, False],
    '┗': [False, True, False, False, True],
    '←': [False, False, False, True, False],
    '→': [False, False, False, False, True],
}
# update reverse table
UNRESOLVED, SABOTEUR, MINER = 0, 1, 2
LOBBY, GAME, END = 0, 1, 2