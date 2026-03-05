-- PlayerState.lua
-- Determines if the player is in a "protected" context where blocking would be disruptive.

ClaudeGuard = ClaudeGuard or {}
ClaudeGuard.PlayerState = {}

local PlayerState = ClaudeGuard.PlayerState

-- Cached state, updated via events
local inCombat = false
local inProtectedInstance = false

local frame = CreateFrame("Frame")

local function UpdateInstanceState()
    local inInstance, instanceType = IsInInstance()
    -- Protected instance types: party (dungeon), raid, pvp (battleground), arena
    inProtectedInstance = inInstance and (
        instanceType == "party" or
        instanceType == "raid" or
        instanceType == "pvp" or
        instanceType == "arena"
    )
end

local function OnEvent(self, event, ...)
    if event == "PLAYER_REGEN_DISABLED" then
        inCombat = true
    elseif event == "PLAYER_REGEN_ENABLED" then
        inCombat = false
        -- Combat just ended — notify core to re-evaluate (may need to show blocker)
        if ClaudeGuard.OnProtectedStateChanged then
            ClaudeGuard.OnProtectedStateChanged()
        end
    elseif event == "ZONE_CHANGED_NEW_AREA" then
        UpdateInstanceState()
        if ClaudeGuard.OnProtectedStateChanged then
            ClaudeGuard.OnProtectedStateChanged()
        end
    elseif event == "UPDATE_BATTLEFIELD_STATUS" then
        UpdateInstanceState()
        if ClaudeGuard.OnProtectedStateChanged then
            ClaudeGuard.OnProtectedStateChanged()
        end
    end
end

frame:RegisterEvent("PLAYER_REGEN_DISABLED")
frame:RegisterEvent("PLAYER_REGEN_ENABLED")
frame:RegisterEvent("ZONE_CHANGED_NEW_AREA")
frame:RegisterEvent("UPDATE_BATTLEFIELD_STATUS")
frame:SetScript("OnEvent", OnEvent)

function PlayerState.IsProtected()
    return inCombat or inProtectedInstance
end

function PlayerState.Init()
    -- Set initial state on load
    inCombat = UnitAffectingCombat("player")
    UpdateInstanceState()
end
