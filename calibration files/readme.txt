Calibration procedure as understood from the various labview files
The power out the cryostat and into the VNA hould be less than 0: P@VNAin < 0. This means that the Weinschell attanuator channel 1 should attenuate the power such that it in below 0.
If P@VNAin < 0, the weinschell attanuation is set to 


We want to input desired power at KID and compute what power that translated to at VNA
# KIDpower + KID_cryoOUT + GainRFbox(freq) - Weinschell = P@VNAin
# KIDpower + KID_cryoOUTp + GainRFbox(freq)-P@VNAin=W

# INIT VNA
:MMEMORY:LOAD 'D:\KIDS\KIDs.csa'
*OPC

Loop over num_subscans

    # SET WEINSCHELL ATTENUATOR
    0. Input KIDpower
    1. KID_cryoOUt obtained from BleuforsOutput2022_4-8GHz.txt 
    2. Interpolate at F0 to get the correct value
    3. GainRFbox is obtained from RFbox_Entropy.txt 
    4. Interpolate at F0 to get the correct value
    5. Add: PcryoOUt=KIDpower + KID_cryoOUT + GainRFbox
    6. Substract: P@VNAin = PcryoOUt --2
    7. Check if PcryoOUt <= 62, else: PcryoOUt=62, give error
    8. Check if PcryoOUt > 2, else: 
    9. Clip PcryoOUt to even number, Weinschell=round(PryoOUt / 2)*2, write to VNA
    10. Power into VNA@F0=KIDpower + KID_cryoOUT + GainRFbox - Weinschell

    # SET VNA POWER
    0. Input KIDpower
    1. KID_cryoIn from interpolating BlueforsInput2020.txt
    2. PVNA = KIDpower - KID_cryoIn

# INIT VNA
:MMEMORY:LOAD 'D:\KIDS\KIDs.csa'
*OPC