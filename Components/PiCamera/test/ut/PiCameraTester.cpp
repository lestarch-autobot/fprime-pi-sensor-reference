// ======================================================================
// \title  PiCameraTester.cpp
// \author ubuntu
// \brief  cpp file for PiCamera component test harness implementation class
// ======================================================================

#include "PiCameraTester.hpp"

namespace PiSensor {

// ----------------------------------------------------------------------
// Construction and destruction
// ----------------------------------------------------------------------

PiCameraTester ::PiCameraTester()
    : PiCameraGTestBase("PiCameraTester", PiCameraTester::MAX_HISTORY_SIZE),
      component("PiCamera") {
  this->initComponents();
  this->connectPorts();
}

PiCameraTester ::~PiCameraTester() { this->component.deinit(); }

// ----------------------------------------------------------------------
// Tests
// ----------------------------------------------------------------------

void PiCameraTester ::toDo() {
  // TODO
}

} // namespace PiSensor
