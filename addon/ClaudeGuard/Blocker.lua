-- Blocker.lua
-- Full-screen overlay that blocks all gameplay when Claude Code is idle.

ClaudeGuard = ClaudeGuard or {}
ClaudeGuard.Blocker = {}

local Blocker = ClaudeGuard.Blocker

local SNOOZE_DURATION = 120 -- seconds
local MAX_SNOOZES = 3

local snoozeCount = 0
local snoozedUntil = 0

-- Main blocker frame
local blockerFrame = CreateFrame("Frame", "ClaudeGuardBlockerFrame", UIParent)
blockerFrame:SetFrameStrata("TOOLTIP")
blockerFrame:SetAllPoints(UIParent)
blockerFrame:EnableMouse(true)
blockerFrame:EnableKeyboard(true)
blockerFrame:SetPropagateKeyboardInput(false)
blockerFrame:Hide()

-- Dark background overlay
local bg = blockerFrame:CreateTexture(nil, "BACKGROUND")
bg:SetAllPoints(blockerFrame)
bg:SetColorTexture(0, 0, 0, 0.85)

-- Main message text
local mainText = blockerFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalHuge")
mainText:SetPoint("CENTER", blockerFrame, "CENTER", 0, 60)
mainText:SetText("Claude Code is waiting for a prompt.\nGet back to work!")
mainText:SetTextColor(1, 0.82, 0)
mainText:SetJustifyH("CENTER")

-- Subtitle text
local subText = blockerFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
subText:SetPoint("TOP", mainText, "BOTTOM", 0, -16)
subText:SetText("Give Claude a task, then /reload to dismiss.")
subText:SetTextColor(0.7, 0.7, 0.7)

-- Icon (using built-in WoW texture)
local icon = blockerFrame:CreateTexture(nil, "OVERLAY")
icon:SetSize(64, 64)
icon:SetPoint("BOTTOM", mainText, "TOP", 0, 16)
icon:SetTexture("Interface\\Icons\\Spell_Holy_BorrowedTime")

-- Snooze button
local snoozeBtn = CreateFrame("Button", "ClaudeGuardSnoozeBtn", blockerFrame, "UIPanelButtonTemplate")
snoozeBtn:SetSize(200, 30)
snoozeBtn:SetPoint("TOP", subText, "BOTTOM", 0, -24)

local function UpdateSnoozeButton()
    local remaining = MAX_SNOOZES - snoozeCount
    if remaining > 0 then
        snoozeBtn:SetText("I need 2 more minutes (" .. remaining .. " left)")
        snoozeBtn:Enable()
    else
        snoozeBtn:SetText("No snoozes remaining")
        snoozeBtn:Disable()
    end
end

local function DoSnooze()
    if snoozeCount >= MAX_SNOOZES then
        return false
    end
    snoozeCount = snoozeCount + 1
    snoozedUntil = GetTime() + SNOOZE_DURATION
    Blocker.Hide()
    UpdateSnoozeButton()

    -- Schedule re-show after snooze expires
    C_Timer.After(SNOOZE_DURATION, function()
        if ClaudeGuard.ShouldBlock and ClaudeGuard.ShouldBlock() then
            Blocker.Show()
        end
    end)
    return true
end

snoozeBtn:SetScript("OnClick", function()
    DoSnooze()
end)

-- Eat all key presses (frame has keyboard enabled + propagation disabled)
blockerFrame:SetScript("OnKeyDown", function(self, key)
    -- Do nothing — input is consumed
end)

function Blocker.Show()
    -- Check snooze
    if snoozedUntil > GetTime() then
        return
    end
    UpdateSnoozeButton()
    blockerFrame:Show()
end

function Blocker.Hide()
    blockerFrame:Hide()
end

function Blocker.IsShown()
    return blockerFrame:IsShown()
end

function Blocker.Snooze()
    return DoSnooze()
end

function Blocker.GetSnoozeInfo()
    return snoozeCount, MAX_SNOOZES, snoozedUntil
end
