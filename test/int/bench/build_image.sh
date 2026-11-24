#!/bin/sh
# Build the PiSensor image and its dictionary from this checkout, from scratch.
#   build_image.sh [extra fprime-util generate options]
# fprime-util of lib/fprime/requirements.txt is on PATH. PICAMERA_SYSROOT names the
# directory with the camera library development files when the build host has none installed.
# The image does not depend on the directory of the checkout: the compiler writes file names (those of
# assertions) relative to the checkout, as `./Components/PiCamera/PiCamera.cpp`.
# For an image that counts coverage (see Components/PiCamera/test/int/README.md):
#   build_image.sh -DCMAKE_C_FLAGS=--coverage -DCMAKE_CXX_FLAGS=--coverage -DCMAKE_EXE_LINKER_FLAGS=--coverage
# These options take the place of CFLAGS and CXXFLAGS below, so the coverage image keeps the absolute names
# that gcov reads.
set -e
cd "$(dirname "$0")/../../.."
rm -rf build-fprime-automatic-native build-artifacts
CFLAGS="-ffile-prefix-map=$(pwd -P)=. -ffile-prefix-map=$(pwd -L)=."
CXXFLAGS=$CFLAGS
export CFLAGS CXXFLAGS
fprime-util generate ${PICAMERA_SYSROOT:+-DPICAMERA_SYSROOT=$PICAMERA_SYSROOT} "$@"
fprime-util build -j4
sha256sum build-artifacts/Linux/PiSensor/bin/PiSensor build-artifacts/Linux/PiSensor/dict/PiSensorTopologyDictionary.json
