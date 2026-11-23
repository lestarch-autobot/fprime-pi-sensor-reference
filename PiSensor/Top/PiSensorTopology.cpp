// Topology setup of the PiSensor base deployment
#include <PiSensor/Top/PiSensorTopologyAc.hpp>

#include <Fw/Types/MallocAllocator.hpp>

using namespace PiSensor;

// Allocator shared with the catalog GPS subtopology (declared extern there)
Fw::MallocAllocator mallocator;

// Base cycle 1 kHz: divisors for the 10 Hz and 1 Hz rate groups. The 1 Hz group starts 50 ms after the
// 10 Hz cycle on which the sensor managers write their Reading, so that the telemetry packetizer
// (1 Hz) always finds the sample of that second; the flush group follows 250 ms later and sends
// the frame holding the packets of that second (docs/link-budget.md)
Svc::RateGroupDriver::DividerSet rateGroupDivisorsSet{{{1, 0}, {100, 0}, {1000, 50}, {1000, 300}}};

Svc::ActiveRateGroup::ContextArray rateGroup1KHzContext(0);
Svc::ActiveRateGroup::ContextArray rateGroup10HzContext(0);
Svc::ActiveRateGroup::ContextArray rateGroup1HzContext(0);
Svc::ActiveRateGroup::ContextArray rateGroup1HzFlushContext(0);

namespace PiSensor {

#ifdef PISENSOR_COM_TCP
// Priority of the TCP driver task, as in the F Prime Ref deployment
constexpr FwTaskPriorityType COMM_PRIORITY = 34;
#endif

void setupTopology(const TopologyState& state) {
    initComponents(state);
    setBaseIds();
    connectComponents();
    configComponents(state);
#ifdef PISENSOR_COM_TCP
    FW_ASSERT(state.hostname != nullptr);
    (void)comDriver.configure(state.hostname, state.port);
#endif
    rateGroupDriver.configure(rateGroupDivisorsSet);
    rateGroup1KHz.configure(rateGroup1KHzContext);
    rateGroup10Hz.configure(rateGroup10HzContext);
    rateGroup1Hz.configure(rateGroup1HzContext);
    rateGroup1HzFlush.configure(rateGroup1HzFlushContext);
    regCommands();
    readParameters();
    loadParameters();
    startTasks(state);
#ifdef PISENSOR_COM_TCP
    // Task of the TCP driver: opens the connection, opens it again when it is lost, and reads the uplink
    Os::TaskString name("ReceiveTask");
    comDriver.start(name, COMM_PRIORITY, Default::STACK_SIZE);
#endif
}

void startRateGroups(const Fw::TimeInterval& interval) {
    linuxTimer.startTimer(interval);
}

void stopRateGroups() {
    linuxTimer.quit();
}

void teardownTopology(const TopologyState& state) {
    stopTasks(state);
#ifdef PISENSOR_COM_TCP
    comDriver.stop();
    (void)comDriver.join();
#endif
    freeThreads(state);
    tearDownComponents(state);
    deinitComponents(state);
}

}  // namespace PiSensor
