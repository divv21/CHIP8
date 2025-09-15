import sys
import pyglet 
import random
from pyglet.sprite import Sprite
import os 
import itertools
import time 

KEY_MAP = {
    pyglet.window.key._1: 0x1,
    pyglet.window.key._2: 0x2,
    pyglet.window.key._3: 0x3,
    pyglet.window.key._4: 0xC,
    pyglet.window.key.Q: 0x4,
    pyglet.window.key.W: 0x5,
    pyglet.window.key.E: 0x6,
    pyglet.window.key.R: 0xD,
    pyglet.window.key.A: 0x7,
    pyglet.window.key.S: 0x8,
    pyglet.window.key.D: 0x9,
    pyglet.window.key.F: 0xE,
    pyglet.window.key.Z: 0xA,
    pyglet.window.key.X: 0x0,
    pyglet.window.key.C: 0xB,
    pyglet.window.key.V: 0xF,
}

class cpu(pyglet.window.Window):

    def initialize(self): 
        self.clear()
        self.key_inputs = [0]*16 #16 button keyboard input
        self.display_buffer = [[0] * 64 for _ in range(32)]#[0]*32*64 #64*32 display output
        self.memory = [0]*4096 #4096 bytes = interpreter itself, fonts, loads program
        self.gpio = [0]*16 #16 8-bit general purpose registers, store values for operations, last-flag register 
        self.opcode = 0
        self.index = 0 #16 bit index register
        self.pc = 0x200 #16 bit program counter
        self.stack = [] #stack pointer 

        self.sound_timer = 0 #timer registers 
        self.delay_timer = 0
        self.should_draw= False
        self.key_wait = False
        self.wait_register = 0

        self.pixel = pyglet.resource.image('pixel.png')
        self.buzz = pyglet.resource.media('buzz.wav', streaming=False)

        self.batch = pyglet.graphics.Batch()
        self.sprites = []
        for i in range(0,2048):

            self.sprites.append(pyglet.sprite.Sprite(self.pixel,batch=self.batch))
  
        # instruction functions
        funcmap = None # store op <-> method mappings here
        vx = 0 # store register numbers here for op method access
        vy = 0

        self.fonts = [
            0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
            0x20, 0x60, 0x20, 0x20, 0x70, # 1
            0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
            0x90, 0x90, 0xF0, 0x10, 0x10, # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
            0xF0, 0x10, 0x20, 0x40, 0x40, # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90, # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
            0xF0, 0x80, 0x80, 0x80, 0xF0, # C
            0xE0, 0x90, 0x90, 0x90, 0xE0, # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
            0xF0, 0x80, 0xF0, 0x80, 0x80  # F
        ]

        for i in range(len(self.fonts)):
            self.memory[i] = self.fonts[i]

        self.funcmap =  {0x0000: self._0ZZZ,
                    0x00e0: self._0ZZ0,
                    0x00ee: self._0ZZE,
                    0x1000: self._1ZZZ,
                    0x2000: self._2ZZZ,
                    0x3000: self._3ZZZ,
                    0x4000: self._4ZZZ,
                    0x5000: self._5ZZZ,
                    0x6000: self._6ZZZ,
                    0x7000: self._7ZZZ,
                    0x8000: self._8ZZZ,
                    0x8FF0: self._8ZZ0,
                    0x8FF1: self._8ZZ1,
                    0x8FF2: self._8ZZ2,
                    0x8FF3: self._8ZZ3,
                    0x8FF4: self._8ZZ4,
                    0x8FF5: self._8ZZ5,
                    0x8FF6: self._8ZZ6,
                    0x8FF7: self._8ZZ7,
                    0x8FFE: self._8ZZE,
                    0x9000: self._9ZZZ,
                    0xA000: self._AZZZ,
                    0xB000: self._BZZZ,
                    0xC000: self._CZZZ,
                    0xD000: self._DZZZ,
                    0xE000: self._EZZZ,
                    0xE09E: self._EZZE,   # EX9E: SKP Vx
                    0xE0A1: self._EZZ1,   # EXA1: SKNP Vx
                    0xF000: self._FZZZ,
                    0xF007: self._FZ07,
                    0xF00A: self._FZ0A,
                    0xF015: self._FZ15,
                    0xF018: self._FZ18,
                    0xF01E: self._FZ1E,
                    0xF029: self._FZ29,
                    0xF033: self._FZ33,
                    0xF055: self._FZ55,
                    0xF065: self._FZ65
                    }

    def _0ZZZ(self):
        extracted_op = self.opcode & 0xF0FF
        try: 
            self.funcmap[extracted_op]()
        except:
            print(f"unknown instructions: {self.opcode}")

    def  _0ZZ0(self):
        print(f"clear the screen")
        self.display_buffer = [[0] * 64 for _ in range(32)]
        self.should_draw = True

    def _0ZZE(self):
        print(f"returns from the subroutine")
        self.pc = self.stack.pop();

    def _1ZZZ(self):
        print(f"Jumps to address NNN.")
        self.pc = self.opcode & 0x0FFF

    def _2ZZZ(self):
        print("Calls subroutine at NNN.")
        self.stack.append(self.pc)
        self.pc = self.opcode & 0x0fff
      
    def _3ZZZ(self):
        print("Skips the next instruction if VX equals NN.")
        if self.gpio[self.vx] == (self.opcode & 0x00ff):
            self.pc += 2

    def _4ZZZ(self):
        print("skips the next instruction if vx doesnt equal NN")
        if self.gpio[self.vx] != (self.opcode & 0x00FF):
            self.pc+= 2

    def _5ZZZ(self):
        print("skips next instruction if vx equals vy")
        if self.gpio[self.vx] == self.gpio[self.vy]:
            self.pc+=2

    def _6ZZZ(self):
        print("Sets VX to NN.")
        self.gpio[self.vx] = self.opcode & 0x00ff
    
    def _7ZZZ(self):
        print("Adds NN to VX.")
        self.gpio[self.vx] += (self.opcode & 0xff)
    
    def _8ZZZ(self):
        extracted_op = self.opcode & 0xf00f
        extracted_op += 0xff0
        try:
            self.funcmap[extracted_op]()
        except:
            print(f"unknown instructions: {self.opcode}")
        
    def _8ZZ0(self):
        print("Sets VX to the value of VY.")
        self.gpio[self.vx] = self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
    
    def _8ZZ1(self):  
        print("Sets VX to VX or VY.")
        self.gpio[self.vx] |= self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
        
    def _8ZZ2(self):
        print("Sets VX to VX and VY.")
        self.gpio[self.vx] &= self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
        
    def _8ZZ3(self):
        print("Sets VX to VX xor VY.")
        self.gpio[self.vx] ^= self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
        
    def _8ZZ4(self):
        print("Adds VY to VX. VF is set to 1 when there's a carry, and to 0 when there isn't.")
        if self.gpio[self.vx] + self.gpio[self.vy] > 0xff:
            self.gpio[0xf] = 1
        else:
            self.gpio[0xf] = 0
        self.gpio[self.vx] += self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff

    def _8ZZ5(self):
        print("VY is subtracted from VX. VF is set to 0 when there's a borrow, and 1 when there isn't")
        if self.gpio[self.vy] > self.gpio[self.vx]:
            self.gpio[0xf] = 0
        else:
            self.gpio[0xf] = 1
        self.gpio[self.vx] = self.gpio[self.vx] - self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
        
    def _8ZZ6(self):
        print("Shifts VX right by one. VF is set to the value of the least significant bit of VX before the shift.")
        self.gpio[0xf] = self.gpio[self.vx] & 0x0001
        self.gpio[self.vx] = self.gpio[self.vx] >> 1
        
    def _8ZZ7(self):
        print("Sets VX to VY minus VX. VF is set to 0 when there's a borrow, and 1 when there isn't.")
        if self.gpio[self.vx] > self.gpio[self.vy]:
            self.gpio[0xf] = 0
        else:
            self.gpio[0xf] = 1
        self.gpio[self.vx] = self.gpio[self.vy] - self.gpio[self.vx]
        self.gpio[self.vx] &= 0xff
        
    def _8ZZE(self):
        print("Shifts VX left by one. VF is set to the value of the most significant bit of VX before the shift.")
        self.gpio[0xf] = (self.gpio[self.vx] & 0x80) >> 7
        self.gpio[self.vx] = (self.gpio[self.vx] << 1) & 0xff
        
    def _9ZZZ(self):
        print("Skips the next instruction if VX doesn't equal VY.")
        if self.gpio[self.vx] != self.gpio[self.vy]:
            self.pc += 2
        
    def _AZZZ(self):
        print("Sets I to the address NNN.")
        self.index = self.opcode & 0x0fff
    
    def _BZZZ(self):
        print("Jumps to the address NNN plus V0.")
        self.pc = (self.opcode & 0x0fff) + self.gpio[0]
        
    def _CZZZ(self):
        print("Sets VX to a random number and NN.")
        r = int(random.random() * 0xff)
        self.gpio[self.vx] = r & (self.opcode & 0x00ff)
        self.gpio[self.vx] &= 0xff   

    def _DZZZ(self):
        print("draw a sprite")
        x = self.gpio[self.vx] % 64
        y = self.gpio[self.vy] % 32
        height = self.opcode & 0x000F

        # Reset collision flag before drawing
        self.gpio[0xF] = 0

        for row in range(height):
            sprite_byte = self.memory[self.index + row]
            for col in range(8):
                if sprite_byte & (0x80 >> col):
                    screen_x = (x + col) % 64
                    screen_y = (y + row) % 32

                    if self.display_buffer[screen_y][screen_x] == 1:
                        self.gpio[0xF] = 1  # collision detected

                    # XOR draw pixel
                    self.display_buffer[screen_y][screen_x] ^= 1

        self.should_draw = True

    
    def _EZZZ(self):
        extracted_op = self.opcode & 0xF0FF
        try: 
            self.funcmap[extracted_op]()
        except:
            print(f"unknown instructions: {self.opcode}")

    def _EZZE(self):   
        key = self.gpio[self.vx] & 0xF
        if self.key_inputs[key] == 1:
            self.pc+=2

    def _EZZ1(self):
        key = self.gpio[self.vx] & 0xF
        if self.key_inputs[key] == 0:
            self.pc += 2

    def _FZZZ(self):
        extracted_op = self.opcode & 0xf0ff
        try:
            self.funcmap[extracted_op]()
        except:
            print(f"unknown instructions:{self.opcode:04x}")
        
    def _FZ07(self):
        print("Sets VX to the value of the delay timer.")
        self.gpio[self.vx] = self.delay_timer
    
    def _FZ0A(self):
        print("A key press is awaited, and then stored in VX.")
        ret = self.get_key()
        if ret >= 0:
            self.gpio[self.vx] = ret
        else:
            self.pc -= 2
      
    def _FZ15(self):
        print("Sets the delay timer to VX.")
        self.delay_timer = self.gpio[self.vx]
    
    def _FZ18(self):
        print("Sets the sound timer to VX.")
        self.sound_timer = self.gpio[self.vx]
    
    def _FZ1E(self):
        print("Adds VX to I. if overflow, vf = 1")
        self.index += self.gpio[self.vx]
        if self.index > 0xfff:
            self.gpio[0xf] = 1
            self.index &= 0xfff
        else:
            self.gpio[0xf] = 0
      
    def _FZ29(self):
        print("Set index to point to a character")
        # Sets I to the location of the sprite for the character in VX.
        # Characters 0-F (in hexadecimal) are represented by a 4x5 font.
        self.index = (5*(self.gpio[self.vx])) & 0xfff
        
    def _FZ33(self):
        print("Store a number as BCD")
        # Stores the Binary-coded decimal representation of VX, with the
        # most significant of three digits at the address in I, the middle
        # digit at I plus 1, and the least significant digit at I plus 2.
        self.memory[self.index]   = self.gpio[self.vx] // 100
        self.memory[self.index+1] = (self.gpio[self.vx] % 100) // 10
        self.memory[self.index+2] = self.gpio[self.vx] % 10
        
    def _FZ55(self):
        print("Stores V0 to VX in memory starting at address I.")
        i = 0
        while i <= self.vx:
            self.memory[self.index + i] = self.gpio[i]
            i += 1
        self.index += (self.vx) + 1
        
    def _FZ65(self):
        print("Fills V0 to VX with values from memory starting at address I.")
        i = 0
        while i <= self.vx:
            self.gpio[i] = self.memory[self.index + i]
            i += 1
        self.index += (self.vx) + 1
    # end instructions

    ### FX instructions
    def _FX07(self):
        # LD Vx, DT
        self.gpio[self.vx] = self.delay_timer

    def _FX15(self):
        # LD DT, Vx
        self.delay_timer = self.gpio[self.vx]

    def _FX18(self):
        # LD ST, Vx
        self.sound_timer = self.gpio[self.vx]

    def _FX0A(self):
        # LD Vx, K (wait for key press)
        self.key_wait = True
        self.wait_register = self.vx

    def _FX1E(self):
        # ADD I, Vx
        self.index = (self.index + self.gpio[self.vx]) & 0xFFF
    ###

    def load_rom(self, rom_path):
        print(f"loading ROM {rom_path}...")
        with open(rom_path, "rb") as f:
            binary = f.read()
        for i in range(len(binary)):
            self.memory[i+0x200] = binary[i]

    def cycle(self):
        self.opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.vx = (self.opcode & 0x0F00) >> 8
        self.vy = (self.opcode & 0x00F0) >> 4
        self.pc += 2

        leading = self.opcode & 0xF000
        try:
            self.funcmap[leading]()
        except:
            print(f"unknown instructions: {self.opcode}")

    def render(self):
        self.clear()
        batch = pyglet.graphics.Batch()
        for y in range(32):
            for x in range(64):
                if self.display_buffer[y][x] == 1:
                    pyglet.shapes.Rectangle(
                        x * 10,
                        (31 - y) * 10,   # flip Y so top row is row 0
                        10, 10,
                        color=(0, 0, 0),
                        batch=batch
                    )
        batch.draw()
        self.flip()
        self.should_draw = False

    def get_key(self):
        i = 0
        while i < 16:
            if self.key_inputs[i] == 1:
                return i
            i += 1
        return -1
    
    def on_key_press(self, symbol, modifiers):
        # todo:
        print("Key pressed: %r" % symbol)
        if symbol in KEY_MAP.keys():
            self.key_inputs[KEY_MAP[symbol]] = 1
        if self.key_wait:
            self.key_wait = False
        else:
            super(cpu, self).on_key_press(symbol, modifiers)
        
    def on_key_release(self, symbol, modifiers):
        print("Key released: %r" % symbol)
        if symbol in KEY_MAP.keys():
            self.key_inputs[KEY_MAP[symbol]] = 0

    def update_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
        if self.sound_timer == 0:
            print("BEEP!")


    def main(self):
        self.initialize()
        self.load_rom(sys.argv[1])
        while not self.has_exit:
            self.dispatch_events()
            self.cycle()
            self.update_timers()
            self.render()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chip8.py <rom_file>")
        sys.exit(1)
    chip = cpu()      
    chip.main()          