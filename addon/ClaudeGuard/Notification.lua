-- Notification.lua
-- Non-blocking notification shown when Claude is idle but the player is in a protected context.

ClaudeGuard = ClaudeGuard or {}
ClaudeGuard.Notification = {}

local Notification = ClaudeGuard.Notification

local PULSE_MIN_ALPHA = 0.4
local PULSE_MAX_ALPHA = 1.0
local PULSE_SPEED = 1.5 -- full cycles per second

local soundPlayed = false

-- Notification frame
local notifFrame = CreateFrame("Frame", "ClaudeGuardNotifFrame", UIParent)
notifFrame:SetSize(280, 40)
notifFrame:SetPoint("TOP", UIParent, "TOP", 0, -40)
notifFrame:SetFrameStrata("HIGH")
notifFrame:Hide()

-- Border (draws first as the larger area, gold edge peeking out 1px)
local border = notifFrame:CreateTexture(nil, "BACKGROUND")
border:SetPoint("TOPLEFT", notifFrame, "TOPLEFT", -1, 1)
border:SetPoint("BOTTOMRIGHT", notifFrame, "BOTTOMRIGHT", 1, -1)
border:SetColorTexture(1, 0.82, 0, 0.6)

-- Background (draws on top, covering the center of the border)
local bg = notifFrame:CreateTexture(nil, "ARTWORK")
bg:SetAllPoints(notifFrame)
bg:SetColorTexture(0.1, 0.1, 0.1, 0.8)

-- Icon
local icon = notifFrame:CreateTexture(nil, "OVERLAY")
icon:SetSize(24, 24)
icon:SetPoint("LEFT", notifFrame, "LEFT", 10, 0)
icon:SetTexture("Interface\\Icons\\Spell_Holy_BorrowedTime")

-- Text
local text = notifFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
text:SetPoint("LEFT", icon, "RIGHT", 8, 0)
text:SetPoint("RIGHT", notifFrame, "RIGHT", -10, 0)
text:SetText("Claude is ready for a prompt")
text:SetTextColor(1, 0.82, 0)

-- Pulse animation via OnUpdate
local elapsed = 0
notifFrame:SetScript("OnUpdate", function(self, dt)
    elapsed = elapsed + dt
    local alpha = PULSE_MIN_ALPHA + (PULSE_MAX_ALPHA - PULSE_MIN_ALPHA) *
                  (0.5 + 0.5 * math.sin(elapsed * PULSE_SPEED * 2 * math.pi))
    self:SetAlpha(alpha)
end)

function Notification.Show()
    -- Play alert sound on first appearance
    if not soundPlayed then
        PlaySound(SOUNDKIT.RAID_WARNING or 8959)
        soundPlayed = true
    end
    elapsed = 0
    notifFrame:Show()
end

function Notification.Hide()
    notifFrame:Hide()
end

function Notification.IsShown()
    return notifFrame:IsShown()
end

function Notification.ResetSound()
    soundPlayed = false
end
