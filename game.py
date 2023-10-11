import sys
import pygame
import tcod as T
from bearlibterminal import terminal as B
from utils import *
from random import choice

# --- CONSTANTS --- #

VERSION = '0.8'

SCREEN_W = 100
SCREEN_H = 30

MAP_W = 60 - 2
MAP_H = SCREEN_H - 2

BUFFER_H = SCREEN_H // 2 + 1

TITLE = 'Troll Temple'

UNKNOWN_GLYPH = '?', T.red

MAX_SPEED = 5
MIN_SPEED = -4

MAX_DLEVEL = 12

INVENTORY_SLOTS = {
    'w': 'wielded',
    'l': 'carried as light source',
    'a': 'being worn',
    'b': 'being worn',
}

STATUS_W = SCREEN_W - MAP_W - 2
STATUS_H = 10

INV_SIZE = SCREEN_H - 4
INV_W = SCREEN_W
INV_H = INV_SIZE + 3

BOOK_SIZE = SCREEN_H - 4

# --- COLOURS --- #

COLOR_TITLE = T.lighter_yellow

# --- KEYS --- #

pygame.init()

KEYS = [
    ([pygame.K_KP7], ('walk', (-1, -1))),
    ([pygame.K_KP8, pygame.K_UP], ('walk', (0, -1))),
    ([pygame.K_KP9], ('walk', (1, -1))),
    ([pygame.K_KP4, pygame.K_LEFT], ('walk', (-1, 0))),
    ([pygame.K_KP5], 'wait'),
    ([pygame.K_KP6, pygame.K_RIGHT], ('walk', (1, 0))),
    ([pygame.K_KP1], ('walk', (-1, 1))),
    ([pygame.K_KP2, pygame.K_DOWN], ('walk', (0, 1))),
    ([pygame.K_KP3], ('walk', (1, 1))),

    ([pygame.K_ESCAPE], 'quit'),
    ([pygame.K_PERIOD], 'descend'),
    ([pygame.K_g], 'pick_up'),
    ([pygame.K_i], 'inventory'),
    ([pygame.K_b], 'spellbook'),
    ([pygame.K_d], 'drop'),
    ([pygame.K_t], 'test'),
    ([pygame.K_l], 'look'),
    ([pygame.K_w], 'wizard'),
]

def decode_key(key):
    for keys, cmd in KEYS:
        if key in keys:
            return cmd
    return None

# --- QUIT --- #

class Quit(Exception):
    pass

# --- GAME --- #

class Game(object):
    def __init__(self, wizard):
        import mobs
        self.wizard = wizard
        self.wizard = True
        self.selected_game_class = mobs.FIGHTER

    def play(self):
        init(self)
        title_screen()
        intro_screen()
        select_game_class_screen()
        self.start()
        self.loop()
        close()

    def start(self):
        from mobs import Player
        self.player = Player(self.wizard, self.selected_game_class)
        self.turns = 0
        message("Welcome to " + TITLE + "!")
        self.start_map(1)

    def start_map(self, level):
        from maps import Map
        self.map = Map(level)
        x, y, _ = self.map.random_empty_tile()
        self.player.put(self.map, x, y)

    def loop(self):
        draw_all()
        try:
            while True:
                if self.player.death:
                    if self.wizard:
                        if prompt('Die? (Y/N)', [pygame.K_y, pygame.K_n]) == pygame.K_n:
                            new_ui_turn()
                            self.player.resurrect()
                            message('You are resurrected!', T.pink)
                            draw_all()
                            continue
                    prompt(
                        'Game over: %s. Press ENTER' % self.player.death,
                        [pygame.K_RETURN])
                    raise Quit()
                if self.player.won:
                    prompt(
                        'Congratulations! You have won. Press ENTER',
                        [pygame.K_RETURN])
                    raise Quit()
                while self.player.action_turns > 0:
                    key = readkey()
                    self.do_command(key)
                self.map.do_turn(self.turns)
                self.turns += 1
                draw_all()
        except Quit:
            pass

    def do_command(self, key):
        cmd = decode_key(key)
        if cmd is None:
            return
        new_ui_turn()
        if isinstance(cmd, str):
            getattr(self, 'cmd_'+cmd)()
        else:
            name, args = cmd
            getattr(self, 'cmd_'+name)(*args)
        draw_all()

    def cmd_walk(self, dx, dy):
        self.player.walk(dx, dy)

    def cmd_wait(self):
        self.player.wait()

    def cmd_pick_up(self):
        tile = self.player.tile
        if tile.items == []:
            message('There is nothing here to pick up.')
        elif len(tile.items) == 1:
            self.player.pick_up(tile.items[0])
        else:
            while True and tile.items:
                item = select_item('Select an item to pick up, ESC to exit',
                                      tile.items)
                if item:
                    self.player.pick_up(item)
                    draw_all()
                else:
                    break

    def cmd_drop(self):
        item = select_item('Select an item to drop, ESC to exit', self.player.items)
        if item:
            self.player.drop(item)

    def cmd_inventory(self):
        item = select_item('Select an item to use, ESC to exit', self.player.items, True)
        if item:
            self.player.use(item)

    def cmd_descend(self):
        from maps import StairDownTile
        if not isinstance(self.player.tile, StairDownTile):
            message('Stand on a down stairway to descend.')
            return

        self.player.heal(int(self.player.max_hp / 2))
        message('You take a moment to rest, and recover your strength.')
        self.turns += 1
        self.start_map(self.map.level + 1)
        message('After a rare moment of peace, you descend deeper into the heart of the dungeon...')

    def cmd_quit(self):
        if prompt('Quit? (Y/N)', [pygame.K_y, pygame.K_n]) == pygame.K_y:
            raise Quit()
        else:
            new_ui_turn()

    def cmd_wizard(self):
        if self.wizard and self.map.level < MAX_DLEVEL:
            self.start_map(self.map.level+1)

    def cmd_look(self):
        look_mode()
        
    def cmd_spellbook(self):
        if self.player.has_spellbook:
            spell = select_spell('Select a spell to cast, ESC to exit', self.player.spells)
            if spell:
                self.player.use_spell(spell)
        else:
            message("You don't have a spellbook!")

    def cmd_test(self):
        if self.wizard:
            pass

