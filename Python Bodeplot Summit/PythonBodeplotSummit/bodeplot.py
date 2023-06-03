
import niscope
import nifgen
import math


class Bodeplot:

    # -- Property Setter/Getter
    @property
    def scope(self) -> niscope.Session:
        return self._scope

    @scope.setter
    def scope(self, new_scope: niscope.Session):
        self._scope = new_scope

    @property
    def fgen(self) -> nifgen.Session:
        return self._fgen

    @fgen.setter
    def fgen(self, new_fgen: nifgen.Session):
        self._fgen = new_fgen

    @property
    def f_start(self) -> float:
        return self._start_f

    @f_start.setter
    def f_start(self, f: float):
        self._start_f = f

    @property
    def f_stop(self) -> float:
        return self._stop_f

    @f_stop.setter
    def f_stop(self, f: float):
        self._stop_f = f

    @property
    def f_steps(self) -> int:
        return self._start_f

    @f_steps.setter
    def f_steps(self, steps: int):
        self._steps = steps

    @property
    def vin_signal(self) -> str:
        return self._vin

    @vin_signal.setter
    def vin_signal(self, chn: str):
        self._vin = chn

    @property
    def vin_measure(self) -> str:
        return self._vin_measure

    @vin_measure.setter
    def vin_measure(self, chn: str):
        self._vin_measure = chn

    @property
    def vout_measure(self) -> str:
        return self._vout_measure

    @vout_measure.setter
    def vout_measure(self, chn: str):
        self._vout_measure = chn

    @property
    def amplitude(self) -> float:
        return self._vin_amplitude

    @amplitude.setter
    def amplitude(self, vpp: float):
        self._vin_amplitude = vpp

# --- Methods
    def __init__(self):
        """Constructor assign Default Values
        """
        self._start_f = 100
        self._stop_f = 50e3
        self._steps = 100
        self._vin = '0'
        self._vout_measure = '0'
        self._vin_measure = '1'
        self._vin_amplitude = 1

    def configure_arb(self):
        """Initialize the arb reference and configure starting point
        """
        self.fgen.output_mode = nifgen.OutputMode.FUNC
        self.fgen.configure_standard_waveform(
            nifgen.Waveform.SINE, self.amplitude, self.f_start, 0)
        self.fgen.output_enabled = True
        self.fgen.load_impedance = 10e9
        self.fgen.initiate()

    def configure_scope(self):

        self.scope.configure_trigger_edge(
            "0", 0, niscope.TriggerCoupling.DC, niscope.TriggerSlope.POSITIVE, 0)
        
        channel_list = [c for c in range(self.scope.channel_count)] 
        
        self.scope.channels[channel_list].channel_enabled = True
        self.scope.channels[channel_list].probe_attenuation = 1
        self.scope.channels[channel_list].vertical_coupling = niscope.VerticalCoupling.DC
        self.scope.channels[channel_list].input_impedance = 1e6
        self.scope.channels[channel_list].vertical_range = 4
        self.scope.channels[channel_list].vertical_offset = 0

    def re_config_scope(self):

        self.scope.clear_waveform_measurement_stats(niscope.ClearableMeasurement.ALL_MEASUREMENTS)
        self.scope.clear_waveform_processing()
        self.scope.channels[0].vertical_range = 4
        self.scope.channels[1].vertical_range = 4
        self.scope.channels[0].add_waveform_processing(
            niscope.ArrayMeasurement.MULTI_ACQ_AVERAGE)
        self.scope.channels[1].add_waveform_processing(
            niscope.ArrayMeasurement.MULTI_ACQ_AVERAGE)
        # -- Start Acquistion
        self.scope.initiate()
        vin = self.scope.channels[1].fetch_measurement_stats(
            niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK)[0]
        freq = self.scope.channels[1].fetch_measurement_stats(
            niscope.ScalarMeasurement.FREQUENCY)[0]
        vout = self.scope.channels[0].fetch_measurement_stats(
            niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK)[0]
        # - Stop Scope Session
        self.scope.abort()
        self.scope.channels[0].vertical_range = 1.1*vout.result
        self.scope.channels[1].vertical_range = 1.1*vin.result
        # -- Fixed SR since expected cut-off is at 10k
        sr = 1e6
        records = int(20 * 1/freq.result * sr)
        print(f"{freq.result} =>{records}")
        self.scope.configure_horizontal_timing(sr, records, 50, 1,True)
        self.scope.commit()

    def fetch_measurement(self) -> tuple:

        self.scope.clear_waveform_measurement_stats(niscope.ClearableMeasurement.ALL_MEASUREMENTS)
        self.scope.clear_waveform_processing()
        self.scope.channels[0].add_waveform_processing(
            niscope.ArrayMeasurement.MULTI_ACQ_AVERAGE)
        self.scope.channels[1].add_waveform_processing(
            niscope.ArrayMeasurement.MULTI_ACQ_AVERAGE)

        vin = self.scope.channels[1].fetch_measurement_stats(
            niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK)[0]
        vout = self.scope.channels[0].fetch_measurement_stats(
            niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK)[0]
        self.scope.meas_other_channel = 1

        phase = self.scope.channels[0].fetch_measurement_stats(
            niscope.ScalarMeasurement.PHASE_DELAY)[0]
        phase = 360 - phase.result//360
        gain = 20 * math.log10(vout.result/vin.result)

        return (gain, phase)

    def measure(self) -> None:

        self.configure_arb()
        self.configure_scope()
        self.re_config_scope()

        f_list = []
        gain_list = []
        phase_list = []
        f = self.f_start
        while f < self.f_stop:
            # - Configure
            f_list.append(f)
            gain_list.append(gain)
            phase_list.append(phase)
            # Call update results
            f = f * (self.f_stop/self.f_start)**(1/self.f_steps)
            # TODO do something with the data

    def measure_single(self,f:float) -> tuple:
        self.fgen.configure_standard_waveform(
                nifgen.Waveform.SINE, self.amplitude, f, 0)
        self.re_config_scope()
        return self.fetch_measurement()

if __name__ == "__main__":
    #
    bp = Bodeplot()
    bp.scope = niscope.Session("Scope", options={'simulate': True, 'driver_setup': {
                            'Model': '5122', 'BoardType': 'PXI'}})
    bp.fgen = nifgen.Session("Fgen", options={'simulate': True, 'driver_setup': {
                             'Model': '5421', 'BoardType': 'PXIe'}})
    bp.f_start = 200
    bp.f_stop = 50e3
    bp.f_steps = 10
    bp.amplitude = 2
    bp.measure()
