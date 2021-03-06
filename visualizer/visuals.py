
import numpy as np
import pickle
from random import randint, random
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.label import Label
from kivy.clock import Clock as kivyClock
from kivy.core.window import Window

from core import BaseWidget, run, lookup
from gfxutil import topleft_label, CEllipse, KFAnim, AnimGroup
from mixer import Mixer
from wavegen import WaveGenerator
from wavesrc import WaveFile
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
    def __init__(self, pitch, rootPitch, duration, color, prevNote=None,):
        super(MelodyNote, self).__init__()

        # make the shape a color that corresponds to pitch

        # how long it takes for notes to go off screen
        self.lifetime = duration*10
        self.pitch = pitch

        # save it to draw lines
        self.prevNote = prevNote

        # Let y position of start depend on pitch
        self.pos = (Window.width-5, Window.height/37*(pitch+18))

        # drawing a line between notes
        if self.prevNote != None:
            self.add(self.prevNote.color)
            self.line = Line(points=(
                self.pos[0], self.pos[1], self.prevNote.pos[0], self.prevNote.pos[1]), width=1)
            self.add(self.line)

        # drawing shape
        #self.color = Color(*pitchDict[(pitch+rootPitch) % 12])
        self.color = Color(*color)
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
        self.color.a = self.color.a - .5/(self.lifetime*kivyClock.get_fps()+1)
        self.secondcolor.a = self.secondcolor.a + \
            (self.time-self.lifetime/20)/self.lifetime*0.05

        # moves to the left
        newpos = (self.pos[0]-(Window.width /
                  (self.lifetime*kivyClock.get_fps()+1)), self.pos[1])
        self.pos = newpos
        self.shape.cpos = newpos
        self.secondshape.cpos = newpos

        if self.prevNote != None:
            self.line.points = (
                (self.pos[0], self.pos[1], self.prevNote.pos[0], self.prevNote.pos[1]))

        self.time += dt
        return self.pos_anim.is_active(self.time)


# Handles everything about Audio.
#   creates the main Audio object
#   load and plays solo and bg audio tracks
#   creates audio buffers for sound-fx (miss sound)
#   functions as the clock (returns song time elapsed)


class AudioController(object):
    def __init__(self, solo):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        # song
        self.solo = WaveGenerator(WaveFile(solo))
        self.mixer.add(self.solo)

        self.solo.pause()

    def toggle(self):
        self.solo.play_toggle()

    # return current time (in seconds) of song
    def get_time(self):
        return self.solo.frame / Audio.sample_rate

    # needed to update audio
    def on_update(self):
        self.audio.on_update()


class MainWidget1(BaseWidget):
    def __init__(self):
        super(MainWidget1, self).__init__()

        self.folder = 'haydn'
        self.audio_ctrl = AudioController(self.folder+'/corpus_audio.wav')
        self.root_pitch = 48

        self.decay = 1.0

        self.info = topleft_label()
        self.add_widget(self.info)

        # animation stuff
        self.anim_group = AnimGroup()
        self.canvas.add(self.anim_group)
        #self.noteinfo = ''

        self.prevNote1 = None
        self.prevNote2 = None
        self.prevNote3 = None
        self.prevNote4 = None

        self.index1 = 0
        self.index2 = 0
        self.index3 = 0
        self.index4 = 0

        open_file = open(self.folder+'/soprano.pickle', "rb")
        self.part1 = pickle.load(open_file)
        open_file.close()

        open_file = open(self.folder+'/alto.pickle', "rb")
        self.part2 = pickle.load(open_file)
        open_file.close()

        open_file = open(self.folder+'/tenor.pickle', "rb")
        self.part3 = pickle.load(open_file)
        open_file.close()

        open_file = open(self.folder+'/bass.pickle', "rb")
        self.part4 = pickle.load(open_file)
        open_file.close()

        self.part1.sort(key=lambda a: a[0])
        self.part2.sort(key=lambda a: a[0])
        self.part3.sort(key=lambda a: a[0])
        self.part4.sort(key=lambda a: a[0])

        self.part1 = [(x[0]+3, x[1]) for x in self.part1]
        self.part2 = [(x[0]+3, x[1]) for x in self.part2]
        self.part3 = [(x[0]+3, x[1]) for x in self.part3]
        self.part4 = [(x[0]+3, x[1]) for x in self.part4]

    def on_update(self):

        self.info.text = 'root note: %s\n' % self.root_pitch

        self.info.text += str(kivyClock.get_time())

        time = kivyClock.get_time()

        r = abs(np.sin(time/10))
        g = abs(np.sin(time/10+2))
        b = abs(np.sin(time/10+4))

        if self.index1 < len(self.part1) and time >= self.part1[self.index1][0]:

            if self.part1[self.index1][1] == -1:
                self.prevNote1 = None

            else:
                newNote1 = MelodyNote(self.part1[self.index1][1]-58, self.root_pitch,
                                      self.decay, (r, g, b), self.prevNote1)

                self.anim_group.add(newNote1)
                self.prevNote1 = newNote1
            self.index1 += 1

        if self.index2 < len(self.part2) and time >= self.part2[self.index2][0]:
            if self.part2[self.index2][1] == -1:
                self.prevNote2 = None

            else:
                newNote2 = MelodyNote(self.part2[self.index2][1]-58, self.root_pitch,
                                      self.decay, (g, b, r),  self.prevNote2)
                self.anim_group.add(newNote2)
                self.prevNote2 = newNote2
            self.index2 += 1

        if self.index3 < len(self.part3) and time >= self.part3[self.index3][0]:
            if self.part3[self.index3][1] == -1:
                self.prevNote3 = None

            else:
                newNote3 = MelodyNote(self.part3[self.index3][1]-58, self.root_pitch,
                                      self.decay, (b, r, g), self.prevNote3)
                self.anim_group.add(newNote3)
                self.prevNote3 = newNote3
            self.index3 += 1

        if self.index4 < len(self.part4) and time >= self.part4[self.index4][0]:
            if self.part4[self.index4][1] == -1:
                self.prevNote4 = None

            else:
                newNote4 = MelodyNote(self.part4[self.index4][1]-58, self.root_pitch,
                                      self.decay, (g, r, b), self.prevNote4)
                self.anim_group.add(newNote4)
                self.prevNote4 = newNote4
            self.index4 += 1

        self.anim_group.on_update()
        self.audio_ctrl.on_update()

    def on_key_down(self, keycode, modifiers):
        # trigger a major triad to play with left hand keys
        print('key-down', keycode, modifiers)

        # triggering melody notes with key presses
        if keycode[1] == 'p':
            self.audio_ctrl.toggle()


if __name__ == "__main__":
    # to run, on the command line, type: python visuals.py 1
    run(eval('MainWidget' + sys.argv[1])())
