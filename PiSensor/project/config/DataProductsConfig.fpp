module DataProductsConfig {
    #Base ID for the DataProducts Subtopology, all components are offsets from this base ID
    constant BASE_ID = 0x04000000

    module QueueSizes {
        constant dpCat    = 10
        constant dpMgr  = 10
        constant dpWriter   = 10
        constant dpBufferAccumulator = 10
        constant dpBufferManager   = 10
    }


    module StackSizes {
        constant dpCat    = 64 * 1024
        constant dpMgr  = 64 * 1024
        constant dpWriter   = 64 * 1024
        constant dpBufferAccumulator = 64 * 1024
        constant dpBufferManager   = 64 * 1024
    }

    module Priorities {
        constant dpCat    = 24
        constant dpMgr  = 23
        constant dpWriter   = 22
        constant dpBufferAccumulator = 21
        # dpBufferManager is passive; this value is kept for projects that use
        # the shared DataProducts config constants.
        constant dpBufferManager  = 21
    }

    module CpuAffinities {
        constant dpCat    = Os.TASK_DEFAULT
        constant dpMgr  = Os.TASK_DEFAULT
        constant dpWriter   = Os.TASK_DEFAULT
        constant dpBufferAccumulator = Os.TASK_DEFAULT
        # dpBufferManager is intentionally omitted because it is passive.
    }

    module BufferAccumulator {
        constant allocatorId   = 301
        constant maxNumBuffers = 10
    }

    # Buffer management constants
    module BuffMgr {
        # PiSensor: one PiCamera Capture container, PICTURE_MAX_SIZE (262144) bytes plus the
        # Metrics record and the container overhead. The catalog value is 10000.
        constant dpBufferStoreSize  = 264192
        constant dpBufferStoreCount = 10
        constant dpBufferManagerId  = 300
    }

    # Directory and file paths
    module Paths {
        # PiSensor: a product path is a command argument (fileManager.CalculateCrc and the
        # like), and a command string holds FW_CMD_STRING_MAX_SIZE (40) characters. With
        # this directory "dp/Dp_<id>_<seconds>_<microseconds>.fdp" is 39 characters
        # (8-digit id, 10-digit seconds); with the catalog value "./DpCat" it is 44.
        constant dpDir    = "dp"
        constant dpState  = "dp/DpState.dat"
    }
}
