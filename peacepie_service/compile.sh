#!/bin/bash
cd ./tmp/Python-3.10.12
./configure --enable-optimizations
make -j 2
make altinstall
