import kivy
import numpy as np
from random import randint, random
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.label import Label
from kivy.clock import Clock as kivyClock
from kivy.core.window import Window

from kivyparticle import ParticleSystem
from core import BaseWidget, run, lookup
from gfxutil import topleft_label, CEllipse, CRectangle, KFAnim, AnimGroup
from note import NoteGenerator, Envelope
from mixer import Mixer
from audio import Audio

import sys
import os
sys.path.insert(0, os.path.abspath('..'))

# part 1:

# wanted specific colors for notes
pitchDict = {0: (153, 255, 255), 1: (77, 255, 219), 2: (0, 204, 102), 3: (217, 255, 102), 4: (255, 224, 102), 5: (255, 191, 128), 6: (
    255, 153, 102), 7: (255, 128, 128), 8: (217, 140, 179), 9: (204, 153, 255), 10: (128, 128, 255), 11: (153, 206, 255), 12: (153, 255, 254)}
for item in pitchDict:
    pitchDict[item] = (pitchDict[item][0]/256, pitchDict[item]
                       [1]/256, pitchDict[item][2]/256)
reversed_pitchDict = {value: key for (key, value) in pitchDict.items()}


class MelodyNote(InstructionGroup):
    # Shape object of a single note
    def __init__(self, pitch, rootPitch, duration, prevNote=None):
        super(MelodyNote, self).__init__()

        # make the shape a color that corresponds to pitch

        # how long it takes for notes to go off screen
        self.lifetime = duration*10
        self.pitch = pitch

        # save it to draw lines
        self.prevNote = prevNote

        # Let y position of start depend on pitch
        self.pos = (Window.width-5, Window.height/23*(pitch+6))

        # drawing a line between notes
        if self.prevNote != None:
            self.add(self.prevNote.color)
            self.line = Line(points=(
                self.pos[0], self.pos[1], self.prevNote.pos[0], self.prevNote.pos[1]), width=1)
            self.add(self.line)

        # drawing shape
        self.color = Color(*pitchDict[(pitch+rootPitch) % 12])
        self.add(self.color)
        self.size = 50
        self.shape = CEllipse(cpos=self.pos, csize=(self.size, self.size))

        self.add(self.shape)

        self.secondcolor = Color(0, 0, 0)
        self.secondcolor.a = 0

        self.add(self.secondcolor)
        # making shape fill disappear
        self.secondshape = CEllipse(
            cpos=self.pos, csize=(self.size-3, self.size-3))
        self.add(self.secondshape)

        self.pos_anim = KFAnim((0, self.shape.cpos),
                               (self.lifetime, self.shape.cpos))

        self.time = 0
        self.on_update(0)

    def printInfo(self):
        # prints the info of an object for debuggiung:
        info = str(pitchDict[self.pitch])
        info += '\npitch: %d' % self.pitch
        info += '\nsize: %d' % self.size
        info += '\nduration: %d' % self.lifetime
        info += '\ntime: %d' % self.time
        info += '\nposition:' + str(self.pos)

        return info

    def on_update(self, dt):

        # make size grow until note ends, then shrink slowly
        if self.time < self.lifetime/10:
            newsize = (self.shape.csize[0]+0.25, self.shape.csize[1]+.25)
            self.shape.csize = newsize
            self.secondshape.csize = (newsize[0]-3, newsize[1]-3)
            self.size = newsize[0]
        else:
            newsize = ((self.size-.75*self.time*self.size/self.lifetime)
                       * 1.1, (self.size-.75*self.time*self.size/self.lifetime)*1.1,)
            self.shape.csize = newsize
            self.secondshape.csize = (newsize[0]-3, newsize[1]-3)

        # fading out the alpha
        self.color.a = self.color.a - .5/(self.lifetime*kivyClock.get_fps())
        self.secondcolor.a = self.secondcolor.a + \
            (self.time-self.lifetime/20)/self.lifetime*0.05

        # moves to the left
        newpos = (self.pos[0]-(Window.width /
                  (self.lifetime*kivyClock.get_fps())), self.pos[1])
        self.pos = newpos
        self.shape.cpos = newpos
        self.secondshape.cpos = newpos

        if self.prevNote != None:
            self.line.points = (
                (self.pos[0], self.pos[1], self.prevNote.pos[0], self.prevNote.pos[1]))

        self.time += dt
        return self.pos_anim.is_active(self.time)


