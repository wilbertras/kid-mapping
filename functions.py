import pyvisa
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import os
import matplotlib.pyplot as plt


def get_s21(vna, weinschell, fstart, fstop, subscanbw, num_points, kidpower, ifbw, calfile=False):
    bfout, bfin, rfout = power_calibration()
    subscanbw *= 1e-3
    totscanbw = fstop - fstart
    num_subscans = int(np.ceil(totscanbw / subscanbw))
    realfstart = fstart
    realfstop = fstart + num_subscans * subscanbw
    f0start = realfstart + subscanbw / 2
    freqs = np.linspace(realfstart, realfstop, num_points*num_subscans)
    scans = []
    # Initialize VNA
    if calfile:
        init_vna(vna, calibfile=calfile)
    for i in range(num_subscans):
        f0 = f0start + i*subscanbw
        if i == 0:
            KID_cryoOUt = bfout(f0)
            GainRFbox = rfout(f0)
            PcryoOUt = kidpower + KID_cryoOUt + GainRFbox
            PVNAin = PcryoOUt - 2
            if PVNAin > 62:
                att = 62
            elif PVNAin < 2:
                att = 2
            else:
                att = PVNAin
            att = np.round(att / 2) * 2
        set_weinschell(weinschell, att)
        KID_cryoIn = bfin(f0)
        vna_power = kidpower - KID_cryoIn
        subscan = vna_scan(vna, f0, subscanbw, num_points, vna_power, ifbw, i)
        print('Subscan %d/%d complete' % (i+1, num_subscans), end='\r')
        scans.append(subscan)
    s21 = np.array(scans).flatten()
    print('S21 completed')
    vna.close()
    weinschell.close()
    return freqs, s21


def power_calibration():
    BFout = np.load('calibration files/BFout.npy')
    BFin = np.load('calibration files/BFin.npy')
    RFout = np.load('calibration files/RFout.npy')
    bfout = interp1d(BFout[:, 0], BFout[:, 1])
    bfin = interp1d(BFin[:, 0], BFin[:, 1])
    rfout = interp1d(RFout[:, 0], RFout[:, 1])
    return bfout, bfin, rfout


def connect2vi(VISA, timeout=300000):
    rm = pyvisa.ResourceManager() 
    vi = rm.open_resource(VISA)
    vi.timeout = timeout
    try:
        vi.query('*IDN?')
    except:
        print('Could not connect to VI')
    return vi


def calibrate_vna(vna, calibfile='D:\KIDS\KIDs.csa'):
    try:
        vna.write('SENS:CORR:COLL:FULL')   # Start een volledige 2-poorts kalibratie
        vna.query('*OPC?')                 # Blokkeer totdat kalibratie voltooid is
        vna.write(f'MMEMORY:STOR:CSAR "{calibfile}";')  # Opslaan met dezelfde bestandsnaam
        
        print(f"Calibration successful and saved as: {calibfile}")
    except pyvisa.VisaIOError as e:
        print(f"Error in communication with VNA: {e}")
        

def init_vna(vna, calibfile):
    vna.write('SYST:PRES;')
    vna.write('CONT:AUX:OUTP1:VOLT 0;')
    vna.write('CONT:AUX:OUTP2:VOLT 5;')
    vna.write('OUTP ON;')
    if calibfile:
        vna.write('MMEM:LOAD:CSAR "D:\KIDS\KIDs.csa";')
    else:
        vna.write('MMEM:LOAD:CSAR "D:\KIDS\VNA_through_donottouch.csa";')
    vna.query('*OPC?;')
    vna.write('SENS1:SWE:TRIG:POIN OFF;')
    vna.write('TRIG:SCOP CURR;')
    vna.write('INIT1:CONT ON;')

def vna_scan(vna, f0, subscanbw, num_points, vna_power, ifbw, id):
    # Set sweep params
    session = 'Scan%d' % id
    vna.write('DISP:WIND:TRAC1:DEL;')
    vna.write(f'CALC1:PAR:DEF "{session}", S21;')
    vna.write(f'CALC1:PAR:SEL "{session}";')
    vna.write(f'DISP:WIND:TRAC1:FEED "{session}";')  
    vna.write('DISP:WIND:TRAC1:Y:AUTO')
    vna.write(f'SENS1:FREQ:CENT {f0}GHz;')
    vna.write(f'SENS1:FREQ:SPAN {subscanbw}GHz;')
    vna.write(f'SOUR1:POW1:LEV {vna_power};')
    vna.write(f'SENS1:BWID {ifbw}Hz;')
    vna.write(f'SENS1:SWE:POIN {num_points};') 
    vna.write('MMEM:STOR:TRAC:FORM:SNP DB;')
    vna.write('FORM:DATA ASCII;')
    vna.write('sens1:swe:trig:poin off;')
    vna.write('sens1:swe:time:auto on;')          
    vna.write('TRIG:SOUR MAN;')
    vna.write('INIT:CONT OFF;')
    # power = float(vna.query('SOUR1:POW1:LEV?'))
    # print('VNA power = %.2f' % power, end='\r')
    
    # Trigger a single sweep
    vna.write(f'TRIG:SCOP CURR;')
    vna.write(f'INIT:IMM;')
    if vna.query('*OPC?'):
        response = vna.query_ascii_values(f'CALC1:DATA? FDATA;')
        s21 = np.array(response)     
    return s21


def set_weinschell(weinschell, attn):
    attn_chan2 = 2
    weinschell.write(f'CHAN1;ATTN {attn}')
    weinschell.write(f'CHAN2;ATTN {attn_chan2}')
