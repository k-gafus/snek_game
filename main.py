"""
List of things "To Do" or to consider in unorderly manner:
----------------------------------------------------------
[] Put together "Menu" system (Maybe as last thing ?)
[] Solidify FSM logic
[] Implement better timers? instead of using "sleep" - research needed
[x] Make "World" class handle all collisions
[x] Refactor "Border" class
[x] Re-implement "Target" consumption logic with "Target" staying ignorant
[x] Refine all "Game Over" conditions and events related to it (Do I need this with
   with "World" class present?)
[x] Create "Joystick" class and move it's function there ?
[x] Implement proper "Score" handler
[x] Implement additional buttons for "Menu" and/or "Reset"?
[x] Fix snek vs food interaction (coordinate mismatch)
[x] Joystick Timer?
"""

import ssd1306
import random
from machine import Pin, ADC, I2C, Timer
from utime import ticks_us, ticks_diff, sleep

#############################
# ---- States & Events ---- #
#############################
class Game_States:
    GAME_MENU = "game_menu"
    RUNNING = "running"
    PAUSED = "paused"
    GAME_OVER = "game_over"

class Joystick_Events:
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    BTN_PRESS = "btn_press"

# Game Manager
class Game_State:
    def __init__(self):
        self.state = Game_States.GAME_MENU
        self.actions = {
            Game_States.GAME_MENU: draw_menu,
            Game_States.RUNNING: None,
            Game_States.PAUSED: None,
            Game_States.GAME_OVER: None
        }

    # Is this even needed?
    def event_handler(self, event):
        next_state = transitions[self.state].get(event)
        if next_state is not None:
            self.state = next_state
            self.actions[self.state]()
        else:
            print("State was not found")

    def current_state(self):
        print(self.state)

"""
Game Manager:
1. Starts in State GAME_MENU
2. If joy_btn pressed -> State RUNNING (May change later, if more options added)
3. While playing, if button pressed -> Game is PAUSED (Need additional btn)
    3.1 Under PAUSED 2? options to Continue or Restart?
    3.2 Continue -> RUNNING / Restart -> Starts game from 0 points
4. When collision happens -> GAME_OVER
    4.1 What options? Main menu / Restart? (Main menu only makes sense if there are
        additional options to change. ex. Play with border or without)

Can this be wrapped in some sort of transitions map?
GAME_MENU -> Button press -> RUNNING
RUNNING -> Button press -> PAUSED
RUNNING -> Collision = True -> GAME_OVER
PAUSED -> Button pressed -> RUNNING
PAUSED -> Button pressed -> RESTART?
GAME_OVER -> Button pressed -> RESTART
GAME_OVER -> Button pressed -> MAIN_MENU?

This transitions map would serve to point, which State is currently active and
depending on it, execute specific block of code within main while loop.
"""

state_transitions = {
    Game_States.GAME_MENU = {
        "btn_press": Game_States.RUNNING
    },
    Game_States.RUNNING = {
        "btn_press": Game_States.PAUSED
        "collision": Game_States.GAME_OVER
    },
    Game_States.PAUSED = {
        "btn_press": Game_States.RUNNING
    },
    Game_States.GAME_OVER = {
        "btn_press": Game_States.GAME_MENU
    }
}

######### GAME STATE FUNCTIONS TEMPORARY LOCATION #########
def draw_menu(display):
    menu_items = [
        "THE SNEK v1.0",
        "Play"
    ]

    x = 10
    y = 10

    for item in menu_items:
        display.text(item, x, y, 1)
        x += 35
        y += 25

    display.fill_rect(35, 38, 3, 3, 1)

#######################
# ---- Constants ---- #
#######################
JOY_X_PIN = 26
JOY_Y_PIN = 27
JOY_BTN_PIN = 22 # For handling Menu options

BTN_RESET = 4 # For "hard reset"? 
BTN_MENU = 5 # For toggling Menu / Pause

DISPLAY_SDA = 0
DISPLAY_SCL = 1
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_ADDRESS = 0x3c

BODY_SIZE = 2

######################
# ---- Hardware ---- #
######################
joy_x = ADC(JOY_X_PIN)
joy_y = ADC(JOY_Y_PIN)
joy_btn = Pin(JOY_BTN_PIN, Pin.IN, Pin.PULL_UP)

btn_reset = Pin(BTN_RESET, Pin.IN, Pin.PULL_UP)
btn_menu = Pin(BTN_MENU, Pin.IN, Pin.PULL_UP)

i2c = I2C(0, sda=Pin(DISPLAY_SDA), scl=Pin(DISPLAY_SCL), freq=400000)

