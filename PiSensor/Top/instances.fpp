module PiSensor {

  module Default {
    constant QUEUE_SIZE = 10
    constant STACK_SIZE = 64 * 1024
  }

  instance linuxTimer: Svc.LinuxTimer base id 0x10000000

  instance rateGroupDriver: Svc.RateGroupDriver base id 0x10001000

  instance rateGroup10Hz: Svc.ActiveRateGroup base id 0x10002000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 40

  instance rateGroup1Hz: Svc.ActiveRateGroup base id 0x10003000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 39

  instance posixTime: Svc.PosixTime base id 0x10004000

  @ Prototype link: TCP byte stream under the CCSDS stack
  instance tcpLink: Drv.TcpClient base id 0x10005000

  @ CFDP file transfer (member of PiFileHandling)
  instance cfdpManager: Svc.Ccsds.Cfdp.CfdpManager base id 0x10010000 \
    queue size 30 \
    stack size 128 * 1024 \
    priority 24 \
  {
    phase Fpp.ToCpp.Phases.configComponents """
    PiSensor::cfdpManager.configure(mallocator, 10);
    """
    phase Fpp.ToCpp.Phases.tearDownComponents """
    PiSensor::cfdpManager.cleanup();
    """
  }

  @ On-board file operations (member of PiFileHandling)
  instance fileManager: Svc.FileManager base id 0x10011000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 22 \
  {
    phase Fpp.ToCpp.Phases.configComponents """
    PiSensor::fileManager.configure("/");
    """
  }

  @ Parameter database (member of PiFileHandling)
  instance prmDb: Svc.PrmDb base id 0x10012000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 21 \
  {
    phase Fpp.ToCpp.Phases.configComponents """
    PiSensor::prmDb.configure("PrmDb.dat");
    PiSensor::prmDb.configureSandbox("/");
    """
    phase Fpp.ToCpp.Phases.readParameters """
    PiSensor::prmDb.readParamFile();
    """
  }

  @ Test harness component (decision D13); not part of the mission design
  instance sysTester: SystemTester.SystemTester base id 0x1000F000

}
