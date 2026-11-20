module PiSensor {

  module Default {
    constant QUEUE_SIZE = 10
    constant STACK_SIZE = 64 * 1024
  }

  instance linuxTimer: Svc.LinuxTimer base id 0x10000000

  instance rateGroupDriver: Svc.RateGroupDriver base id 0x10001000

  instance rateGroup1KHz: Svc.ActiveRateGroup base id 0x10002000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 41

  instance rateGroup10Hz: Svc.ActiveRateGroup base id 0x10003000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 40

  instance rateGroup1Hz: Svc.ActiveRateGroup base id 0x10004000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 39

  @ 1 Hz, 250 ms after rateGroup1Hz: sends the frame that holds the telemetry packets of that second
  instance rateGroup1HzFlush: Svc.ActiveRateGroup base id 0x10007000 \
    queue size Default.QUEUE_SIZE \
    stack size Default.STACK_SIZE \
    priority 39

  instance posixTime: Svc.PosixTime base id 0x10005000

  @ Holds a frame until the radio is free and sends it again when the radio refuses it
  instance comRetry: Svc.ComRetry base id 0x10006000


  @ Pi Camera: one picture and the latest sensor readings as one data product per capture command
  instance piCamera: PiSensor.PiCamera base id 0x10008000 \
    queue size 5 \
    stack size 1048576 \
    priority 30 \
  {
    phase Fpp.ToCpp.Phases.configComponents """
    PiSensor::piCamera.configure(
        PiSensor::getCamera(),
        Bmp280::bmpManager.getIdBase() + PiSensor::SENSOR_READING_CHANNEL,
        MpuImu::imuManager.getIdBase() + PiSensor::SENSOR_READING_CHANNEL,
        NmeaGps::gpsManager.getIdBase() + PiSensor::SENSOR_READING_CHANNEL
    );
    """
  }

}
