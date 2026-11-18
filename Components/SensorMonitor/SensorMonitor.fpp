module PiSensor {

  @ Schedule calls without a new reading or sentence before a sensor is lost
  constant SENSOR_LOSS_CALLS = 5

  @ Reading age in seconds above which a metric is invalid
  constant SENSOR_STALE_SECONDS = 2

  @ Identity reads in a row that must fail before the MPU6050 is lost
  constant MPU6050_IDENTITY_FAIL_CALLS = 3

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

  @ Presence of a sensor
  enum SensorState : U8 {
    PRESENT = 0 @< No loss condition holds
    LOST = 1 @< A loss condition holds
  }

  @ Why a metric is invalid, in the order the conditions are tested
  enum InvalidReason : U8 {
    NONE = 0 @< The metric is valid
    IDENTITY = 1 @< Latest MPU6050 identity read failed or returned another value
    NO_FIX = 2 @< Newest GGA sentence carries no quality indicator 1 to 8
    NO_READING = 3 @< No reading since start-up
    FUTURE_TIME = 4 @< Reading time is after the current time or of another time base
    STALE = 5 @< Reading is older than SENSOR_STALE_SECONDS
    OUT_OF_LIMITS = 6 @< A value is not finite or outside its limits
  }

  @ One sample of every metric, with validity and sample time
  struct SensorSamples {
    temperature: F32 @< BMP280 temperature, degrees Celsius
    temperatureValid: Validity
    temperatureTime: Fw.TimeValue @< Reading time, system time source; zero before a first reading
    roll: F32 @< Roll, degrees, -180 to 180, atan2(a_y, a_z) in the MPU6050 body frame
    pitch: F32 @< Pitch, degrees, -90 to 90, in the MPU6050 body frame
    gyro: FprimeSensors.GeometricVector3 @< Rates about the MPU6050 body axes, degrees per second
    attitudeValid: Validity
    attitudeTime: Fw.TimeValue @< Reading time of the MPU6050 reading
    latitude: F64 @< Latitude, degrees
    longitude: F64 @< Longitude, degrees
    altitude: F64 @< Altitude above mean sea level, metres
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

    @ Schedule call: reads the identity register outside the guard, then
    @ evaluates validity and loss and publishes telemetry inside it
    sync input port run: Svc.Sched

    @ GPS sentence from the frame accumulator
    guarded input port gpsSentenceIn: Svc.ComDataWithContext

    @ GPS sentence passed on, unchanged
    output port gpsSentenceOut: Svc.ComDataWithContext

    @ Sample request from the product manager
    guarded input port samplesGetIn: SamplesGet

    @ BMP280 reading pushed by the BMP280 manager
    guarded input port bmpDataIn: Bmp280.Bmp280DataOut

    @ MPU6050 reading pushed by the MPU6050 manager
    guarded input port imuDataIn: MpuImu.ImuDataOut

    @ Latest GPS reading of the GPS manager with its time
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

    @ Why temperature is invalid
    telemetry TemperatureInvalidReason: InvalidReason

    @ Why attitude is invalid
    telemetry AttitudeInvalidReason: InvalidReason

    @ Why location is invalid
    telemetry FixInvalidReason: InvalidReason

    @ BMP280 presence
    telemetry Bmp280State: SensorState

    @ MPU6050 presence
    telemetry Mpu6050State: SensorState

    @ GPS presence
    telemetry GpsState: SensorState

    @ Quality indicator of the newest GGA sentence, 0xFF when none
    telemetry GpsQuality: U8

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------

    @ No BMP280 reading for the loss age
    event Bmp280Lost() severity warning high format "BMP280 lost: no reading"

    @ The MPU6050 gives no reading or fails its identity read
    event Mpu6050Lost(
      reason: Mpu6050LossReason @< What was detected
      status: Drv.I2cStatus @< Status of the latest identity read, for either reason
      identity: U8 @< Value of the latest identity read, 0 when it failed
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