#####################
# ---- Classes ---- #
#####################
class Joystick:
    def __init__(self, JOY_X_PIN, JOY_Y_PIN):
        self.joy_x = ADC(JOY_X_PIN)
        self.joy_y = ADC(JOY_Y_PIN)

        self.last_input = None

        self.timer = Timer(-1)
        self.timer.init(period=50, mode=Timer.PERIODIC, callback=self._scan_input)
    
    def _scan_input(self, timer):
        raw_x = self.joy_x.read_u16() - 32759 # To offset joystick values
        raw_y = self.joy_y.read_u16() - 32759
        joy_default_negative = 500 # To account for joystick "dead zone"
        joy_default_positive = -500

        if raw_x > joy_default_negative:
            self.last_input = Joystick_Events.LEFT
        if raw_x < joy_default_positive:
            self.last_input = Joystick_Events.RIGHT
        if raw_y > joy_default_negative:
            self.last_input = Joystick_Events.UP
        if raw_y < joy_default_positive:
            self.last_input = Joystick_Events.DOWN

    def get_event(self):
        return self.last_input

class Game_Menu:
    def __init__(self):
        self.state = None
    # Menu options: Start -> Border / Borderless
    # Pause state upon button press? -> Continue / Reset options?
    # Game Over = Shows score and maybe time? (Location of this in code may change)

class Snek_Body:
    def __init__(self, controller):
        self.ctrl = controller
        # Initialize with one segment at the start location
        self.segments = [(self.ctrl.x, self.ctrl.y)]
        self.length = 5
        # self.size = 2
        self.a = None
        self.b = None
        
    def update(self):
        # Add current head position
        self.segments.insert(0, (self.ctrl.x, self.ctrl.y))

        # Trim tail
        while len(self.segments) > self.length:
            self.a, self.b = self.segments[-1] # Replaces refresh logic
            self.segments.pop()

    def draw(self, display):
        for seg in self.segments:
            display.fill_rect(seg[0], seg[1], BODY_SIZE, BODY_SIZE, 1)
        # Replaces "whole display" refreshing
        if self.a is not None:
            display.fill_rect(self.a, self.b, BODY_SIZE, BODY_SIZE, 0)

class Snek_Control:
    def __init__(self, starting_x=0, starting_y=0):
        self.x = starting_x
        self.y = starting_y
        self.dx = BODY_SIZE
        self.dy = 0
        # self.max_x = max_x
        # self.max_y = max_y
        self.max_x = DISPLAY_WIDTH
        self.max_y = DISPLAY_HEIGHT
        self.vector_dict = {
            "left": (-BODY_SIZE, 0),
            "right": (BODY_SIZE, 0),
            "up": (0, -BODY_SIZE),
            "down": (0, BODY_SIZE)
        }
   
    @staticmethod
    def vector_swap(ctrl, direction):
        a, b = ctrl.vector_dict[direction]
        if ctrl.dx + a != 0 or ctrl.dy + b != 0:
            ctrl.dx, ctrl.dy = a, b

    def update_pos(self):
        self.x += self.dx
        self.y += self.dy

# Refactor this class into "Obstacles". Borders, walls...etc.
class Obstacle:
    def __init__(self, outter_x, outter_y, inner_x, inner_y, outter_offset, inner_offset):
        self.outter_x = outter_x
        self.outter_y = outter_y
        self.inner_x = inner_x
        self.inner_y = inner_y
        self.outter_offset = outter_offset
        self.inner_offset = inner_offset
    
    def draw(self, display):
        display.fill_rect(self.outter_offset, self.outter_offset, self.outter_x, self.outter_y, 1)
        display.fill_rect(self.inner_offset, self.inner_offset, self.inner_x, self.inner_y, 0)

class Target:
    def __init__(self): # Used to have obstacle as variable
        # self.bounds = obstacle
        self.rand_x = 0
        self.rand_y = 0
        # self.min_x = self.bounds.inner_offset + 1
        # self.max_x = self.bounds.inner_x - BODY_SIZE
        # self.min_y = self.bounds.inner_offset + 1
        # self.max_y = self.bounds.inner_y - BODY_SIZE
        self.exists = False
    
    # # Randomizes coordinates of Target within "Game Field" bounds
    # def randomizer(self):
    #     # Checks if instance of target/food exists
    #     if not self.exists:
    #         self.rand_x = random.randrange(self.min_x, self.max_x, BODY_SIZE)
    #         self.rand_y = random.randrange(self.min_y, self.max_y, BODY_SIZE)
    #         self.exists = True
    
    def target_draw(self, display):  
        display.fill_rect(self.rand_x, self.rand_y, BODY_SIZE, BODY_SIZE, 1)