class MainWidget1(BaseWidget):
    def __init__(self):
        super(MainWidget1, self).__init__()

        self.audio = Audio(2)
        self.mixer = Mixer()
        self.mixer.set_gain(0.2)
        self.audio.set_generator(self.mixer)

        self.root_pitch = 48
        self.gain = .75
        self.attack = 0.01
        self.decay = 1.0
        self.toRemove = {}

        self.info = topleft_label()
        self.add_widget(self.info)

        # animation stuff
        self.anim_group = AnimGroup()
        self.canvas.add(self.anim_group)
        self.noteinfo = ''

        self.prevNote = None

        self.triadlist = []

    def on_update(self):

        self.audio.on_update()
        self.anim_group.on_update()

        #self.info.text = 'load: %.2f\n' % self.audio.get_cpu_load()
        #self.info.text += 'gain: %.2f\n' % self.gain
        self.info.text = 'root note: %s\n' % self.root_pitch
        #self.info.text += '\nfps:%d' % kivyClock.get_fps()
        #self.info.text += '\nobjects:%d' % len(self.anim_group.objects)
        #self.info.text += '\n noteinfo'+self.noteinfo

    def on_key_down(self, keycode, modifiers):
        # trigger a major triad to play with left hand keys
        print('key-down', keycode, modifiers)
        majorbase = lookup(keycode[1], 'qwerty', (0, 2, 4, 5, 7, 9,))
        if majorbase is not None:
            majorbase = majorbase+self.root_pitch
            triad = [majorbase, majorbase+4, majorbase+7]
            removelist = []
            for i in range(len(triad)):
                note = triad[i]
                if i == 0:
                    newnote = NoteGenerator(note, 0.75, 'square')
                else:
                    newnote = NoteGenerator(note, 0.25, 'square')
                #env = Envelope(newnote, self.attack, 1, self.decay, 2)
                removelist.append(newnote)
                self.mixer.add(newnote)
            self.toRemove[keycode[1]] = removelist

            self.triadlist.append(1)

        # trigger a minor triad to play with left hand keys
        minorbase = lookup(keycode[1], 'asdf', (2, 4, 9, 11))
        if minorbase is not None:
            minorbase = minorbase+self.root_pitch
            triad = [minorbase, minorbase+3, minorbase+7]
            removelist = []
            for i in range(len(triad)):
                note = triad[i]
                if i == 0:
                    newnote = NoteGenerator(note, 0.75, 'square')
                else:
                    newnote = NoteGenerator(note, 0.25, 'square')
                #env = Envelope(newnote, self.attack, 1, self.decay, 2)
                removelist.append(newnote)
                self.mixer.add(newnote)
            self.toRemove[keycode[1]] = removelist

            self.triadlist.append(1)

        # triggering melody notes with key presses
        melody = lookup(keycode[1], 'cvgbhnjmk,l.;',
                        (-5, -3, -1, 0, 2, 4, 5, 7, 9, 11, 12, 14, 16))
        if melody is not None:

            newNote = MelodyNote(melody, self.root_pitch,
                                 self.decay, self.prevNote)
            self.anim_group.add(newNote)
            self.prevNote = newNote
            melody = melody+self.root_pitch+12
            newnote = NoteGenerator(melody, 0.9, 'square')
            env = Envelope(newnote, self.attack, 1, self.decay, 2)
            self.mixer.add(env)

        # changing the base pitch
        base_sel = lookup(keycode[1], ('up', 'down'), (1, -1))
        if base_sel is not None:
            self.root_pitch += base_sel

    def on_key_up(self, keycode,):
        # release held triads

        if keycode[1] in 'qwertyasdf':
            self.triadlist.remove(1)

        if keycode[1] in self.toRemove:
            for gen in self.toRemove[keycode[1]]:
                self.mixer.remove(gen)

            del self.toRemove[keycode[1]]


class MainWidget2(BaseWidget):
    def __init__(self):
        super(MainWidget2, self).__init__()

        self.root_pitch = 48
        self.gain = .75
        self.attack = 0.01
        self.decay = 1.0
        self.toRemove = {}

        self.info = topleft_label()
        self.add_widget(self.info)

        # animation stuff
        self.anim_group = AnimGroup()
        self.canvas.add(self.anim_group)
        self.noteinfo = ''

        self.prevNote1 = None
        self.prevNote2 = None

    def on_update(self):

        self.anim_group.on_update()

        #self.info.text = 'load: %.2f\n' % self.audio.get_cpu_load()
        #self.info.text += 'gain: %.2f\n' % self.gain
        self.info.text = 'root note: %s\n' % self.root_pitch
        #self.info.text += '\nfps:%d' % kivyClock.get_fps()
        #self.info.text += '\nobjects:%d' % len(self.anim_group.objects)
        #self.info.text += '\n noteinfo'+self.noteinfo

    def on_key_down(self, keycode, modifiers):
        # trigger a major triad to play with left hand keys
        print('key-down', keycode, modifiers)

        # triggering melody notes with key presses
        part1 = lookup(keycode[1], 'cvgbhnjmk,l.;',
                       (-5, -3, -1, 0, 2, 4, 5, 7, 9, 11, 12, 14, 16))
        if part1 is not None:

            newNote = MelodyNote(part1, self.root_pitch,
                                 self.decay, self.prevNote1)
            self.anim_group.add(newNote)
            self.prevNote1 = newNote

        part2 = lookup(keycode[1], 'qazwsx',
                       (-5, -3, -1, 0, 2, 4,))

        if part2 is not None:

            newNote2 = MelodyNote(part2, self.root_pitch,
                                  self.decay, self.prevNote2)
            self.anim_group.add(newNote2)
            self.prevNote2 = newNote2

        # changing the base pitch
        base_sel = lookup(keycode[1], ('up', 'down'), (1, -1))
        if base_sel is not None:
            self.root_pitch += base_sel


if __name__ == "__main__":
    # to run, on the command line, type: python visuals.py 1
    run(eval('MainWidget' + sys.argv[1])())