# --- GAME --- #

def out(x, y, text, color = T.white, bkcolor = T.black):
    _txt = GAME.font.render(str(text), True, color, bkcolor)
    if x == 0:
        SCREEN.blit(_txt, (int((SCREEN_W - (_txt.get_width() / GAME.font_width))/2) * GAME.font_width, y * GAME.font_height))
    else:
        SCREEN.blit(_txt, (x * GAME.font_width, y * GAME.font_height))
    
def clear():
    SCREEN.fill(T.black)
    
def refresh():
    pygame.display.flip()
    
def init(game):
    global MESSAGES, GAME, SCREEN
    GAME = game
    MESSAGES = []
    pygame.init()
    GAME.font = pygame.font.Font("UbuntuMono-R.ttf", 20)
    _txt = GAME.font.render("W", True, T.white)
    GAME.font_width = _txt.get_width()
    GAME.font_height = _txt.get_height()
    SCREEN = pygame.display.set_mode((SCREEN_W * GAME.font_width, SCREEN_H * GAME.font_height))
    wiz_str = ""
    if GAME.wizard:
        wiz_str = " [WIZARD]"
    pygame.display.set_caption(TITLE + " v." + VERSION + wiz_str)

def close():
    GAME = None
    pygame.quit()
    sys.exit()

# --- UI --- #

def _draw_map():
    player = GAME.player
    for x in range(MAP_W):
        for y in range(MAP_H):
            tile = GAME.map.tiles[x][y]
            if GAME.map.is_visible(x, y):
                c, color = tile.visible_glyph
                d = dist(x, y, player.x, player.y)
                if d > player.light_range + 1:
                    color *= 0.6
            else:
                c, _ = tile.known_glyph
                color = T.dark_grey
            out(x+1, y+1, c, color)
                                  
def _draw_bar(x, y, cur, max, color):
    r = 0
    w = round(cur * 18 / max)
    for r in range(w):
        out(r + 60 + x + 2, y, "=", color)
    out(79, y, "[", T.dark_grey)
    out(98, y, "]", T.dark_grey)

def _draw_status():
    import mobs
    out(60, 1, "Troll Temple" + " (" +  "Depth: " + str(GAME.map.level) + ")", T.light_green) 
    _game_class = mobs.GAME_CLASSES[GAME.player.game_class - 1]
    out(60, 3, "Trollhunter" + " " + _game_class[0] + " Level " + str(GAME.player.level), _game_class[2])
    out(60, 5, "Exp.:   " + str(GAME.player.exp) + "/" + str(GAME.player.max_exp()), T.light_grey)    
    _draw_bar(18, 5, GAME.player.exp, GAME.player.max_exp(), T.light_yellow)
    out(60, 6, "Health: " + str(round(GAME.player.hp)) + "/" + str(GAME.player.max_hp), T.light_grey)    
    _draw_bar(18, 6, GAME.player.hp, GAME.player.max_hp, T.light_red)
    out(60, 7, "Mana:   " + str(round(GAME.player.mp)) + "/" + str(GAME.player.max_mp), T.light_grey)    
    _draw_bar(18, 7, GAME.player.mp, GAME.player.max_mp, T.light_blue)
    out(60, 8, "Damage: " + describe_dice(*GAME.player.dice) + " Armor: " + str(GAME.player.armor) + " Speed: " + str(GAME.player.speed), T.light_grey)
    deads = ""
    if GAME.wizard:
        deads = " Deads: " + str(GAME.player.deads)
    out(60, 9, "Turns:  " + str(GAME.turns) + " Kills: " + str(GAME.player.kills) + deads, T.light_grey)
    out(60, 10, "Magic:  " + str(GAME.player.magic), T.light_grey)

