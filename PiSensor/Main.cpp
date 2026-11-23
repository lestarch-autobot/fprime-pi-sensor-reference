// ======================================================================
// \title  Main.cpp
// \author mstarch
// \brief main program for reference application. Intended for CLI-based systems (Linux, macOS)
//
// \copyright
// Copyright 2009-2022, by the California Institute of Technology.
// ALL RIGHTS RESERVED.  United States Government Sponsorship
// acknowledged.
// ======================================================================
// Used to access topology functions
#include <PiSensor/Top/PiSensorTopology.hpp>
// Used for signal handling shutdown
#include <signal.h>
// Used for command line argument processing
#include <getopt.h>
// Used for atoi
#include <cstdlib>
// Used to get the Os::Console
#include <Os/Os.hpp>
// Used for logging to the console
#include <Fw/Logger/Logger.hpp>

/**
 * \brief print commandline help message
 *
 * This will print a command line help message including the available command line arguments.
 *
 * @param app: name of application
 */
void print_usage(const char* app) {
#ifdef PISENSOR_COM_TCP
    Fw::Logger::log("Usage: ./%s -a <ground address> -p <ground TCP port>\n-h\tHelp\n", app);
#else
    Fw::Logger::log("Usage: ./%s [options]\n-h\tHelp\n", app);
#endif
}

/**
 * \brief shutdown topology cycling on signal
 *
 * The reference topology allows for a simulated cycling of the rate groups. This simulated cycling needs to be stopped
 * in order for the program to shutdown. This is done via handling signals such that it is performed via Ctrl-C
 *
 * @param signum
 */
static void signalHandler(int signum) {
    PiSensor::stopRateGroups();
}

/**
 * \brief execute the program
 *
 * This F´ program is designed to run in standard environments (e.g. Linux/macOs running on a laptop). Thus it uses
 * command line inputs to specify how to connect.
 *
 * @param argc: argument count supplied to program
 * @param argv: argument values supplied to program
 * @return: 0 on success, something else on failure
 */
int main(int argc, char* argv[]) {
    Os::init();
    I32 option = 0;
#ifdef PISENSOR_COM_TCP
    const char* const options = "ha:p:";
    const char* hostname = nullptr;
    U16 port = 0;
#else
    const char* const options = "h";
#endif

    // Loop while reading the getopt supplied options
    while ((option = getopt(argc, argv, options)) != -1) {
        switch (option) {
#ifdef PISENSOR_COM_TCP
            case 'a':
                hostname = optarg;
                break;
            case 'p':
                port = static_cast<U16>(atoi(optarg));
                break;
#endif
            // Cascade intended: help output
            case 'h':
            // Cascade intended: help output
            case '?':
            // Default case: output help and exit
            default:
                print_usage(argv[0]);
                return (option == 'h') ? 0 : 1;
        }
    }
    // Object for communicating state to the reference topology
    PiSensor::TopologyState inputs;
    // Bench devices of the Raspberry Pi 5 (docs/ledger.md)
    inputs.bmp.device = {0, 0};
    inputs.mpu.device = "/dev/i2c-1";
    inputs.gps.device = "/dev/ttyACM0";  // USB GPS receiver
    inputs.gps.baud = 9600;
#ifdef PISENSOR_COM_TCP
    // The ground address and port are bench facts: required, no default
    if ((hostname == nullptr) || (port == 0)) {
        print_usage(argv[0]);
        return 1;
    }
    inputs.hostname = hostname;
    inputs.port = port;
#else
    inputs.rfm69.device.device = 0;  // SPI bus 0
    inputs.rfm69.device.select = 1;  // chip select 1 (the BMP280 has chip select 0)
    inputs.rfm69.device.resetGpioChip = "/dev/gpiochip0";
    inputs.rfm69.device.resetGpioPin = 26;
#endif

    // Setup program shutdown via Ctrl-C
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    Fw::Logger::log("Hit Ctrl-C to quit\n");

    // Setup, cycle, and teardown topology
    PiSensor::setupTopology(inputs);
    PiSensor::startRateGroups(Fw::TimeInterval(0, 1000));  // 1 kHz base cycle
    PiSensor::teardownTopology(inputs);
    Fw::Logger::log("Exiting...\n");
    return 0;
}
