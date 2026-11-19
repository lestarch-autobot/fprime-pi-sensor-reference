// ======================================================================
// \title  PiCameraTestMain.cpp
// \author ubuntu
// \brief  cpp file for PiCamera component test main function
// ======================================================================

#include "PiCameraTester.hpp"

TEST(Nominal, toDo) {
  PiSensor::PiCameraTester tester;
  tester.toDo();
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
