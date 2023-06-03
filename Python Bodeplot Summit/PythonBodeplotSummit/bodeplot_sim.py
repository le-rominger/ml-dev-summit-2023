"""
@author: Wolfgang R
@description: Simulates a bodeplot using PySpice
@requires: Python 3.9 64-Bit
https://pyspice.fabrice-salvaire.fr/releases/v1.4/overview.html
pip install PySpice
pyspice-post-installation --install-ngspice-dll
pyspice-post-installation --check-install

"""

from PySpice.Unit import *
from PySpice.Spice.Netlist import Circuit
from PySpice.Plot.BodeDiagram import bode_diagram
import math
import numpy as np
import matplotlib.pyplot as plt
# import seaborn as sns
# sns.set()
# sns.set_style('dark')
import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()


jumper = False
class BodePlotSim(object):
    def __init__(self):pass
    def measure(self):pass

circuit = Circuit('Low-Pass RC Filter')

circuit.SinusoidalVoltageSource('input', 'in', circuit.gnd, amplitude=1@u_V)

if jumper:
    R1 = circuit.R(1, 'in', 'out', 10@u_kΩ)
else:
    R1 = circuit.R(1, 'in', 'out', 3.3@u_kΩ)
C1 = circuit.C(1, 'out', circuit.gnd, 6.8@u_nF)

break_frequency = 1 / (2 * math.pi * float(R1.resistance * C1.capacitance))

print("Break frequency = {:.1f} Hz".format(break_frequency))

simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.ac(start_frequency=100@u_Hz, stop_frequency=100@u_kHz,
                        number_of_points=10,  variation='dec')

figure, axes = plt.subplots(2, figsize=(20, 10))
style = {
    'marker':'x',
    'color':'blue',
    'linestyle':'--'
    
}
axes[0].semilogx(analysis.frequency, 20*np.log10(np.absolute(analysis.out)), **style )
axes[0].grid(True)
axes[0].grid(True, which='minor')
axes[0].set_xlabel("Frequency [Hz]")
axes[0].set_ylabel("Gain [dB]")

axes[1].semilogx(analysis.frequency, np.angle(analysis.out, deg=False), **style )
axes[1].grid(True)
axes[1].grid(True, which='minor')
axes[1].set_xlabel("Frequency [Hz]")
axes[1].set_ylabel("Phase [rad]")
axes[1].set_ylim(-math.pi/2, 0)
plt.yticks((-math.pi/2, -math.pi/4, 0),
                  (r"$-\frac{\pi}{2}$", r"$-\frac{\pi}{4}$", 0))

for ax in axes:
    ax.axvline(x=break_frequency, color='red')

plt.suptitle("Bode Diagram of a Low-Pass RC Filter")
plt.show()
