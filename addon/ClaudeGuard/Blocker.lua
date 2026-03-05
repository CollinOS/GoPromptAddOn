-- Blocker.lua
-- Full-screen overlay that blocks all gameplay when Claude Code is idle.

ClaudeGuard = ClaudeGuard or {}
ClaudeGuard.Blocker = {}

local Blocker = ClaudeGuard.Blocker

local SNOOZE_DURATION = 120 -- seconds (default, can be overridden)
local MAX_SNOOZES = 3

local snoozeCount = 0
local snoozedUntil = 0

-- Main blocker frame
local blockerFrame = CreateFrame("Frame", "ClaudeGuardBlockerFrame", UIParent)
blockerFrame:SetFrameStrata("TOOLTIP")
blockerFrame:SetAllPoints(UIParent)
blockerFrame:EnableMouse(true)
blockerFrame:Hide()

-- Semi-transparent dark background — game world shows through dimly
local bg = blockerFrame:CreateTexture(nil, "BACKGROUND")
bg:SetAllPoints(blockerFrame)
bg:SetColorTexture(0, 0, 0, 0.7)

-- Content container for vertical centering
local content = CreateFrame("Frame", nil, blockerFrame)
content:SetSize(400, 280)
content:SetPoint("CENTER", blockerFrame, "CENTER", 0, 0)

-- Icon (using built-in WoW texture)
local icon = content:CreateTexture(nil, "OVERLAY")
icon:SetSize(64, 64)
icon:SetPoint("TOP", content, "TOP", 0, 0)
icon:SetTexture("Interface\\Icons\\Spell_Holy_BorrowedTime")

-- Icon pulse animation
local iconAnimGroup = icon:CreateAnimationGroup()
iconAnimGroup:SetLooping("BOUNCE")
local iconFade = iconAnimGroup:CreateAnimation("Alpha")
iconFade:SetFromAlpha(1.0)
iconFade:SetToAlpha(0.4)
iconFade:SetDuration(1.5)
iconFade:SetSmoothing("IN_OUT")

-- Main message text
local mainText = content:CreateFontString(nil, "OVERLAY", "GameFontNormalHuge")
mainText:SetPoint("TOP", icon, "BOTTOM", 0, -16)
mainText:SetText("Claude Code is waiting for a prompt.\nGet back to work!")
mainText:SetTextColor(1, 0.82, 0)
mainText:SetJustifyH("CENTER")

-- Subtitle text
local subText = content:CreateFontString(nil, "OVERLAY", "GameFontNormal")
subText:SetPoint("TOP", mainText, "BOTTOM", 0, -12)
subText:SetText("Give Claude a task — this will dismiss automatically.")
subText:SetTextColor(0.7, 0.7, 0.7)

-- Idle duration text (updated on a 1-second tick)
local idleText = content:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
idleText:SetPoint("TOP", subText, "BOTTOM", 0, -8)
idleText:SetTextColor(0.5, 0.5, 0.5)

-- Snooze button
local snoozeBtn = CreateFrame("Button", "ClaudeGuardSnoozeBtn", content, "UIPanelButtonTemplate")
snoozeBtn:SetSize(220, 28)
snoozeBtn:SetPoint("TOP", idleText, "BOTTOM", 0, -16)

-- Reload button
local reloadBtn = CreateFrame("Button", "ClaudeGuardReloadBtn", content, "UIPanelButtonTemplate")
reloadBtn:SetSize(220, 28)
reloadBtn:SetPoint("TOP", snoozeBtn, "BOTTOM", 0, -6)
reloadBtn:SetText("Reload UI")
reloadBtn:SetScript("OnClick", function()
    ReloadUI()
end)

local function FormatDuration(seconds)
    if seconds < 60 then
        return seconds .. "s"
    elseif seconds < 3600 then
        local m = math.floor(seconds / 60)
        local s = seconds % 60
        if s > 0 then
            return m .. "m " .. s .. "s"
        end
        return m .. "m"
    else
        local h = math.floor(seconds / 3600)
        local m = math.floor((seconds % 3600) / 60)
        return h .. "h " .. m .. "m"
    end
end

-- Update idle duration text on a 1-second tick
local idleTickElapsed = 0
blockerFrame:SetScript("OnUpdate", function(self, dt)
    idleTickElapsed = idleTickElapsed + dt
    if idleTickElapsed < 1 then return end
    idleTickElapsed = 0

    local ts = CLAUDEGUARD_COMPANION_TIMESTAMP
    if ts and ts > 0 then
        local elapsed = time() - ts
        if elapsed > 0 then
            idleText:SetText("Idle for " .. FormatDuration(elapsed))
        else
            idleText:SetText("")
        end
    else
        idleText:SetText("")
    end
end)

local function UpdateSnoozeButton()
    local remaining = MAX_SNOOZES - snoozeCount
    if remaining > 0 then
        snoozeBtn:SetText("Snooze " .. math.floor(SNOOZE_DURATION / 60) .. " min (" .. remaining .. " left)")
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

function Blocker.Show()
    if snoozedUntil > GetTime() then
        return
    end
    UpdateSnoozeButton()
    idleTickElapsed = 0
    blockerFrame:Show()
    iconAnimGroup:Play()

    -- Play sound if enabled
    if ClaudeGuard.ShouldPlaySound and ClaudeGuard.ShouldPlaySound() then
        PlaySound(SOUNDKIT.READY_CHECK or 8960)
    end
end

function Blocker.Hide()
    blockerFrame:Hide()
    iconAnimGroup:Stop()
end

function Blocker.IsShown()
    return blockerFrame:IsShown()
end

function Blocker.Snooze(duration)
    if duration then
        SNOOZE_DURATION = math.min(duration, 300)
    end
    return DoSnooze()
end

function Blocker.ResetSnoozes()
    snoozeCount = 0
    UpdateSnoozeButton()
end

function Blocker.GetSnoozeInfo()
    return snoozeCount, MAX_SNOOZES, snoozedUntil
end
