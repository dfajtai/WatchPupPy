#!/bin/bash
if [ -d "../env" ]; then
    source ../env/bin/activate
    echo "Virtual environment activated."
else
    echo "Virtual environment not found. Please create it first."
fi