// Topology setup of the PiSensor base deployment
#include <PiSensor/Top/PiSensorTopologyAc.hpp>

#include <Fw/Types/MallocAllocator.hpp>

using namespace PiSensor;

// Allocator shared with the catalog GPS subtopology (declared extern there)
Fw::MallocAllocator mallocator;

// Base cycle 10 Hz: divisors for the 10 Hz and 1 Hz rate groups
Svc::RateGroupDriver::DividerSet rateGroupDivisorsSet{{{1, 0}, {10, 0}}};

Svc::ActiveRateGroup::ContextArray rateGroup10HzContext(0);
Svc::ActiveRateGroup::ContextArray rateGroup1HzContext(0);

enum TopologyConstants {
    COMM_PRIORITY = 34,
};

namespace PiSensor {

void setupTopology(const TopologyState& state) {
    initComponents(state);
    setBaseIds();
    connectComponents();
    configComponents(state);
    rateGroupDriver.configure(rateGroupDivisorsSet);
    rateGroup10Hz.configure(rateGroup10HzContext);
    rateGroup1Hz.configure(rateGroup1HzContext);
    if (state.hostname != nullptr && state.port != 0) {
        tcpLink.configure(state.hostname, state.port);
    }
    regCommands();
    readParameters();
    loadParameters();
    startTasks(state);
    if (state.hostname != nullptr && state.port != 0) {
        Os::TaskString name("ReceiveTask");
        tcpLink.start(name, COMM_PRIORITY, Default::STACK_SIZE);
    }
}

void startRateGroups(const Fw::TimeInterval& interval) {
    linuxTimer.startTimer(interval);
}

void stopRateGroups() {
    linuxTimer.quit();
}

void teardownTopology(const TopologyState& state) {
    stopTasks(state);
    freeThreads(state);
    tcpLink.stop();
    (void)tcpLink.join();
    tearDownComponents(state);
    deinitComponents(state);
}

}  // namespace PiSensor
