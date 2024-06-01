# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class MultipleModesNoDefault(BasicModifier):
    """Define modifier with multiple modes and no default mode"""
    name = "multiple-modes-no-default"

    tags('test')

    mode('test_mode1', description='This is the first test mode')

    mode('test_mode2', description='This is the second test mode')
