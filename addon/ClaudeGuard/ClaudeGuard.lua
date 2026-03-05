-- ClaudeGuard.lua
-- Core controller: reads CompanionData, manages state, wires up modules and slash commands.

ClaudeGuard = ClaudeGuard or {}

local addonName = "ClaudeGuard"
local VERSION = "1.0.0"
local disabled = false
local currentStatus = "unknown"

-- Settings defaults
local defaults = {
    soundEnabled = true,
    notifPoint = nil,
    notifRelPoint = nil,
    notifX = nil,
    notifY = nil,
}

local function InitSettings()
    if not ClaudeGuardSettings then
        ClaudeGuardSettings = {}
    end
    for k, v in pairs(defaults) do
        if ClaudeGuardSettings[k] == nil then
            ClaudeGuardSettings[k] = v
        end
    end
end

function ClaudeGuard.ShouldPlaySound()
    return ClaudeGuardSettings and ClaudeGuardSettings.soundEnabled
end

-- Called by PlayerState when protected state changes (e.g., combat ends)
function ClaudeGuard.OnProtectedStateChanged()
    if disabled then return end
    ClaudeGuard.EvaluateState()
end

-- Decide whether to show Blocker, Notification, or nothing
function ClaudeGuard.EvaluateState()
    if disabled then
        ClaudeGuard.Blocker.Hide()
        ClaudeGuard.Notification.Hide()
        return
    end

    local shouldBlock = (currentStatus == "idle" or currentStatus == "closed")

    if not shouldBlock then
        ClaudeGuard.Blocker.Hide()
        ClaudeGuard.Notification.Hide()
        ClaudeGuard.Notification.ResetSound()
        return
    end

    if ClaudeGuard.PlayerState.IsProtected() then
        ClaudeGuard.Blocker.Hide()
        ClaudeGuard.Notification.Show()
    else
        ClaudeGuard.Notification.Hide()
        ClaudeGuard.Blocker.Show()
    end
end

-- Used by Blocker to check if it should re-show after snooze
function ClaudeGuard.ShouldBlock()
    if disabled then return false end
    local shouldBlock = (currentStatus == "idle" or currentStatus == "closed")
    return shouldBlock and not ClaudeGuard.PlayerState.IsProtected()
end

-- Print helper
local function Print(msg)
    DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard|r: " .. msg)
end

-- Initialization on ADDON_LOADED
local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", function(self, event, arg1)
    if event == "ADDON_LOADED" and arg1 == addonName then
        self:UnregisterEvent("ADDON_LOADED")

        InitSettings()
        ClaudeGuard.PlayerState.Init()
        ClaudeGuard.Notification.RestorePosition()

        -- Read status from CompanionData.lua (written by companion script)
        if CLAUDEGUARD_COMPANION_STATUS then
            currentStatus = CLAUDEGUARD_COMPANION_STATUS
        else
            currentStatus = "working"
        end

        ClaudeGuard.EvaluateState()
        Print("v" .. VERSION .. " loaded. Status: " .. currentStatus .. ". Type /cg for help.")
    end
end)

-- Slash commands
SLASH_CLAUDEGUARD1 = "/cg"
SLASH_CLAUDEGUARD2 = "/claudeguard"

SlashCmdList["CLAUDEGUARD"] = function(msg)
    local args = strtrim(msg)
    local cmd = args:lower()

    -- /cg with no args — compact status summary
    if cmd == "" then
        local protectedStr = ClaudeGuard.PlayerState.IsProtected() and "yes" or "no"
        local snoozeUsed, snoozeMax = ClaudeGuard.Blocker.GetSnoozeInfo()
        local soundStr = ClaudeGuardSettings.soundEnabled and "on" or "off"
        Print("Claude: " .. currentStatus ..
              " | Protected: " .. protectedStr ..
              " | Snoozes: " .. snoozeUsed .. "/" .. snoozeMax ..
              " | Sound: " .. soundStr ..
              (disabled and " | DISABLED" or ""))
        return
    end

    if cmd == "status" then
        local protectedStr = ClaudeGuard.PlayerState.IsProtected() and "yes" or "no"
        local blockerStr = ClaudeGuard.Blocker.IsShown() and "shown" or "hidden"
        local notifStr = ClaudeGuard.Notification.IsShown() and "shown" or "hidden"
        local snoozeUsed, snoozeMax = ClaudeGuard.Blocker.GetSnoozeInfo()
        Print("Status:")
        DEFAULT_CHAT_FRAME:AddMessage("  Claude: " .. currentStatus)
        DEFAULT_CHAT_FRAME:AddMessage("  Protected: " .. protectedStr)
        DEFAULT_CHAT_FRAME:AddMessage("  Blocker: " .. blockerStr)
        DEFAULT_CHAT_FRAME:AddMessage("  Notification: " .. notifStr)
        DEFAULT_CHAT_FRAME:AddMessage("  Snoozes: " .. snoozeUsed .. "/" .. snoozeMax)
        DEFAULT_CHAT_FRAME:AddMessage("  Sound: " .. (ClaudeGuardSettings.soundEnabled and "on" or "off"))
        DEFAULT_CHAT_FRAME:AddMessage("  Disabled: " .. (disabled and "yes" or "no"))

    elseif cmd == "sound on" then
        ClaudeGuardSettings.soundEnabled = true
        Print("Sound enabled.")

    elseif cmd == "sound off" then
        ClaudeGuardSettings.soundEnabled = false
        Print("Sound disabled.")

    elseif cmd:match("^snooze") then
        if disabled then
            Print("ClaudeGuard is disabled.")
            return
        end
        local secs = tonumber(cmd:match("^snooze%s+(%d+)"))
        if secs then
            secs = math.min(secs, 300)
            if ClaudeGuard.Blocker.Snooze(secs) then
                Print("Snoozed for " .. secs .. " seconds.")
            else
                Print("No snoozes remaining.")
            end
        else
            if ClaudeGuard.Blocker.Snooze() then
                Print("Snoozed for 2 minutes.")
            else
                Print("No snoozes remaining.")
            end
        end

    elseif cmd == "reset" then
        ClaudeGuard.Blocker.ResetSnoozes()
        Print("Snooze counter reset.")

    elseif cmd == "disable" then
        disabled = true
        ClaudeGuard.Blocker.Hide()
        ClaudeGuard.Notification.Hide()
        Print("Disabled until next login/reload.")

    elseif cmd == "enable" then
        disabled = false
        ClaudeGuard.EvaluateState()
        Print("Re-enabled.")

    elseif cmd == "help" then
        Print("Commands:")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg — Compact status summary")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg status — Detailed status")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg snooze [secs] — Snooze blocker (default 120s, max 300s)")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg reset — Reset snooze counter")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg sound on|off — Toggle sounds")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg disable — Disable until login/reload")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg enable — Re-enable")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg help — This help")
    else
        Print("Unknown command. Type /cg help for options.")
    end
end
