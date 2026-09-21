#include "xziel/map_format.hpp"

#include <sstream>
#include <string>

namespace xziel {

namespace {

bool parseBool(
    int value,
    bool& output) noexcept {
    if (value == 0) {
        output = false;
        return true;
    }

    if (value == 1) {
        output = true;
        return true;
    }

    return false;
}

bool parseKind(
    const std::string& value,
    InteractionKind& kind) noexcept {
    if (value == "use") {
        kind = InteractionKind::Use;
    } else if (value == "door") {
        kind = InteractionKind::Door;
    } else if (value == "pickup") {
        kind = InteractionKind::Pickup;
    } else if (value == "weapon") {
        kind = InteractionKind::WeaponBuy;
    } else if (value == "perk") {
        kind = InteractionKind::Perk;
    } else if (value == "switch") {
        kind = InteractionKind::Switch;
    } else if (value == "quest") {
        kind = InteractionKind::QuestItem;
    } else if (value == "revive") {
        kind = InteractionKind::Revive;
    } else {
        return false;
    }

    return true;
}

bool onlyWhitespaceRemaining(
    std::istringstream& stream) noexcept {
    std::string extra;
    return !(stream >> extra);
}

} // namespace

bool parseMapText(
    std::string_view text,
    MapDefinition& destination,
    MapParseError& error) noexcept {
    destination = {};
    error = {};

    std::istringstream source{
        std::string(text)};

    std::string line;
    std::size_t lineNumber = 0;
    bool headerSeen = false;

    while (std::getline(source, line)) {
        ++lineNumber;

        const auto first =
            line.find_first_not_of(
                " 	");

        if (first == std::string::npos ||
            line[first] == '#') {
            continue;
        }

        std::istringstream record{
            line.substr(first)};

        std::string type;
        record >> type;

        if (!headerSeen) {
            if (type != "xziel_map") {
                error = {
                    MapParseErrorCode::MissingHeader,
                    lineNumber,
                };
                return false;
            }

            std::uint32_t version = 0;
            if (!(record >> version) ||
                !onlyWhitespaceRemaining(record)) {
                error = {
                    MapParseErrorCode::MalformedRecord,
                    lineNumber,
                };
                return false;
            }

            if (version != 1U) {
                error = {
                    MapParseErrorCode::UnsupportedVersion,
                    lineNumber,
                };
                return false;
            }

            headerSeen = true;
            continue;
        }

        if (type == "box") {
            if (destination.boxCount >=
                destination.boxes.size()) {
                error = {
                    MapParseErrorCode::CapacityExceeded,
                    lineNumber,
                };
                return false;
            }

            MapBoxDefinition box{};
            int visible = 0;
            int blockPlayer = 0;
            int blockZombies = 0;

            if (!(record >>
                  box.id >>
                  box.center.x >>
                  box.center.y >>
                  box.center.z >>
                  box.halfExtents.x >>
                  box.halfExtents.y >>
                  box.halfExtents.z >>
                  box.materialId >>
                  visible >>
                  blockPlayer >>
                  blockZombies) ||
                !onlyWhitespaceRemaining(record) ||
                !parseBool(visible, box.visible) ||
                !parseBool(blockPlayer, box.blocksPlayer) ||
                !parseBool(blockZombies, box.blocksZombies)) {
                error = {
                    MapParseErrorCode::MalformedRecord,
                    lineNumber,
                };
                return false;
            }

            destination.boxes[
                destination.boxCount++] =
                box;
            continue;
        }

        if (type == "door") {
            if (destination.doorCount >=
                destination.doors.size()) {
                error = {
                    MapParseErrorCode::CapacityExceeded,
                    lineNumber,
                };
                return false;
            }

            MapDoorEntity entity{};
            int startsOpen = 0;

            if (!(record >>
                  entity.door.id >>
                  entity.door.cost >>
                  startsOpen >>
                  entity.door.blocker.minimum.x >>
                  entity.door.blocker.minimum.y >>
                  entity.door.blocker.minimum.z >>
                  entity.door.blocker.maximum.x >>
                  entity.door.blocker.maximum.y >>
                  entity.door.blocker.maximum.z >>
                  entity.interaction.position.x >>
                  entity.interaction.position.y >>
                  entity.interaction.position.z >>
                  entity.interaction.maximumDistance >>
                  entity.interaction.minimumFacingDot >>
                  entity.interaction.priority >>
                  entity.interaction.holdSeconds) ||
                !onlyWhitespaceRemaining(record) ||
                !parseBool(
                    startsOpen,
                    entity.door.startsOpen)) {
                error = {
                    MapParseErrorCode::MalformedRecord,
                    lineNumber,
                };
                return false;
            }

            entity.interaction.id =
                entity.door.id;
            entity.interaction.kind =
                InteractionKind::Door;
            entity.interaction.cost =
                entity.door.cost;
            entity.interaction.enabled =
                !entity.door.startsOpen;

            destination.doors[
                destination.doorCount++] =
                entity;
            continue;
        }

        if (type == "window") {
            if (destination.windowCount >=
                destination.windows.size()) {
                error = {
                    MapParseErrorCode::CapacityExceeded,
                    lineNumber,
                };
                return false;
            }

            MapWindowEntity entity{};
            unsigned int maximumPlanks = 0U;

            if (!(record >>
                  entity.window.id >>
                  entity.window.blocker.minimum.x >>
                  entity.window.blocker.minimum.y >>
                  entity.window.blocker.minimum.z >>
                  entity.window.blocker.maximum.x >>
                  entity.window.blocker.maximum.y >>
                  entity.window.blocker.maximum.z >>
                  maximumPlanks >>
                  entity.window.barricade.zombieTearSeconds >>
                  entity.window.barricade.rebuildSeconds >>
                  entity.window.barricade.rebuildPointsPerPlank >>
                  entity.window.barricade.maximumRebuildPointsPerRound >>
                  entity.interaction.position.x >>
                  entity.interaction.position.y >>
                  entity.interaction.position.z >>
                  entity.interaction.maximumDistance >>
                  entity.interaction.minimumFacingDot >>
                  entity.interaction.priority) ||
                !onlyWhitespaceRemaining(record)) {
                error = {
                    MapParseErrorCode::MalformedRecord,
                    lineNumber,
                };
                return false;
            }

            if (maximumPlanks == 0U ||
                maximumPlanks > 255U) {
                error = {
                    MapParseErrorCode::MalformedRecord,
                    lineNumber,
                };
                return false;
            }

            entity.window.barricade.maximumPlanks =
                static_cast<std::uint8_t>(
                    maximumPlanks);

            entity.interaction.id =
                entity.window.id;
            entity.interaction.kind =
                InteractionKind::Use;
            entity.interaction.holdSeconds = 0.0f;
            entity.interaction.enabled = true;

            destination.windows[
                destination.windowCount++] =
                entity;
            continue;
        }

        if (type == "interaction") {
            if (destination.interactionCount >=
                destination.interactions.size()) {
                error = {
                    MapParseErrorCode::CapacityExceeded,
                    lineNumber,
                };
                return false;
            }

            InteractionTarget target{};
            std::string kindText;
            int enabled = 0;

            if (!(record >>
                  target.id >>
                  kindText >>
                  target.position.x >>
                  target.position.y >>
                  target.position.z >>
                  target.maximumDistance >>
                  target.minimumFacingDot >>
                  target.priority >>
                  target.holdSeconds >>
                  target.cost >>
                  enabled) ||
                !onlyWhitespaceRemaining(record) ||
                !parseKind(kindText, target.kind) ||
                !parseBool(enabled, target.enabled)) {
                error = {
                    MapParseErrorCode::MalformedRecord,
                    lineNumber,
                };
                return false;
            }

            destination.interactions[
                destination.interactionCount++] =
                target;
            continue;
        }

        error = {
            MapParseErrorCode::UnknownRecord,
            lineNumber,
        };
        return false;
    }

    if (!headerSeen) {
        error = {
            MapParseErrorCode::MissingHeader,
            lineNumber,
        };
        return false;
    }

    return true;
}

} // namespace xziel
