#pragma once

#include "xziel/map_runtime.hpp"

#include <cstddef>
#include <string_view>

namespace xziel {

enum class MapParseErrorCode : std::uint8_t {
    None,
    MissingHeader,
    UnsupportedVersion,
    UnknownRecord,
    MalformedRecord,
    CapacityExceeded,
};

struct MapParseError {
    MapParseErrorCode code = MapParseErrorCode::None;
    std::size_t line = 0;
};

[[nodiscard]] bool parseMapText(
    std::string_view text,
    MapDefinition& destination,
    MapParseError& error) noexcept;

} // namespace xziel
