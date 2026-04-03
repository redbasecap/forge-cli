#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 -c "
from solution import fibonacci
assert fibonacci(0) == 0, f'fibonacci(0) = {fibonacci(0)}'
assert fibonacci(1) == 1, f'fibonacci(1) = {fibonacci(1)}'
assert fibonacci(10) == 55, f'fibonacci(10) = {fibonacci(10)}'
assert fibonacci(20) == 6765, f'fibonacci(20) = {fibonacci(20)}'
print('All tests passed!')
"
