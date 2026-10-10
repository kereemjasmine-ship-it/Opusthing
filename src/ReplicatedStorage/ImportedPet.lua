-- ImportedPet (ModuleScript, ReplicatedStorage)
-- Drives the Blender-made Void Hydra after it has been imported into Studio
-- (blender/export/VoidHydra.fbx). It has the same interface as VoidHydra:
--   local pet = ImportedPet.new(ReplicatedStorage.VoidHydraModel)
--   pet.Model.Parent = workspace
--   pet:Update(feetCFrame, dt) -- every frame
--
-- MeshParts are recognised by the names the importer gives them, which come
-- from the Blender objects: Body, Tail, Neck1..5, Circle_*, Shards_*, and a
-- _NeonPink / _NeonMagenta / _NeonViolet suffix on every glowing piece.

local ImportedPet = {}
ImportedPet.__index = ImportedPet

-- If the pet faces backwards after importing, change this to CFrame.Angles(0, math.pi, 0).
ImportedPet.Facing = CFrame.identity

local NEON_COLORS = {
	NeonMagenta = Color3.fromRGB(227, 92, 255),
	NeonPink = Color3.fromRGB(255, 139, 240),
	NeonViolet = Color3.fromRGB(166, 77, 255),
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

	-- The pet's origin is the centre of the summoning circle, on the ground.
	local circle = model:FindFirstChild("Circle_NeonPink", true)
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
