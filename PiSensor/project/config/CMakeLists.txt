# Project configuration: files here replace catalog configuration files of the same name.
register_fprime_config(
    INTERFACE
    CONFIGURATION_OVERRIDES
        "${CMAKE_CURRENT_LIST_DIR}/AcConstants.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/CdhCoreTlmConfig.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/CfdpCfg.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/ComCcsdsConfig.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/ComCfg.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/DataProductsConfig.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/TlmPacketizerCfg.fpp"
)
