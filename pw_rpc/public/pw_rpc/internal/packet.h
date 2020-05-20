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

#include <cstddef>
#include <cstdint>

#include "pw_rpc_protos/packet.pwpb.h"
#include "pw_span/span.h"
#include "pw_status/status_with_size.h"

namespace pw::rpc::internal {

class Packet {
 public:
  // Parses a packet from a protobuf message. Missing or malformed fields take
  // their default values.
  static Packet FromBuffer(span<const std::byte> data);

  // Returns an empty packet with default values set.
  static constexpr Packet Empty() {
    return Packet(PacketType::kRpc, 0, 0, 0, {});
  }

  // Encodes the packet into its wire format. Returns the encoded size.
  StatusWithSize Encode(span<std::byte> buffer) const;

  bool is_control() const { return !is_rpc(); }
  bool is_rpc() const { return type_ == PacketType::kRpc; }

  PacketType type() const { return type_; }
  uint32_t channel_id() const { return channel_id_; }
  uint32_t service_id() const { return service_id_; }
  uint32_t method_id() const { return method_id_; }
  span<const std::byte> payload() const { return payload_; }

  void set_type(PacketType type) { type_ = type; }
  void set_channel_id(uint32_t channel_id) { channel_id_ = channel_id; }
  void set_service_id(uint32_t service_id) { service_id_ = service_id; }
  void set_method_id(uint32_t method_id) { method_id_ = method_id; }
  void set_payload(span<const std::byte> payload) { payload_ = payload; }

 private:
  constexpr Packet(PacketType type,
                   uint32_t channel_id,
                   uint32_t service_id,
                   uint32_t method_id,
                   span<const std::byte> payload)
      : type_(type),
        channel_id_(channel_id),
        service_id_(service_id),
        method_id_(method_id),
        payload_(payload) {}

  PacketType type_;
  uint32_t channel_id_;
  uint32_t service_id_;
  uint32_t method_id_;
  span<const std::byte> payload_;
};

}  // namespace pw::rpc::internal