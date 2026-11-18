module PiSensor {

  @ Schedule calls without a new reading or sentence before a sensor is lost
  constant SENSOR_LOSS_CALLS = 5

  @ Reading age in seconds above which a metric is invalid
  constant SENSOR_STALE_SECONDS = 2

  @ I2C address of the MPU6050
  constant MPU6050_ADDRESS = 0x68

  @ MPU6050 identity register
  constant MPU6050_IDENTITY_REGISTER = 0x75

  @ Value the MPU6050 identity register returns
  constant MPU6050_IDENTITY_VALUE = 0x68

  @ Validity of a metric
  enum Validity : U8 {
    INVALID = 0 @< The metric must not be used
    VALID = 1 @< The metric is current
  }

  @ Why the MPU6050 is reported lost
  enum Mpu6050LossReason : U8 {
    NO_READING = 0 @< No reading for the loss age
    IDENTITY = 1 @< The identity read failed or returned a wrong value
  }

  @ One sample of every metric, with validity and sample time
  struct SensorSamples {
    temperature: F32 @< BMP280 temperature, degrees Celsius
    temperatureValid: Validity
    temperatureTime: Fw.TimeValue @< Reading time of the BMP280 reading
    roll: F32 @< Roll, degrees
    pitch: F32 @< Pitch, degrees
    gyro: FprimeSensors.GeometricVector3 @< Gyro rates, degrees per second
    attitudeValid: Validity
    attitudeTime: Fw.TimeValue @< Reading time of the MPU6050 reading
    latitude: F64 @< Latitude, degrees
    longitude: F64 @< Longitude, degrees
    altitude: F64 @< Altitude, metres
    fixValid: Validity
    locationTime: Fw.TimeValue @< Reading time of the GPS reading
  }

  @ Request for the latest sample of every metric
  port SamplesGet(
    ref samples: SensorSamples @< Filled by the callee
  )

  @ Sensor monitor: publishes the sensor telemetry with validity, reports
  @ sensor loss and return, serves samples to products
  passive component SensorMonitor {

    # ----------------------------------------------------------------------
    # General ports
    # ----------------------------------------------------------------------

    @ Schedule call: evaluates validity and loss, publishes telemetry
    guarded input port run: Svc.Sched

    @ GPS sentence from the frame accumulator
    guarded input port gpsSentenceIn: Svc.ComDataWithContext

    @ GPS sentence passed on, unchanged
    output port gpsSentenceOut: Svc.ComDataWithContext

    @ Sample request from the product manager
    guarded input port samplesGetIn: SamplesGet

    @ Latest BMP280, MPU6050 and GPS readings with their times
    output port tlmGetOut: Fw.TlmGet

    @ MPU6050 identity register read through the IMU bus driver
    output port imuIdentityOut: Drv.I2cWriteRead

    # ----------------------------------------------------------------------
    # Special ports
    # ----------------------------------------------------------------------

    event port eventOut

    text event port textEventOut

    telemetry port tlmOut

    time get port timeGetOut

    # ----------------------------------------------------------------------
    # Telemetry
    # ----------------------------------------------------------------------

    @ BMP280 temperature
    telemetry Temperature: F32 format "{.2f} degC"

    @ Temperature validity
    telemetry TemperatureValid: Validity

    @ Roll from the MPU6050 acceleration
    telemetry Roll: F32 format "{.1f} deg"

    @ Pitch from the MPU6050 acceleration
    telemetry Pitch: F32 format "{.1f} deg"

    @ Roll, pitch and gyro rate validity
    telemetry AttitudeValid: Validity

    @ Gyro rate about x
    telemetry GyroX: F32 format "{.2f} deg/s"

    @ Gyro rate about y
    telemetry GyroY: F32 format "{.2f} deg/s"

    @ Gyro rate about z
    telemetry GyroZ: F32 format "{.2f} deg/s"

    @ GPS latitude
    telemetry Latitude: F64 format "{.6f} deg"

    @ GPS longitude
    telemetry Longitude: F64 format "{.6f} deg"

    @ GPS altitude
    telemetry Altitude: F64 format "{.1f} m"

    @ Location fix validity
    telemetry FixValid: Validity

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------

    @ No BMP280 reading for the loss age
    event Bmp280Lost() severity warning high format "BMP280 lost: no reading"

    @ The MPU6050 gives no reading or fails its identity read
    event Mpu6050Lost(
      reason: Mpu6050LossReason @< What was detected
      status: Drv.I2cStatus @< Status of the identity read
      identity: U8 @< Identity value read, 0 when the read failed
    ) severity warning high format "MPU6050 lost: {}, identity read {} value 0x{x}"

    @ No GPS sentence for the loss age
    event GpsSilent() severity warning high format "GPS silent: no sentence"

    @ The BMP280 delivers readings again
    event Bmp280Returned() severity activity high format "BMP280 returned"

    @ The MPU6050 delivers readings again with the right identity
    event Mpu6050Returned() severity activity high format "MPU6050 returned"

    @ GPS sentences arrive again
    event GpsReturned() severity activity high format "GPS sentences returned"

  }

}
