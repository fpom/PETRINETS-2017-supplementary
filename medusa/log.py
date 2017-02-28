import sys

verbosity = 0
DEBUG = 0b100000
BUILD = 0b010000
INFO  = 0b001000
STAT  = 0b000100
WARN  = 0b000010
ERROR = 0b000001
ALL   = DEBUG | BUILD | INFO | STAT | WARN | ERROR

CLEAR = "\033[0m"
BLUE = "\033[1;34m"
BOLD = "\033[1;38m"
GRAY = "\033[1;30m"
COLUMN = "\033[1;30;47m"
LIGHTGRAY = "\033[0;30m"
GREEN = "\033[1;32m"
CYAN = "\033[1;36m"
MAGENTA = "\033[1;35m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"

def log (message, color=None, eol=True) :
    if color :
        sys.stderr.write(color)
    if isinstance(message, (list, tuple)) :
        message = " ".join(str(m) for m in message)
    sys.stderr.write(message)
    if color :
        sys.stderr.write(CLEAR)
    if eol :
        sys.stderr.write("\n")
    sys.stderr.flush()

players = []

def debug (player, message) :
    if verbosity & DEBUG :
        log("[debug] ", GRAY, eol=False)
        if player is None :
            log(message, LIGHTGRAY, eol=True)
        else :
            for p in players :
                if p == player.name :
                    log(p, COLUMN, eol=False)
                    log(" ", eol=False)
                    log(message, LIGHTGRAY, eol=True)
                    break
                else :
                    log(" ", COLUMN, eol=False)
                    log(" " + (" " * 4), eol=False)
            else :
                log("", eol=True)

def build (message, eol=True) :
    if verbosity & BUILD :
        log("[build] ", BLUE, eol=False)
        log(message, LIGHTGRAY, eol=eol)

def info (message, eol=True) :
    if verbosity & INFO :
        log("[info] ", GREEN, False)
        log(message, eol=eol)

def stat (message, eol=True) :
    if verbosity & STAT :
        log("[stat] ", CYAN, eol=False)
        log(message, LIGHTGRAY, eol=eol)

def warn (message, eol=True) :
    if verbosity & WARN :
        log("[warning] ", YELLOW, False)
        log(message, eol=eol)

def err (message, eol=True) :
    if verbosity & ERROR :
        log("[error] ", RED, False)
        log(message, eol=eol)

def die (message, code=1) :
    err(message)
    sys.exit(code)