# --- MESSAGES --- #

def _draw_messages():
    n = len(MESSAGES)
    if n == 0:
        return
    start = max(n - BUFFER_H, 0)
    for i in range(start, n):
        latest, s, color = MESSAGES[i]
        if not latest:
            color *= 0.6
        out(60, i - start + 13, s, color)

def message(s, color = T.white):
    s = s[0].upper() + s[1:]
    print(s)
    MESSAGES.append((True, s, color))
    _draw_messages()
    refresh()

# --- INVENTORY --- #

def _draw_special_items():
    y = 3
    if GAME.player.has_spellbook or GAME.player.has_craftbox or GAME.player.has_alchemyset:
        out(45, 1, "Special items", COLOR_TITLE)
    if GAME.player.has_spellbook:
        out(45, y, "spellbook", T.light_blue)
        y += 1
    if GAME.player.has_craftbox:
        out(45, y, "craftbox", T.dark_yellow)
        y += 1
    if GAME.player.has_alchemyset:
        out(45, y, "alchemyset", T.light_green)
        y += 1

def _draw_items(title, items):
    clear()
    out(2, 1, title, COLOR_TITLE)
    for i, item in enumerate(items):
        out(3, i + 3, chr(i + ord('a')), T.light_grey)
        c, color = item.glyph
        out(5, i+3, chr(ord(c)), color)
        s = item.descr
        if GAME.player.has_equipped(item):
            color = T.white
            out(1, i+3, '*', color)
        else:
            color = T.light_grey
        out(7, i+3, s, color)

def draw_inventory(title='Inventory', items=None, flag=False):
    _draw_items(title, items or GAME.player.items)
    if flag:
        _draw_special_items()
    _draw_messages()
    _draw_status()
    refresh()

# --- SPELLBOOK --- #

def _draw_spellbook(title, spells):
    clear()
    out(2, 1, title, COLOR_TITLE)
    for i, spell in enumerate(spells):
        out(3, i + 3, chr(i + ord('a')), T.light_grey)
        out(5, i+3, spell.descr, T.light_grey)

def spellbook(title='Spellbook', spells=None):
    _draw_spellbook(title, spells or GAME.player.spells)
    _draw_messages()
    _draw_status()
    refresh()   

# --- UI --- #

def draw_all():
    clear()
    _draw_map()
    _draw_messages()
    _draw_status()
    refresh()

def select_game_class_screen():
    import mobs
    clear()
    
    out(2, 1, "Choose your class", COLOR_TITLE)
    for i, game_class in enumerate(mobs.GAME_CLASSES):
        out(3, i + 3, chr(i + ord('a')), T.light_grey) 
        out(5, i + 3, game_class[0], game_class[2])    
    refresh()
    sel = select_game_class()
    GAME.selected_game_class = sel[1]

def intro_screen():
    clear()
    
    out(0, 2, "Many centuries ago...", COLOR_TITLE)
    
    
    out(0, 28, "Press ENTER to continue...", T.light_grey)
    refresh()
    anykey()

