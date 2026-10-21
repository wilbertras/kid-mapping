from ppadb.client import Client as AdbClient
import matplotlib.pyplot as plt
from datetime import datetime
import functions as ft
from copy import copy
import tkinter as tk
import numpy as np
import itertools
import pyvisa
import pygame
import time
import json
import sys
import os


class Mapping:
    def __init__(self, name):
        self.name = name
        self.add_scans()
        self.add_phone()
        self.add_vna()

    def mirror(self, scrcpy="scrcpy-win64-v211\scrcpy.exe"):
        os.startfile(scrcpy)

    def add_fsweep(self, fstart, fstop, subscanbw, num_points, kidpower, ifbw, calfile=False):
        self.fstart = fstart
        self.fstop = fstop
        self.subscanbw = subscanbw
        self.num_points = num_points
        self.kidpower = kidpower
        self.ifbw = ifbw
        self.calfile = calfile
        print('fsweep: %.1f-%.1f GHz, %d MHz scans with %d points, %d dBm, %d IFBW' % (self.fstart, self.fstop, self.subscanbw, self.num_points, self.kidpower, self.ifbw))

    def add_scans(self, xstart=None, xsteps=[], ystart=None, ysteps=[]):
        self.xstart = xstart
        self.xsteps = xsteps
        self.ystart = ystart
        self.ysteps = ysteps
        self.nr_xsteps = len(self.xsteps)
        self.nr_ysteps = len(self.ysteps)
        print('scans: %d in X, %d in Y' % (self.nr_xsteps, self.nr_ysteps))

    def add_phone(self, host="127.0.0.1", port=5037, id=0):
        self.host = host
        self.port = port
        self.id = id
        self.client = AdbClient(host=self.host, port=self.port)
        self.devices  = self.client.devices()
        if len(self.devices):
            self.device = self.devices[self.id]
            print('phone: %s' % self.device)
        else:
            print('WARNING: no ADB devices found')
            self.device = None

    def add_vna(self, GPIB_vna="GPIB0::16::INSTR", GPIB_weinschell="GPIB0::10::INSTR", timeout=3000000):
        self.GPIB_vna = GPIB_vna
        self.GPIB_weinschell = GPIB_weinschell
        self.timeout = timeout
        self.vna = self.connect2vi(self.GPIB_vna)
        if self.vna:
            print('VNA: ', self.vna) % self.vna
        self.weinschell = self.connect2vi(self.GPIB_weinschell)
        if self.weinschell:
            print('Weinschell: ', self.weinschell)
        
    def connect2vi(self, GPIB):
        try:
            rm = pyvisa.ResourceManager() 
            vi = rm.open_resource(GPIB)
            vi.timeout = self.timeout
            vi.query('*IDN?')
        except:
            print('WARNING: %s not found' % GPIB)
            vi = None
        return vi
    
    def sweep(self):
        if self.vna and self.weinschell:
            return ft.get_s21(self.vna, self.weinschell, self.fstart, self.fstop, self.subscanbw, self.num_points, self.kidpower, self.ifbw, self.calibfile)
        elif (not self.vna) or (not self.weinschell) and self.test:
            return [], []
        else:
            print("WARNING: sweep not made because no VNA connected")

    def adb(self, val):
        if self.device:
            self.device.shell(val)
        elif (not self.device) and self.test:
            print(val)
        else:
            print("WARNING: command not send because no phone connected")

    def read_battery(self):
        if self.device:
            output = self.device.shell("dumpsys battery")
            battery_level = '??'
            for line in output.splitlines():
                if "level" in line:
                    battery_level = str(int(line.split(":")[1].strip()))
            return battery_level   
        elif (not self.device) and self.test:
            return 'test'  
        else:
            print("WARNING: no ADB device")
            return '??'
    
    def reboot(self):
        answer = input("Are you sure? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            self.adb("reboot -p")
        else:
            print("Cancelled.")

    def timestamp(self):
        year = datetime.now().year
        month = datetime.now().month
        day = datetime.now().day
        hour = datetime.now().hour
        minute = datetime.now().minute
        return '_%d%02d%02d_%02dh%02d' % (year, month, day, hour, minute)

    def create_directory(self, base_name):
        dir_name = base_name
        counter = 1
        while os.path.exists(dir_name):
            dir_name = f"{base_name}({counter})"
            counter += 1
        os.makedirs(dir_name)
        return dir_name

    def select_directory(self, initial_dir=None):
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        if not initial_dir:
            initial_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current file
        selected_dir = tk.filedialog.askdirectory(title="Select Directory", initialdir=initial_dir)
        root.destroy()
        return selected_dir

    def start(self, test=False):
        self.test = test
        pygame.init()
        colors = {
            'white': (255, 255, 255),
            'blue': (0, 0, 255),
            'green': (0, 255, 0),
            'red': (255, 0, 0),
            'black': (0, 0, 0)
        }
        colorkeys = ['white', 'blue', 'green', 'red']
        colorkey_cycler = itertools.cycle(colorkeys)
        linecolor = next(colorkey_cycler)
        bgcolor = 'black'

        width, height = 700, 720
        column_width = width // 2
        small_box_height = height // 8
        big_box_height = height // 6
        small_font_size = 25
        big_font_size = 25
        screen = pygame.display.set_mode((width, height))

        def draw_text_boxes(text_list, bgcolor, linecolor):
            y=0
            for i, text in enumerate(text_list):
                row = i // 2
                col = i % 2
                if row==0:
                    BOX_height = big_box_height
                    font_size = big_font_size
                    y = 0
                else:
                    y = big_box_height + (row-1)*big_box_height
                    BOX_height = big_box_height
                    font_size = big_font_size
                x = col * column_width
                pygame.draw.rect(screen, bgcolor, (x, y, column_width, BOX_height), 0)
                pygame.draw.rect(screen, linecolor, (x, y, column_width, BOX_height), 1)
                # Split the text into two lines
                lines = text.split('\n')
                
                # Render each line of text
                for j, line in enumerate(lines):
                    if len(lines) > 2:
                        if (j==0) or (j==1 and len(lines)==3) :
                            font_size = big_font_size
                        else:
                            font_size = small_font_size
                    FONT = pygame.font.Font(None, font_size)
                    text_surface = FONT.render(line, True, linecolor)
                    text_rect = text_surface.get_rect(center=(x + column_width // 2, y + ((j-1) * font_size) + (BOX_height // 2)))
                    screen.blit(text_surface, text_rect)
        

        screen_width = 1440
        screen_height = 3216
        x_centre = int(screen_width / 2)
        y_centre = int(screen_height / 2)
        length_line_mm = 50
        pxl_mm = 0.06
        length_line_pxl = int(length_line_mm / pxl_mm)
        half_length = int(length_line_pxl / 2)
        y_min = y_centre - half_length
        y_max = y_centre + half_length
        x_min = x_centre - half_length
        x_max = x_centre + half_length
        x_init = x_centre
        y_init = y_centre
        dx_init = 10
        dx_min = 1
        dy_min = 1
        dy_init = 10
        w_init = 5
        w_min = 1
        step = 1

        ## Initiate scanning paramaters
        running = True
        nr_y2scan = len(self.ysteps)
        nr_x2scan = len(self.xsteps)
        nr_xscanned = 0
        nr_yscanned = 0
        w = w_init
        x = x_init
        y = y_init
        dx = dx_init
        dy = dy_init
        restart = True
        false_true = [False, True]
        inverted_cycler = itertools.cycle(false_true)
        inverted = next(inverted_cycler)
        measure = False
        wait = 1
        wait_before_scan = 500
        linetypes = ['both', 'none', 'x', 'y']
        linetype_cycler = itertools.cycle(linetypes)
        linetype = next(linetype_cycler)
        square_cycler = itertools.cycle(false_true)
        square = next(square_cycler)
        datadir = None

        while running:
            if restart:
                self.adb("input keyevent 67")
                pygame.time.wait(wait)
                restart = 0

            text_list = [
            'Position (X, Y)\n(%d, %d)\n Move : up,down,left,right' % (x, y),
            'Linewidth W\n%d\n -1/=1/+1 : Q/W/E' % w,
            'Stepsize dX\n%d\n -1/=1/+1 : Z/X/C' % dx,
            'Stepsize dY\n%d\n -1/=1/+1 : T/Y/U' % dy,
            '# to scan (#X, #Y)\n(%d, %d)' % (nr_x2scan, nr_y2scan),
            'Add scan : L \n only works single line or square',
            'Invert screen : I',
            'Switch lines-square : S',
            'Change color : G \nCycles White-Blue-Green-Red-Off',
            'Scanned (#X, #Y)\n(%d, %d)' % (nr_xscanned, nr_yscanned),
            'Reset : Backspace',
            'Quit : Esc',
            ]
            screen.fill(colors[bgcolor])
            draw_text_boxes(text_list, colors[bgcolor], colors[linecolor])
            
            if measure:
                battery = self.read_battery()
                if square:
                    if nr_xscanned < nr_x2scan and nr_yscanned < nr_y2scan and nr_x2scan > 0 and nr_y2scan > 0:
                        while linetype != 'both':
                            self.adb("input keyevent KEYCODE_B")
                            linetype = next(linetype_cycler)
                        pygame.time.wait(wait)
                        xstep = self.xsteps[nr_xscanned]
                        ystep = self.ysteps[nr_yscanned]
                        print('Scan %d/%d, stepping %d in X and %d in Y' % (nr_xscanned+1, nr_x2scan, xstep, ystep))
                        if xstep > 0:
                            for i in range(xstep):
                                self.adb("input keyevent KEYCODE_DPAD_RIGHT")
                                pygame.time.wait(wait)
                                x += 1
                        elif xstep < 0:
                            for i in range(-xstep):
                                self.adb("input keyevent KEYCODE_DPAD_LEFT")
                                pygame.time.wait(wait)
                                x -= 1
                        else:
                            pass
                        if ystep > 0:
                            for i in range(ystep):
                                self.adb("input keyevent KEYCODE_DPAD_UP")
                                pygame.time.wait(wait)
                                y += 1
                        elif ystep < 0:
                            for i in range(-ystep):
                                self.adb("input keyevent KEYCODE_DPAD_DOWN")
                                pygame.time.wait(wait)
                                y -= 1
                        else:
                            pass
                        pygame.time.wait(wait_before_scan)
                        freqs, s21 = self.sweep()
                        name = '%s/S21_x%02d_y%02d_%s%%.npy' % (datadir, nr_xscanned, nr_yscanned, battery)
                        np.save(name, np.stack((freqs, s21), axis=-1).T)
                        nr_xscanned += 1
                        nr_yscanned += 1
                    elif nr_xscanned == nr_x2scan and nr_yscanned == nr_y2scan:
                        measure = 0
                        while linetype != 'both':
                            self.adb("input keyevent KEYCODE_B")
                            linetype = next(linetype_cycler)
                        pygame.time.wait(wait)
                        print('Helemaal f*cking klaar met de meting')
                    else:
                        measure = 0
                        self.adb("input keyevent KEYCODE_B")
                        print('WARNING: Measurement stopped but might not be complete')
                else:
                    if nr_xscanned < nr_x2scan and nr_x2scan > 0 and nr_yscanned == 0:
                        while linetype != 'x':
                            self.adb("input keyevent KEYCODE_B")
                            linetype = next(linetype_cycler)
                        pygame.time.wait(wait)
                        xstep = self.xsteps[nr_xscanned]
                        print('Scan %d/%d, stepping %d' % (nr_xscanned+1, nr_x2scan, xstep))
                        if xstep > 0:
                            for i in range(xstep):
                                self.adb("input keyevent KEYCODE_DPAD_RIGHT")
                                pygame.time.wait(wait)
                                x += 1
                        elif xstep < 0:
                            for i in range(-xstep):
                                self.adb("input keyevent KEYCODE_DPAD_LEFT")
                                pygame.time.wait(wait)
                                x -= 1
                        else:
                            pass
                        pygame.time.wait(wait_before_scan)
                        freqs, s21 = self.sweep()
                        name = '%s/S21_x%02d_%s%%.npy' % (datadir, nr_xscanned, battery)
                        np.save(name, np.stack((freqs, s21), axis=-1).T)
                        nr_xscanned += 1
                    elif nr_xscanned == nr_x2scan and nr_yscanned < nr_y2scan and nr_y2scan > 0:
                        while linetype != 'y':
                            self.adb("input keyevent KEYCODE_B")
                            linetype = next(linetype_cycler)
                        pygame.time.wait(wait)
                        ystep = self.ysteps[nr_yscanned]
                        print('Scan %d/%d, stepping %d' % (nr_yscanned+1, nr_y2scan, ystep))
                        if ystep > 0:
                            for i in range(ystep):
                                self.adb("input keyevent KEYCODE_DPAD_UP")
                                pygame.time.wait(wait)
                                y += 1
                        elif ystep < 0:
                            for i in range(-ystep):
                                self.adb("input keyevent KEYCODE_DPAD_DOWN")
                                pygame.time.wait(wait)
                                y -= 1
                        else:
                            pass
                        pygame.time.wait(wait_before_scan)
                        freqs, s21 = self.sweep()
                        name = '%s/S21_y%02d_%s%%.npy' % (datadir, nr_yscanned, battery)
                        np.save(name, np.stack((freqs, s21), axis=-1).T)
                        nr_yscanned += 1
                    elif nr_xscanned == nr_x2scan and nr_yscanned == nr_y2scan:
                        measure = 0
                        while linetype != 'both':
                            self.adb("input keyevent KEYCODE_B")
                            linetype = next(linetype_cycler)
                        pygame.time.wait(wait)
                        print('Helemaal f*cking klaar met de meting')
                    else:
                        measure = 0
                        self.adb("input keyevent KEYCODE_B")
                        print('WARNING: Measurement stopped but might not be complete')

            event = pygame.event.poll()

            if event.type == pygame.QUIT:
                running = 0 

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = 0
                if event.key == pygame.K_BACKSPACE:
                    self.adb("67")
                    pygame.time.wait(wait)
                    x = x_init
                    y = y_init
                    w = w_init
                    dx = dx_init
                    dy = dy_init
                    colorkey_cycler = itertools.cycle(colorkeys)
                    bgcolor = 'black'
                    linecolor = next(colorkey_cycler)
                    linetype_cycler = itertools.cycle(linetypes)
                    linetype = next(linetype_cycler)
                    inverted_cycler = itertools.cycle(false_true)
                    inverted = next(inverted_cycler)
                    square_cycler = itertools.cycle(false_true)
                    square = next(square_cycler)

                if event.key == pygame.K_DOWN:
                    if linetype == 'y' or linetype == 'both':
                        self.adb("input keyevent KEYCODE_DPAD_DOWN")
                        pygame.time.wait(wait)
                        y -= dy
                        if y < y_min:
                            y = y_min
                if event.key == pygame.K_UP:
                    if linetype == 'y' or linetype == 'both':
                        self.adb("input keyevent KEYCODE_DPAD_UP")
                        pygame.time.wait(wait)
                        y += dy
                        if y > y_max:
                            y = y_max
                if event.key == pygame.K_RIGHT:
                    if linetype == 'x' or linetype == 'both':
                        self.adb("input keyevent KEYCODE_DPAD_RIGHT")
                        pygame.time.wait(wait)
                        x += dx
                        if x > x_max:
                            x = x_max
                if event.key == pygame.K_LEFT:
                    if linetype == 'x' or linetype == 'both':
                        self.adb("input keyevent KEYCODE_DPAD_LEFT")
                        pygame.time.wait(wait)
                        x -= dx
                        if x < x_min:
                            x = x_min
                if event.key == pygame.K_e:
                    self.adb("input keyevent KEYCODE_E")
                    pygame.time.wait(wait)
                    w += step
                if event.key == pygame.K_q:
                    self.adb("input keyevent KEYCODE_Q")
                    pygame.time.wait(wait)
                    w -= step
                    if w < w_min:
                        w = w_min
                if event.key == pygame.K_c:
                    self.adb("input keyevent KEYCODE_C")
                    pygame.time.wait(wait)
                    dx += step
                if event.key == pygame.K_z:
                    self.adb("input keyevent KEYCODE_Z")
                    pygame.time.wait(wait)
                    dx -= step
                    if dx < dx_min:
                        dx = dx_min
                if event.key == pygame.K_u:
                    self.adb("input keyevent KEYCODE_U")
                    pygame.time.wait(wait)
                    dy += step
                if event.key == pygame.K_t:
                    self.adb("input keyevent KEYCODE_T")
                    pygame.time.wait(wait)
                    dy -= step
                    if dy < dy_min:
                        dy = dy_min
                if event.key == pygame.K_x:
                    self.adb("input keyevent KEYCODE_X")
                    pygame.time.wait(wait)
                    dx = 1
                if event.key == pygame.K_y:
                    self.adb("input keyevent KEYCODE_Y")
                    pygame.time.wait(wait)
                    dy = 1
                if event.key == pygame.K_w:
                    self.adb("input keyevent KEYCODE_W")
                    pygame.time.wait(wait)
                    w = 1
                if event.key == pygame.K_i:
                    self.adb("input keyevent KEYCODE_I")
                    pygame.time.wait(wait)
                    current_linecolor = copy(linecolor)
                    current_bgcolor = copy(bgcolor)
                    bgcolor = current_linecolor
                    linecolor = current_bgcolor
                    inverted = next(inverted_cycler)
                if event.key == pygame.K_g:
                    self.adb("input keyevent KEYCODE_G")
                    pygame.time.wait(wait)
                    if inverted:
                        bgcolor = next(colorkey_cycler)
                        linecolor = 'black'
                    else:
                        bgcolor = 'black'
                        linecolor = next(colorkey_cycler)
                if event.key == pygame.K_b:
                    self.adb("input keyevent KEYCODE_B")
                    linetype = next(linetype_cycler)
                    pygame.time.wait(wait)
                if event.key == pygame.K_l:
                    if square:
                        if not len(self.xsteps) and not len(self.ysteps):
                            self.xsteps.append(0)
                            self.ysteps.append(0)
                            self.xstart = copy(int(x))
                            self.ystart = copy(int(y))
                            xprev = copy(int(x))
                            yprev = copy(int(y))
                        else:
                            if int(x - xprev) or int(y - yprev):
                                self.xsteps.append(int(x - xprev))
                                self.ysteps.append(int(y - yprev))
                                xprev = copy(x)
                                yprev = copy(y)
                        print('xstart = ', self.xstart, '# %d xsteps' % (len(self.xsteps)))
                        print('xsteps = ', self.xsteps)
                        print('ystart = ', self.ystart, '# %d ysteps' % (len(self.ysteps)))
                        print('ysteps = ', self.ysteps)
                    else:
                        if linetype == 'x':
                            if not len(self.xsteps):
                                self.xsteps.append(0)
                                self.xstart = copy(int(x))
                                xprev = copy(int(x))
                            else:
                                if int(x - xprev):
                                    self.xsteps.append(int(x - xprev))
                                    xprev = copy(x)
                            print('xstart = ', self.xstart, '# %d xsteps' % (len(self.xsteps)))
                            print('xsteps = ', self.xsteps)
                        elif linetype == 'y':
                            if not len(self.ysteps):
                                self.ysteps.append(0)
                                self.ystart = copy(int(y))
                                yprev = copy(int(y))
                            else:
                                if int(y - yprev):
                                    self.ysteps.append(int(y - yprev))
                                    yprev = copy(y)
                            print('ystart = ', self.ystart, '# %d ysteps' % (len(self.ysteps)))
                            print('ysteps = ', self.ysteps)
                        else:
                            print('WARNING: steps can only be added when having a single line either in x or y')
                            print('xstart = ', self.xstart, '# %d xsteps' % (len(self.xsteps)))
                            print('xsteps = ', self.xsteps)
                            print('ystart = ', self.ystart, '# %d ysteps' % (len(self.ysteps)))
                            print('ysteps = ', self.ysteps)
                if event.key == pygame.K_s:
                    self.adb("input keyevent KEYCODE_S")
                    square = next(square_cycler)
                    pygame.time.wait(wait)
                if event.key == pygame.K_m:
                    datadir = ft.select_directory(initial_dir=datadir)
                    if datadir:
                        print(f"Selected directory: {datadir}")
                    freqs, s21 = self.sweep()
                    date = ft.timestamp()
                    name = '%s/S21_x%dy%d_w%d.npy' % (datadir, x, y, w)
                    np.save(name, np.stack((freqs, s21), axis=-1).T)
                    print('Saved: %s' % (name))
                if event.key == pygame.K_RETURN:
                        if inverted:
                            print('WARNING: screen is inverted')
                        elif not len(self.xsteps) and not len(self.ysteps): 
                            print('WARNING: no steps in X and Y')
                        else:
                            measure = 1
                            nr_x2scan = len(self.xsteps)
                            nr_y2scan = len(self.ysteps)
                            nr_xscanned = 0
                            nr_yscanned = 0
                            if square:
                                pass
                            else:
                                while linetype != 'both':
                                    self.adb("input keyevent KEYCODE_B")
                                    linetype = next(linetype_cycler)
                            pygame.time.wait(wait)
                            self.adb("input keyevent KEYCODE_X")
                            dx = 1
                            self.adb("input keyevent KEYCODE_Y")
                            dy = 1
                            if nr_x2scan and self.xstart:
                                while x > self.xstart:
                                    self.adb("input keyevent KEYCODE_DPAD_LEFT")
                                    x -= dx
                                while x < self.xstart:
                                    self.adb("input keyevent KEYCODE_DPAD_RIGHT")
                                    x += dx
                            if nr_y2scan and self.ystart:
                                while y > self.ystart:
                                    self.adb("input keyevent KEYCODE_DPAD_DOWN")
                                    y -= dy
                                while y < self.ystart:
                                    self.adb("input keyevent KEYCODE_DPAD_UP")
                                    y += dy
                            
                            print('Start X: ', self.xstart)
                            print('Start Y: ', self.ystart)
                            print('# steps in X: ', nr_x2scan)
                            print('# steps in Y: ', nr_y2scan)
                            print('linewidth: ', w)
                            print('color: ', linecolor)
                            maindir = self.select_directory()
                            if maindir:
                                print(f"Selected directory: {maindir}")
                            date = self.timestamp()
                            datadir = maindir + '/Mapping_' + self.name + date
                            self.create_directory(datadir)
                            
                            # Initiate array
                            freqsname = '%s/freqs.npy' % (datadir)
                            darkname = '%s/S21_dark.npy' % (datadir)
                            settingsname = '%s/settings.txt' % (datadir)
                            dict = {'color': linecolor, 'width':w,
                                    'fstart':self.fstart, 'fstop':self.fstop, 'subscanbw':self.subscanbw, 
                                    'kidpower':self.kidpower, 'ifbw':self.ifbw, 'nr points':self.num_points, 'xstart':self.xstart, 'ystart':self.ystart, 'xsteps':self.xsteps, 'ysteps':self.ysteps}
                            with open(settingsname, 'w') as file:
                                json.dump(dict, file)

                            # Make dark scan and save it
                            while linetype != 'none':
                                self.adb("input keyevent KEYCODE_B")
                                linetype = next(linetype_cycler)
                            pygame.time.wait(wait_before_scan)
                            st = time.time()
                            freqs, dark_s21 = self.sweep()
                            et = time.time()
                            scan_time = et - st
                            print('Time 1 scan = %d seconds' % scan_time)
                            if square:
                                print('Expected duration measurement: %d minutes' % ((nr_x2scan) * scan_time / 60))
                            else:
                                print('Expected duration measurement: %d minutes' % ((nr_x2scan + nr_y2scan) * scan_time / 60))
                            np.save(darkname, np.stack((freqs, dark_s21), axis=-1).T)
                            print('Saved: %s' % darkname)                    
                            fig, ax = plt.subplots()
                            ax.plot(freqs, dark_s21)
                            plt.show(block=True)
            pygame.display.flip()
        pygame.quit()
        sys.exit()







    
