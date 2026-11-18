#ifndef PISENSOR_PISENSORTOPOLOGYDEFS_HPP
#define PISENSOR_PISENSORTOPOLOGYDEFS_HPP

#include "PiSensor/Top/FppConstantsAc.hpp"

#include "Svc/Subtopologies/CdhCore/PingEntries.hpp"
#include "Svc/Subtopologies/ComCcsds/PingEntries.hpp"
#include "Svc/Subtopologies/DataProducts/PingEntries.hpp"
#include "Svc/Subtopologies/FileHandlingCfdp/PingEntries.hpp"

#include "Svc/Subtopologies/CdhCore/SubtopologyTopologyDefs.hpp"
#include "Svc/Subtopologies/ComCcsds/SubtopologyTopologyDefs.hpp"
#include "Svc/Subtopologies/DataProducts/SubtopologyTopologyDefs.hpp"
#include "Svc/Subtopologies/FileHandlingCfdp/SubtopologyTopologyDefs.hpp"

#include "fprime-sensors/Bmp280/Subtopology/SubtopologyTopologyDefs.hpp"
#include "fprime-sensors/MpuImu/Subtopology/SubtopologyTopologyDefs.hpp"
#include "fprime-sensors/NmeaGps/Subtopology/SubtopologyTopologyDefs.hpp"
#include "fprime-sensors/Rfm69/Subtopology/SubtopologyTopologyDefs.hpp"

#include "Svc/Subtopologies/ComCcsds/Ports_ComBufferQueueEnumAc.hpp"
#include "Svc/Subtopologies/ComCcsds/Ports_ComPacketQueueEnumAc.hpp"

namespace PingEntries {
namespace PiSensor_rateGroup10Hz {
enum { WARN = 3, FATAL = 5 };
}
namespace PiSensor_rateGroup1Hz {
enum { WARN = 3, FATAL = 5 };
}
}  // namespace PingEntries

namespace PiSensor {

//! State handed to the topology: link endpoint and device paths of the bench
struct TopologyState {
    const char* hostname;                  //!< Ground host of the TCP link
    U16 port;                              //!< Ground port of the TCP link
    CdhCore::SubtopologyState cdhCore;
    ComCcsds::SubtopologyState comCcsds;
    DataProducts::SubtopologyState dataProducts;
    FileHandlingCfdp::SubtopologyState fileHandlingCfdp;
    Bmp280::SubtopologyState bmp;          //!< BMP280 SPI bus and chip select
    MpuImu::SubtopologyState mpu;          //!< MPU6050 I2C device
    NmeaGps::SubtopologyState gps;         //!< GPS UART device and baud rate
    Rfm69::SubtopologyState rfm69;         //!< RFM69 SPI device and reset line
};

namespace PingEntries = ::PingEntries;
}  // namespace PiSensor

#endif
