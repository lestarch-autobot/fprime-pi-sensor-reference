# Link between the deployment and the ground: TCP (Drv.TcpClient behind Svc.ComStub) or RFM69 (the packet
# radio of fprime-sensors). Select with -DPISENSOR_COM=RFM69 at generate time.
set(PISENSOR_COM "TCP" CACHE STRING "Link of the PiSensor deployment: TCP or RFM69")
set_property(CACHE PISENSOR_COM PROPERTY STRINGS TCP RFM69)
if (NOT PISENSOR_COM MATCHES "^(TCP|RFM69)$")
  message(FATAL_ERROR "PISENSOR_COM is '${PISENSOR_COM}': TCP or RFM69")
endif()
add_compile_definitions(PISENSOR_COM_${PISENSOR_COM})

add_fprime_subdirectory("${CMAKE_CURRENT_LIST_DIR}/Top/")

register_fprime_deployment(
    SOURCES
        "${CMAKE_CURRENT_LIST_DIR}/Main.cpp"
    DEPENDS
        PiSensor_Top
)
