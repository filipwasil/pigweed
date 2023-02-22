// Copyright 2023 The Pigweed Authors
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

#include "pw_async/internal/types.h"
#include "pw_chrono/system_clock.h"
#include "pw_containers/intrusive_list.h"

namespace pw::async {
class BasicDispatcher;
namespace test::backend {
class NativeFakeDispatcher;
}
}  // namespace pw::async

namespace pw::async::backend {

// Task backend for BasicDispatcher.
class NativeTask final : public IntrusiveList<NativeTask>::Item {
 private:
  friend class ::pw::async::Task;
  friend class ::pw::async::BasicDispatcher;
  friend class ::pw::async::test::backend::NativeFakeDispatcher;

  NativeTask() = default;
  explicit NativeTask(TaskFunction&& f) { func_ = std::move(f); }
  void operator()(Context& ctx) { func_(ctx); }
  void set_function(TaskFunction&& f) { func_ = std::move(f); }

  pw::chrono::SystemClock::time_point due_time() const { return due_time_; }
  void set_due_time(chrono::SystemClock::time_point due_time) {
    due_time_ = due_time;
  }
  std::optional<chrono::SystemClock::duration> interval() const {
    if (interval_ == chrono::SystemClock::duration::zero()) {
      return std::nullopt;
    }
    return interval_;
  }
  void set_interval(std::optional<chrono::SystemClock::duration> interval) {
    if (!interval.has_value()) {
      interval_ = chrono::SystemClock::duration::zero();
      return;
    }
    interval_ = *interval;
  }

  TaskFunction func_ = nullptr;
  pw::chrono::SystemClock::time_point due_time_;
  // A duration of 0 indicates that the task is not periodic.
  chrono::SystemClock::duration interval_ =
      chrono::SystemClock::duration::zero();
};

using NativeTaskHandle = NativeTask&;

}  // namespace pw::async::backend
