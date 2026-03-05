-- ClaudeGuard.lua
-- Core controller: reads SavedVariables, manages state, wires up modules and slash commands.

ClaudeGuard = ClaudeGuard or {}

local addonName = "ClaudeGuard"
local disabled = false
local currentStatus = "unknown"

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
        -- Claude is working — hide everything
        ClaudeGuard.Blocker.Hide()
        ClaudeGuard.Notification.Hide()
        ClaudeGuard.Notification.ResetSound()
        return
    end

    -- Claude is idle/closed — check if player is protected
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

-- Initialization on ADDON_LOADED
local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", function(self, event, arg1)
    if event == "ADDON_LOADED" and arg1 == addonName then
        self:UnregisterEvent("ADDON_LOADED")

        -- Initialize PlayerState (read current combat/instance state)
        ClaudeGuard.PlayerState.Init()

        -- Read status from CompanionData.lua (written by companion script)
        if CLAUDEGUARD_COMPANION_STATUS then
            currentStatus = CLAUDEGUARD_COMPANION_STATUS
        else
            -- No data from companion yet — default to working (don't block)
            currentStatus = "working"
        end

        ClaudeGuard.EvaluateState()

        -- Print load message
        DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard|r loaded. Status: " .. currentStatus .. ". Type /cg for commands.")
    end
end)

-- Slash commands
SLASH_CLAUDEGUARD1 = "/cg"
SLASH_CLAUDEGUARD2 = "/claudeguard"

SlashCmdList["CLAUDEGUARD"] = function(msg)
    local cmd = strtrim(msg):lower()

    if cmd == "status" then
        local protectedStr = ClaudeGuard.PlayerState.IsProtected() and "yes" or "no"
        local blockerStr = ClaudeGuard.Blocker.IsShown() and "shown" or "hidden"
        local notifStr = ClaudeGuard.Notification.IsShown() and "shown" or "hidden"
        local snoozeUsed, snoozeMax = ClaudeGuard.Blocker.GetSnoozeInfo()
        DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard Status:|r")
        DEFAULT_CHAT_FRAME:AddMessage("  Claude: " .. currentStatus)
        DEFAULT_CHAT_FRAME:AddMessage("  Protected: " .. protectedStr)
        DEFAULT_CHAT_FRAME:AddMessage("  Blocker: " .. blockerStr)
        DEFAULT_CHAT_FRAME:AddMessage("  Notification: " .. notifStr)
        DEFAULT_CHAT_FRAME:AddMessage("  Snoozes used: " .. snoozeUsed .. "/" .. snoozeMax)
        DEFAULT_CHAT_FRAME:AddMessage("  Disabled: " .. (disabled and "yes" or "no"))

    elseif cmd == "snooze" then
        if disabled then
            DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard|r is disabled.")
            return
        end
        if ClaudeGuard.Blocker.Snooze() then
            DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard|r: Snoozed for 2 minutes.")
        else
            DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard|r: No snoozes remaining.")
        end

    elseif cmd == "disable" then
        disabled = true
        ClaudeGuard.Blocker.Hide()
        ClaudeGuard.Notification.Hide()
        DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard|r disabled until next login/reload.")

    elseif cmd == "enable" then
        disabled = false
        ClaudeGuard.EvaluateState()
        DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard|r re-enabled.")

    else
        DEFAULT_CHAT_FRAME:AddMessage("|cFFFFD100ClaudeGuard Commands:|r")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg status  - Show current status")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg snooze  - Snooze blocker for 2 minutes")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg disable - Disable until next login")
        DEFAULT_CHAT_FRAME:AddMessage("  /cg enable  - Re-enable after disable")
    end
end
