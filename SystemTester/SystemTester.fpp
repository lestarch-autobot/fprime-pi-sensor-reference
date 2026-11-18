module SystemTester {

  @ Test harness component: record markers and start reports for system tests.
  @ Harness, not part of the mission design (SSDD decision D13).
  passive component SystemTester {

    @ Rate group port, 1 Hz
    sync input port run: Svc.Sched

    @ Write a marker into the event record
    sync command MARK(
      $id: U32 @< Marker identifier chosen by the test
    )

    @ A marker command was received
    event Marker(
      $id: U32 @< Marker identifier of the command
    ) severity activity high format "Marker {}"

    @ The process started; sent once, on the first cycle
    event Started severity activity high format "Deployment started"

    @ Seconds since the process started
    telemetry UptimeS: U32

    command recv port cmdIn
    command reg port cmdRegOut
    command resp port cmdResponseOut
    event port eventOut
    text event port textEventOut
    telemetry port tlmOut
    time get port timeGetOut
  }
}
