// Copyright 2020 The Pigweed Authors
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not
// use this file except in compliance with the License. You may obtain a copy of
// the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations under
// the License.
#pragma once

#include "pw_sync/spin_lock.h"
#include "pw_sync/yield_core.h"

namespace pw::sync {

inline SpinLock::SpinLock()
    : native_type_{.locked = false, .saved_interrupt_mask = 0} {}

inline SpinLock::native_handle_type SpinLock::native_handle() {
  return native_type_;
}

}  // namespace pw::sync