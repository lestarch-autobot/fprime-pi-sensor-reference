#!/bin/sh
# Build the PiSensor image and its dictionary from this checkout, from scratch.
#   build_image.sh [extra fprime-util generate options]
# fprime-util of lib/fprime/requirements.txt is on PATH. PICAMERA_SYSROOT names the
# directory with the camera library development files when the build host has none installed.
# For an image that counts coverage (see Components/PiCamera/test/int/README.md):
#   build_image.sh -DCMAKE_C_FLAGS=--coverage -DCMAKE_CXX_FLAGS=--coverage -DCMAKE_EXE_LINKER_FLAGS=--coverage
set -e
cd "$(dirname "$0")/../../.."
rm -rf build-fprime-automatic-native build-artifacts
fprime-util generate ${PICAMERA_SYSROOT:+-DPICAMERA_SYSROOT=$PICAMERA_SYSROOT} "$@"
fprime-util build -j4
sha256sum build-artifacts/Linux/PiSensor/bin/PiSensor build-artifacts/Linux/PiSensor/dict/PiSensorTopologyDictionary.json