# Game Referee
class World:
    def __init__(self, snek_body, obstacle, target):
        self.snek_body = snek_body
        self.obstacle = obstacle
        self.target = target

    def update(self):
        """
        Returns True if the game should continue, False if a collision happened.
        """
        # 1. Check if coordinates for target are valid
        if self.target.exists == False:
            self._rand_target_pos()

        # 2. Check if we ate food ('Good' collision)
        self._check_target()

        # 3. Check for 'Bad' collisions
        if self._check_collision():
            return False
        return True

    # Randomizes coordinates of Target within "Game Field" bounds
    def _rand_target_pos(self):
        min_x = self.obstacle.inner_offset + 1
        max_x = self.obstacle.inner_x - BODY_SIZE
        min_y = self.obstacle.inner_offset + 1
        max_y = self.obstacle.inner_y - BODY_SIZE
        # Checks if instance of target/food exists
        if not self.target.exists:
            self.target.rand_x = random.randrange(min_x, max_x, BODY_SIZE)
            self.target.rand_y = random.randrange(min_y, max_y, BODY_SIZE)
            self.target.exists = True

    def _check_target(self):
        head_pos = self.snek_body.segments[0]
        if head_pos == (self.target.rand_x, self.target.rand_y):
            print(f"Target was consumed at: {head_pos}, {(self.target.rand_x, self.target.rand_y)}")
            self.target.exists = False
            self.snek_body.length += 1
            score.update(display_obj)

    def _check_collision(self):
        head_x, head_y = self.snek_body.segments[0]
        
        # Obstacle checks
        if (head_x >= self.obstacle.inner_x or head_x < self.obstacle.inner_offset or
            head_y >= self.obstacle.inner_y or head_y < self.obstacle.inner_offset):
            print("Collision with obstacle has occurred")
            return True
        
        # Self-collision check
        if self.snek_body.segments[0] in self.snek_body.segments[1:]:
            print("Self collision has occurred")
            return True
            
        return False

#######################
# ---- Functions ---- #
#######################
def address_converter():            # This code only works when there
    decimal = i2c.scan()            # is single I2C unit and need for
    for i in decimal:               # it exists once, to get the addr
        hexadecimal = f'0x{i:02x}'
        return hexadecimal

def display_update():
    display_obj.fill(0)
    display_obj.text("Snek v1.0", 20, 32, 1)
    display_obj.show()

###########################
# ---- Class Objects ---- #
###########################
snek_control = Snek_Control(starting_x=10, starting_y=26)
snek_body = Snek_Body(snek_control)
obstacle = Obstacle(outter_x=128, outter_y=55, inner_x=126,
                inner_y=52, outter_offset=0, inner_offset=1)
target = Target() # Used to have snek_body and obstacle as variables
world = World(snek_body, obstacle, target)
joystick_obj = Joystick(JOY_X_PIN, JOY_Y_PIN)
game_state = Game_State()

#########################
# ---- Actions Map ---- #
#########################
# Actions list for Staticmethod Wrapper
actions = {
    Joystick_Events.LEFT: lambda: Snek_Control.vector_swap(snek_control, "left"),
    Joystick_Events.RIGHT: lambda: Snek_Control.vector_swap(snek_control, "right"),
    Joystick_Events.UP: lambda: Snek_Control.vector_swap(snek_control, "up"),
    Joystick_Events.DOWN: lambda: Snek_Control.vector_swap(snek_control, "down")
}

#######################
# ---- Variables ---- #
#######################
display_obj = ssd1306.SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c, addr=DISPLAY_ADDRESS)

#######################
# ---- Main Loop ---- #
#######################
random.seed(joy_x.read_u16() + joy_y.read_u16() + ticks_us())

#########################################
#### TESTING / WORKING ON NEW THINGS ####
#########################################

display_obj.fill(0) # Clears display once at the start
obstacle.draw(display_obj) # Draws border once at the start

class Score:
    def __init__(self):
        self.counter = -00001 # Had to offset score by 1
                              # Unless I come up with better solution later
    def update(self, display):
        self._counter_up()
        # display.fill_rect(90, 57, 38, 9, 0)
        display.fill_rect(0, 57, 128, 9, 0) # Should I use one block or 2 lesser ones
        display.text("Score", 0, 57, 1)
        display.text(f"{self.counter:05d}", 88, 57, 1)

    def _counter_up(self):
        self.counter += 1

score = Score()
score.update(display_obj) # Render score once, before the main loop

# def score():
#     test = 00000
#     display_obj.text("Score", 0, 57, 1)
#     display_obj.text(str(test), 90, 57, 1)
#     test += 1

# score()

while True:
    #### FOR TESTING PURPOSES ####
    # draw_menu(display_obj)
    # display_obj.show()
    #################

    # # 1. Inputs
    # # event = get_joystick_event()
    # event = joystick_obj.get_event()
    # if event in actions: actions[event]()
   
    # # 2. Logic
    # snek_control.update_pos()
    # snek_body.update()  # Handle the list logic
    # world.update()
    # # target.randomizer() # Should be calculated internally
   
    # # 3. Render
    # target.target_draw(display_obj)
    # snek_body.draw(display_obj) # Handle the drawing logic
    # display_obj.show()

    # sleep(0.25) # "Speed" testing

    if game_state.state == game_menu:
        draw_menu(display_obj)
    
    # game_state.current_state()