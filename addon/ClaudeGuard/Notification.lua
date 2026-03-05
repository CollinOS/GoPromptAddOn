-- Notification.lua
-- Non-blocking notification shown when Claude is idle but the player is in a protected context.

ClaudeGuard = ClaudeGuard or {}
ClaudeGuard.Notification = {}

local Notification = ClaudeGuard.Notification

local PULSE_MIN_ALPHA = 0.5
local PULSE_MAX_ALPHA = 1.0
local PULSE_SPEED = 1.0 -- full cycles per second

local soundPlayed = false

-- Notification frame — draggable
local notifFrame = CreateFrame("Frame", "ClaudeGuardNotifFrame", UIParent)
notifFrame:SetSize(280, 40)
notifFrame:SetPoint("TOP", UIParent, "TOP", 0, -120) -- below error frame and boss frames
notifFrame:SetFrameStrata("HIGH")
notifFrame:SetMovable(true)
notifFrame:EnableMouse(true)
notifFrame:RegisterForDrag("LeftButton")
notifFrame:SetScript("OnDragStart", function(self) self:StartMoving() end)
notifFrame:SetScript("OnDragStop", function(self)
    self:StopMovingOrSizing()
    -- Save position to settings
    if ClaudeGuardSettings then
        local point, _, relPoint, x, y = self:GetPoint()
        ClaudeGuardSettings.notifPoint = point
        ClaudeGuardSettings.notifRelPoint = relPoint
        ClaudeGuardSettings.notifX = x
        ClaudeGuardSettings.notifY = y
    end
end)
notifFrame:Hide()

-- Border glow (outer frame, gold)
local border = notifFrame:CreateTexture(nil, "BACKGROUND")
border:SetPoint("TOPLEFT", notifFrame, "TOPLEFT", -2, 2)
border:SetPoint("BOTTOMRIGHT", notifFrame, "BOTTOMRIGHT", 2, -2)
border:SetColorTexture(1, 0.82, 0, 0.5)

-- Border pulse animation
local borderAnimGroup = border:CreateAnimationGroup()
borderAnimGroup:SetLooping("BOUNCE")
local borderFade = borderAnimGroup:CreateAnimation("Alpha")
borderFade:SetFromAlpha(0.5)
borderFade:SetToAlpha(0.15)
borderFade:SetDuration(1.5)
borderFade:SetSmoothing("IN_OUT")

-- Background
local bg = notifFrame:CreateTexture(nil, "ARTWORK")
bg:SetAllPoints(notifFrame)
bg:SetColorTexture(0.1, 0.1, 0.1, 0.85)

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

-- Gentle frame pulse via OnUpdate (supplements the border animation)
local elapsed = 0
notifFrame:SetScript("OnUpdate", function(self, dt)
    elapsed = elapsed + dt
    local alpha = PULSE_MIN_ALPHA + (PULSE_MAX_ALPHA - PULSE_MIN_ALPHA) *
                  (0.5 + 0.5 * math.sin(elapsed * PULSE_SPEED * 2 * math.pi))
    self:SetAlpha(alpha)
end)

-- Restore saved position
function Notification.RestorePosition()
    if ClaudeGuardSettings and ClaudeGuardSettings.notifPoint then
        notifFrame:ClearAllPoints()
        notifFrame:SetPoint(
            ClaudeGuardSettings.notifPoint,
            UIParent,
            ClaudeGuardSettings.notifRelPoint,
            ClaudeGuardSettings.notifX,
            ClaudeGuardSettings.notifY
        )
    end
end

function Notification.Show()
    if not soundPlayed then
        if ClaudeGuard.ShouldPlaySound and ClaudeGuard.ShouldPlaySound() then
            PlaySound(SOUNDKIT.IG_PLAYER_INVITE or 880)
        end
        soundPlayed = true
    end
    elapsed = 0
    notifFrame:Show()
    borderAnimGroup:Play()
end

function Notification.Hide()
    notifFrame:Hide()
    borderAnimGroup:Stop()
end

function Notification.IsShown()
    return notifFrame:IsShown()
end

function Notification.ResetSound()
    soundPlayed = false
end
