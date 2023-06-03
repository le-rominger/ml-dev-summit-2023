"""
@author: Wolfgang R
@description: Demonstrates the usage of Session Management to perform a bodeplot on a passive filter

"""

import contextlib
import logging
import pathlib
import sys

import click
import grpc
from typing import Tuple
import ni_measurementlink_service as nims
from _helpers import ServiceOptions, str_to_enum
from _session_helper import create_nifgen_session, create_niscope_session
from bodeplot import Bodeplot

service_directory = pathlib.Path(__file__).resolve().parent
measurement_service = nims.MeasurementService(
    service_config_path=service_directory / "PythonBodeplotSummit.serviceconfig",
    version="1.0.0.0",
    ui_file_paths=[service_directory / "PythonBodeplotSummit.measui"],
)



@measurement_service.register_measurement
@measurement_service.configuration(
    "filter_pins",
    nims.DataType.PinArray1D,
    ["Vin_measure", "Vout_measure"],
    instrument_type=nims.session_management.INSTRUMENT_TYPE_NI_SCOPE,
)
@measurement_service.configuration(
    "vin_signal",
    nims.DataType.Pin,
    "Vin_signal",
    instrument_type=nims.session_management.INSTRUMENT_TYPE_NI_FGEN,
)
@measurement_service.configuration("Start Freq.", nims.DataType.Double, 100.0)
@measurement_service.configuration("Stop Frequ.", nims.DataType.Double, 50.0e3)
@measurement_service.configuration("Amplitude", nims.DataType.Double, 1.0)
@measurement_service.configuration("Freq. Step", nims.DataType.Int32, 10)
@measurement_service.output("Gain", nims.DataType.DoubleArray1D)
@measurement_service.output("Phase", nims.DataType.DoubleArray1D)
@measurement_service.output("actual_gain", nims.DataType.Double)
@measurement_service.output("actual_phase", nims.DataType.Double)
def measure(filter_pins:str,
            vin_signal:str,
            f_start:float,
            f_stop:float,
            vpp:float,
            steps:int) -> Tuple:

    logging.info(f"pins={filter_pins}, f_start={f_start}, f_stop={f_stop}, steps={steps}, vpp={vpp}")

# -- Add Cancellation callback
    pending_cancellation = False

    def cancel_callback():
        logging.info("Canceling acquisition")
        nonlocal pending_cancellation
        pending_cancellation = True

    measurement_service.context.add_cancel_callback(cancel_callback)

# -- Get Instrument Session

    session_management_client = nims.session_management.Client(
        grpc_channel=measurement_service.get_channel(
            provided_interface=nims.session_management.GRPC_SERVICE_INTERFACE_NAME,
            service_class=nims.session_management.GRPC_SERVICE_CLASS,
        )
    )

# -- Reserve Session
    with contextlib.ExitStack() as stack:
        scope_reservation = stack.enter_context(
            session_management_client.reserve_sessions(
                context=measurement_service.context.pin_map_context,
                pin_or_relay_names=filter_pins,
                instrument_type_id=nims.session_management.INSTRUMENT_TYPE_NI_SCOPE,
                # If another measurement is using the session, wait for it to complete.
                # Specify a timeout to aid in debugging missed unreserve calls.
                # Long measurements may require a longer timeout.
                timeout=20,
            )
        )
        if len(scope_reservation.session_info) != 1:
            measurement_service.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Unsupported number of sessions: {len(scope_reservation.session_info)}",
        )
        fgen_reservation = stack.enter_context(
                session_management_client.reserve_sessions(
                context=measurement_service.context.pin_map_context,
                pin_or_relay_names=[vin_signal],
                instrument_type_id=nims.session_management.INSTRUMENT_TYPE_NI_FGEN,
                # If another measurement is using the session, wait for it to complete.
                # Specify a timeout to aid in debugging missed unreserve calls.
                # Long measurements may require a longer timeout.
                timeout=20,
         )
        )
        if len(fgen_reservation.session_info) != 1:
            measurement_service.context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Unsupported number of sessions: {len(fgen_reservation.session_info)}",
        )

# --- CALL measurement
        bp = Bodeplot()
        bp.scope = create_niscope_session(scope_reservation.session_info[0], measurement_service)
        bp.fgen = create_nifgen_session(fgen_reservation.session_info[0], measurement_service)
        bp.f_start = f_start
        bp.f_stop = f_stop
        bp.f_steps = steps
        bp.amplitude = vpp
        bp.measure()
        # bp.measure_single()
        
        return ([1.0,2.0,3.0],[1.0,2.0,3.0],0.0,1.0)
    return ()


@click.command
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose logging. Repeat to increase verbosity.",
)
def main(verbose: int):
    """Host the Python Bodeplot Summit service."""
    if verbose > 1:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=level)

    with measurement_service.host_service():
        input("Press enter to close the measurement service.\n")


if __name__ == "__main__":
    main()
    sys.exit(0)
