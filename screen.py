import win32console, os, ctypes, win32ui, win32con, subprocess
from util import WIDTH, HEIGHT

subprocess.check_output("chcp 437", shell=True);

def create_font():
    LF_FACESIZE = 32
    STD_OUTPUT_HANDLE = -11

    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class CONSOLE_FONT_INFOEX(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong),
                    ("nFont", ctypes.c_ulong),
                    ("dwFontSize", COORD),
                    ("FontFamily", ctypes.c_uint),
                    ("FontWeight", ctypes.c_uint),
                    ("FaceName", ctypes.c_wchar * LF_FACESIZE)]

    font = CONSOLE_FONT_INFOEX()
    font.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)
    font.nFont = 12
    font.dwFontSize.X = 11
    font.dwFontSize.Y = 18
    font.FontFamily = 54
    font.FontWeight = 400
    font.FaceName = "Consolas"

    return font
font = create_font()

def change_font(buffer=None):
    STD_OUTPUT_HANDLE = -11
    if buffer:
        buffer.SetStdHandle(STD_OUTPUT_HANDLE)
    handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    ctypes.windll.kernel32.SetCurrentConsoleFontEx(handle, ctypes.c_long(False), ctypes.pointer(font))

class ScreenBuffers:

    def __init__(self, adjust_size=False, num_buf=2):
        self.num_buf = num_buf
        self.buffers = [win32console.CreateConsoleScreenBuffer() for _ in range(num_buf)]
        self.curr = 0
        self.prev = 0
        win32console.SetConsoleTitle('Saboteur')
        self.adjust_size = adjust_size
        #self.resize_window()

    def resize_window(self):
        if self.adjust_size:
            for buffer in self.buffers:
                buffer.SetConsoleWindowInfo(True, win32console.PySMALL_RECTType(0, 0, WIDTH, HEIGHT))

    def begin_draw(self):
        self.prev = self.curr
        self.curr = (self.curr + 1) % self.num_buf
        buffer = win32console.CreateConsoleScreenBuffer()
        self.buffers[self.curr] = buffer
        change_font(buffer)
        self.resize_window()

    def draw(self, *_str, end='\n'):
        self.buffers[self.curr].WriteConsole(' '.join([str(s) for s in [*_str]]) + end)
        
    def end_draw(self):
        self.buffers[self.curr].SetConsoleActiveScreenBuffer()
        self.buffers[self.prev].Close()

if __name__ == '__main__':
    buffers = ScreenBuffers()
    n = 1
    while True:
        buffers.begin_draw()
        buffers.draw(f'hahaha{n}\n')
        buffers.draw(f'hehehe{n}\n')
        buffers.end_draw()
        n = (n + 1) % 2