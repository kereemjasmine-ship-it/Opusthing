-- PetFollower (LocalScript, StarterPlayerScripts)
-- Gives every player in the server a pet that follows them.
-- Pet models imported from Blender go in a ReplicatedStorage folder named
-- PetModels (VoidPup, ShadowBat, CrystalFox, NebulaOwl, RuneGolem, VoidHydra).
-- A player's "EquippedPet" attribute picks one (set it from the server); with
-- no attribute they get DEFAULT_PET. Without PetModels it falls back to a Model
-- named VoidHydraModel in ReplicatedStorage, then to the Part-built hydra.
-- This is a stand-in until the game's own pet system equips these models.
-- Pets are built and animated on each client, so movement is smooth and
-- costs the server nothing.

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local VoidHydra = require(ReplicatedStorage:WaitForChild("VoidHydra"))
local ImportedPet = require(ReplicatedStorage:WaitForChild("ImportedPet"))

local DEFAULT_PET = "VoidHydra"

local FOLLOW_OFFSET = Vector3.new(4.5, 0, 4) -- studs: right of and behind the player
local FOLLOW_SPEED = 8 -- higher = snappier
local MAX_DRAW_DISTANCE = 250 -- skip animating pets this far from the camera
local PET_CONFIG = { Scale = 0.35 }

local folder = Instance.new("Folder")
folder.Name = "ClientPets"
folder.Parent = workspace

local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude

local active = {} -- [Player] = { pet, hrp, cframe }

local function refreshFilter()
	local ignore = { folder }
	for _, player in Players:GetPlayers() do
		if player.Character then
			table.insert(ignore, player.Character)
		end
	end
	rayParams.FilterDescendantsInstances = ignore
end

local function removePet(player: Player)
	local entry = active[player]
	if entry then
		entry.pet:Destroy()
		active[player] = nil
	end
end

local function templateFor(player: Player): Model?
	local models = ReplicatedStorage:FindFirstChild("PetModels")
	local wanted = tostring(player:GetAttribute("EquippedPet") or DEFAULT_PET)
	local model = models and models:FindFirstChild(wanted)
	if model and model:IsA("Model") then
		return model
	end
	local fallback = ReplicatedStorage:FindFirstChild("VoidHydraModel")
	return if fallback and fallback:IsA("Model") then fallback else nil
end

local function addPet(player: Player, character: Model)
	removePet(player)
	local hrp = character:WaitForChild("HumanoidRootPart", 10)
	if not hrp or not character.Parent then
		return
	end
	removePet(player) -- another addPet may have finished while we waited
	local template = templateFor(player)
	local pet = if template then ImportedPet.new(template) else VoidHydra.new(PET_CONFIG)
	pet.Model.Name = player.Name .. "_Pet"
	pet.Model.Parent = folder
	active[player] = { pet = pet, hrp = hrp, cframe = nil }
	refreshFilter()
end

local function watch(player: Player)
	player.CharacterAdded:Connect(function(character)
		task.spawn(addPet, player, character)
	end)
	player.CharacterRemoving:Connect(function()
		removePet(player)
	end)
	player:GetAttributeChangedSignal("EquippedPet"):Connect(function()
		if player.Character then
			task.spawn(addPet, player, player.Character)
		end
	end)
	if player.Character then
		task.spawn(addPet, player, player.Character)
	end
end

for _, player in Players:GetPlayers() do
	watch(player)
end
Players.PlayerAdded:Connect(watch)
Players.PlayerRemoving:Connect(removePet)

RunService.RenderStepped:Connect(function(dt)
	local camera = workspace.CurrentCamera
	local alpha = 1 - math.exp(-FOLLOW_SPEED * dt)

	for player, entry in active do
		local hrp = entry.hrp
		if not hrp.Parent then
			continue
		end

		local goal = (hrp.CFrame * CFrame.new(FOLLOW_OFFSET)).Position
		if camera and (goal - camera.CFrame.Position).Magnitude > MAX_DRAW_DISTANCE then
			continue
		end

		-- stand on whatever is below the follow point
		local hit = workspace:Raycast(goal + Vector3.new(0, 6, 0), Vector3.new(0, -40, 0), rayParams)
		local groundY = if hit then hit.Position.Y else hrp.Position.Y - 3
		goal = Vector3.new(goal.X, groundY, goal.Z)

		local look = hrp.CFrame.LookVector * Vector3.new(1, 0, 1)
		if look.Magnitude < 1e-3 then
			look = Vector3.new(0, 0, -1)
		end
		local target = CFrame.lookAt(goal, goal + look.Unit)

		entry.cframe = if entry.cframe then entry.cframe:Lerp(target, alpha) else target
		entry.pet:Update(entry.cframe, dt)
	end
end)
