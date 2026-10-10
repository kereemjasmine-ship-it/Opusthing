-- ImportedPet (ModuleScript, ReplicatedStorage)
-- Drives any Blender-made void pet after it has been imported into Studio
-- (blender/export/VoidHydra.fbx and blender/pets/<Name>/export/<Name>.fbx).
-- It has the same interface as VoidHydra:
--   local pet = ImportedPet.new(ReplicatedStorage.PetModels.VoidPup)
--   pet.Model.Parent = workspace
--   pet:Update(feetCFrame, dt) -- every frame
--
-- MeshParts are recognised by the names the importer gives them, which come
-- from the Blender objects: body parts (Body, Head, Tail, WingL...), Circle*
-- (base rings and halos, spun), Shards* (orbiting bits), and a _Neon<Colour>
-- suffix on every glowing piece.

local ImportedPet = {}
ImportedPet.__index = ImportedPet

-- If the pet faces backwards after importing, change this to CFrame.Angles(0, math.pi, 0).
ImportedPet.Facing = CFrame.identity

-- Every glow colour used by the void pet family (same hexes as the Blender palettes).
local NEON_COLORS = {
	NeonMagenta = Color3.fromHex("e35cff"), -- VoidHydra
	NeonPink = Color3.fromHex("ff8bf0"), -- VoidHydra, VoidPup, ShadowBat, RuneGolem
	NeonViolet = Color3.fromHex("a64dff"), -- VoidHydra, VoidPup
	NeonCyan = Color3.fromHex("4de1ff"), -- ShadowBat
	NeonIce = Color3.fromHex("4d8eff"), -- CrystalFox
	NeonLilac = Color3.fromHex("7d5eff"), -- CrystalFox
	NeonTeal = Color3.fromHex("3ff2c8"), -- NebulaOwl
	NeonGold = Color3.fromHex("ffcf4d"), -- NebulaOwl
	NeonAmber = Color3.fromHex("ff9a3c"), -- RuneGolem
}

local function kindOf(name: string): string
	if name == "Circle_NeonViolet" then
		return "innerRing"
	elseif name:find("^Circle") then
		return "ring"
	elseif name:find("^Shards") then
		return "shards"
	end
	return "body"
end

function ImportedPet.new(template: Model)
	local self = setmetatable({}, ImportedPet)
	local model = template:Clone()
	self.Model = model
	self._time = 0
	self._entries = {}
	self._parts = {}
	self._cframes = {}
	self._neon = {}

	-- The pet's origin is the centre of its base ring if it has one (the hydra's
	-- tail pushes its bounding box off-centre), else the bounding box centre.
	local circle = model:FindFirstChild("Circle_NeonPink", true)
	if not circle then
		for _, d in model:GetDescendants() do
			if d:IsA("BasePart") and d.Name:find("^Circle_") then
				circle = d
				break
			end
		end
	end
	local boxCFrame, boxSize = model:GetBoundingBox()
	local bottom = boxCFrame.Position.Y - boxSize.Y / 2
	local centre = if circle and circle:IsA("BasePart") then circle.Position else boxCFrame.Position
	local origin = CFrame.new(centre.X, bottom, centre.Z) * boxCFrame.Rotation

	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = true
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			local suffix = d.Name:match("_(Neon%a+)$")
			if suffix and NEON_COLORS[suffix] then
				d.Material = Enum.Material.Neon
				d.Color = NEON_COLORS[suffix]
				d.CastShadow = false
				table.insert(self._neon, d)
			end
			table.insert(self._entries, { kind = kindOf(d.Name), offset = origin:ToObjectSpace(d.CFrame) })
			table.insert(self._parts, d)
			table.insert(self._cframes, d.CFrame)
		end
	end
	return self
end

function ImportedPet:Update(rootCFrame: CFrame, dt: number)
	self._time += dt
	local t = self._time
	local groups = {
		body = CFrame.new(0, math.sin(t * 2.2) * 0.05, 0),
		ring = CFrame.Angles(0, t * 0.6, 0),
		innerRing = CFrame.Angles(0, -t * 1.1, 0),
		shards = CFrame.new(0, math.sin(t * 2) * 0.15, 0) * CFrame.Angles(0, t * 0.4, 0),
	}
	local base = rootCFrame * ImportedPet.Facing
	for i, entry in self._entries do
		self._cframes[i] = base * groups[entry.kind] * entry.offset
	end
	workspace:BulkMoveTo(self._parts, self._cframes, Enum.BulkMoveMode.FireCFrameChanged)

	local glow = 0.15 + 0.15 * math.sin(t * 3)
	for _, part in self._neon do
		part.Transparency = glow
	end
end

function ImportedPet:Destroy()
	self.Model:Destroy()
end

return ImportedPet
