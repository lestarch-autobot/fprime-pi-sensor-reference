add_compile_options(
  -Wno-shadow
)
# The link of the deployment (PiSensor/CMakeLists.txt): the topology, its instances and its packets
if (PISENSOR_COM STREQUAL "RFM69")
  set(PISENSOR_COM_INPUTS "${CMAKE_CURRENT_LIST_DIR}/topologyRfm69.fpp")
else()
  set(PISENSOR_COM_INPUTS "${CMAKE_CURRENT_LIST_DIR}/instancesTcp.fpp" "${CMAKE_CURRENT_LIST_DIR}/topologyTcp.fpp")
endif()
register_fprime_module(
  AUTOCODER_INPUTS
    "${CMAKE_CURRENT_LIST_DIR}/instances.fpp"
    "${CMAKE_CURRENT_LIST_DIR}/system.fpp"
    ${PISENSOR_COM_INPUTS}
  SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/PiSensorTopology.cpp"
  DEPENDS
    Fw_Logger
    Svc_PosixTime
    Svc_TlmPacketizer_config_TlmPacketizerConfig
    fprime-sensors_NmeaGps_Subtopology
    Components_PiCamera
)