def title_screen():
    clear()

    out(5, 4,  '##### ####   ###  #     #', T.green)
    out(5, 5,  '# # # #   # #   # #     #', T.green)
    out(5, 6,  '  #   ####  #   # #     #', T.green)
    out(5, 7,  '  #   # #   #   # #     #', T.green)
    out(5, 8,  '  #   #  #   ###  ##### #####', T.green)

    out(10, 10,  '##### ##### #     # ##### #     #####', T.light_red)
    out(10, 11,  '# # # #     ##   ## #   # #     #', T.light_red)
    out(10, 12,  '  #   ###   # # # # ####  #     ###', T.light_red)
    out(10, 13,  '  #   #     #  #  # #     #     #', T.light_red)
    out(10, 14,  '  #   ##### #     # #     ##### #####', T.light_red)

    out(35, 17,  ' v.' + VERSION, T.light_green)

    out(10, 22,  'by Apromix <maxwof@ukr.net>', T.light_yellow)

    out(48, 4,  '                        /\ ', T.darker_yellow)
    out(48, 5,  '                      _/--\ ', T.darker_yellow)
    out(48, 6,  '                     /     O ', T.darker_yellow)
    out(48, 7,  '               /\   /       \ ', T.darker_yellow)
    out(48, 8,  '             _/| \_/      _  \ ', T.darker_yellow)
    out(48, 9,  '            /     /     _/ \  \ ', T.darker_yellow)
    out(48, 10, '         __/  ___/     /    \  ) ', T.darker_yellow)
    out(48, 11, '        y       Λ     |      | | ', T.darker_yellow)
    out(48, 12, '       ,       / \   /       | | ', T.darker_yellow)
    out(48, 13, '      /        \  \  |        \( ', T.darker_yellow)
    out(48, 14, '     /             \|          | \ ', T.darker_yellow)
    out(45, 15, '       ,___|_  _|-----`__ |-|- __|__,---', T.darker_yellow)
    out(45, 16, '      ._/ /                 \____/      \, ', T.darker_yellow)
    out(45, 17, '     /  \ \                  \```\        \, ', T.darker_yellow)
    out(45, 18, '    (__   _\                 |```|         L_, ', T.darker_yellow)
    out(45, 19, '    /   ./ /       /\         \```\       /  _\ ', T.darker_yellow)
    out(45, 20, '   |   /  /       /  \        |```|       \,   | ', T.darker_yellow)
    out(45, 21, '  /  (                |       \```\       /  _/ \ ', T.darker_yellow)
    out(45, 22, ' /                            |```|           _,| ', T.darker_yellow)
    out(45, 23, ' |_                           \```\             \ ', T.darker_yellow)

    out(0, 28, "Press ENTER to continue...", T.light_grey)
    refresh()
    anykey()

def describe_tile(x, y):
    if GAME.map.is_visible(x, y):
        tile = GAME.map.tiles[x][y]
        message('%s.' % tile.name, tile.glyph[1])
        if tile.mob:
            message('%s.' % tile.mob.name, tile.mob.glyph[1])
        for item in tile.items:
            message('%s.' % item.descr, item.glyph[1])
    else:
        message('Out of sight.', T.grey)

def new_ui_turn():
    for i in reversed(list(range(len(MESSAGES)))):
        latest, s, color = MESSAGES[i]
        if latest:
            MESSAGES[i] = False, s, color
        else:
            break

# --- LOOK --- #

def look_mode():
    global MESSAGES
    from game import decode_key

    x, y, map = GAME.player.x, GAME.player.y, GAME.player.map
    _messages = MESSAGES
    MESSAGES = []
    message('Look mode - use movement keys, ESC to exit.', COLOR_TITLE)
    new_ui_turn()
    _draw_messages()
    redraw = True
    while True:
        if redraw:
            draw_all()

            tile = map.tiles[x][y]
            if map.is_visible(x, y):
                char, color = tile.visible_glyph
                out(x+1, y+1, char, color, T.light_gray)
            refresh()
            describe_tile(x, y)

            _draw_messages()
            refresh()

            while MESSAGES and MESSAGES[-1][0]:
                MESSAGES.pop()
                
            redraw = False
        cmd = decode_key(readkey())
        if cmd == 'quit':
            break
        elif isinstance(cmd, tuple):
            name, args = cmd
            if name == 'walk':
                dx, dy = args
                if map.in_map(x + dx, y + dy):
                    x, y = x + dx, y + dy
                    redraw = True

    MESSAGES = _messages

# --- KEYS --- #

def select_item(title, items, flag = False):
    items = items[:INV_SIZE]
    draw_inventory(title, items, flag)
    while True:
        key = readkey()
        if key in range(pygame.K_a, pygame.K_z):
            i = key - pygame.K_a
            if 0 <= i < len(items):
                return items[i]
        if key in [pygame.K_ESCAPE]:
            return None
    return None

def select_spell(title, spells):
    spells = spells[:BOOK_SIZE]
    spellbook(title, spells)
    while True:
        key = readkey()
        if key in range(pygame.K_a, pygame.K_z):
            i = key - pygame.K_a
            if 0 <= i < len(spells):
                return spells[i]
        if key in [pygame.K_ESCAPE]:
            return None
    return None

def select_game_class():
    import mobs
    while True:
        key = readkey()
        if key in range(pygame.K_a, pygame.K_z):
            i = key - pygame.K_a
            if 0 <= i < len(mobs.GAME_CLASSES):
                return mobs.GAME_CLASSES[i]

def prompt(s, choices = None):
    message(s, T.green)
    draw_all()
    if choices:
        choices = list(choices)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key in choices:
                        return event.key
    else:
        return readkey()

def readkey():
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            return event.key

def anykey():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if pygame.key.get_pressed()[pygame.K_RETURN]:
                    return






