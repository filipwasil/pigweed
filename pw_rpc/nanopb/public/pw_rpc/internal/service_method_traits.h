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

#include "pw_rpc/internal/nanopb_method.h"

namespace pw::rpc::internal {

// Identifies a base class from a member function it defines. This should be
// used with decltype to retrieve the base class.
template <typename T, typename U>
T BaseFromMember(U T::*);

// Gets information about a service and method at compile-time. Uses a pointer
// to a member function of the service implementation to identify the service
// class, generated service class, and Method object. This class is friended by
// the generated service classes to give it access to the internal method list.
template <typename Service, uint32_t method_id>
class ServiceMethodTraits {
 public:
  ServiceMethodTraits() = delete;

  // Type of the generic service base class.
  using BaseService =
      decltype(BaseFromMember(&Service::_PwRpcInternalGeneratedBase));

  // Reference to the Method object corresponding to this method.
  static constexpr const NanopbMethod& method() {
    return *BaseService::NanopbMethodFor(method_id);
  }

  static_assert(BaseService::NanopbMethodFor(method_id) != nullptr,
                "The selected function is not an RPC service method");
};

}  // namespace pw::rpc::internal
