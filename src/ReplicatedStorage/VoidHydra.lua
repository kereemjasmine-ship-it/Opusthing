-- VoidHydra (ModuleScript, ReplicatedStorage)
-- A blocky, studded five-headed hydra pet with neon collars and a spinning
-- summoning circle. Every piece is a plain Part (Plastic + Studs surfaces for
-- the body, Neon for the glow), so no meshes or uploads are needed.
--
-- Usage:
--   local VoidHydra = require(ReplicatedStorage.VoidHydra)
--   local pet = VoidHydra.new({ Scale = 0.35 })
--   pet.Model.Parent = workspace
--   RunService.RenderStepped:Connect(function(dt) pet:Update(someCFrame, dt) end)
--
-- All sizes below are in "design units"; Config.Scale converts them to studs.

local VoidHydra = {}
VoidHydra.__index = VoidHydra

VoidHydra.Palette = {
	Void = Color3.fromRGB(11, 7, 16), -- claws, deepest shadow
	Hide = Color3.fromRGB(28, 19, 38), -- main body blocks
	HideLight = Color3.fromRGB(42, 27, 61), -- alternating body blocks
	Plate = Color3.fromRGB(61, 38, 89), -- armour plates, horns, spikes
	Belly = Color3.fromRGB(90, 58, 133), -- belly scales, jaw
	Neon = Color3.fromRGB(227, 92, 255), -- eyes, mouth, spike tips
	NeonSoft = Color3.fromRGB(255, 139, 240), -- collars and summoning rings
	Violet = Color3.fromRGB(166, 77, 255), -- shards, inner ring
	Bone = Color3.fromRGB(232, 220, 245), -- fangs, horn tips
}

export type Config = {
	Scale: number?,
	Hover: number?,
	NeckCount: number?,
	NeckSegments: number?,
	CollarSegments: number?,
	RingSegments: number?,
	ShardCount: number?,
	Particles: boolean?,
	Light: boolean?,
}

local DEFAULT_CONFIG = {
	Scale = 0.35, -- 1 design unit = 0.35 studs (pet is ~4 studs tall)
	Hover = 0.8, -- how high the body floats above the circle (design units)
	NeckCount = 5,
	NeckSegments = 4,
	CollarSegments = 8,
	RingSegments = 28,
	ShardCount = 8,
	Particles = true,
	Light = true,
}

local PLASTIC = Enum.Material.Plastic
local NEON = Enum.Material.Neon
local V = Vector3.new

local function at(x: number, y: number, z: number, rx: number?, ry: number?, rz: number?): CFrame
	return CFrame.new(x, y, z) * CFrame.Angles(math.rad(rx or 0), math.rad(ry or 0), math.rad(rz or 0))
end

-- Block frame from a to b whose X axis is `right` (keeps neck blocks square to the neck's plane).
local function segmentFrame(a: Vector3, b: Vector3, right: Vector3): CFrame
	local back = (a - b).Unit
	local up = back:Cross(right).Unit
	return CFrame.fromMatrix((a + b) / 2, right, up, back)
end

function VoidHydra.new(config: Config?)
	local cfg = table.clone(DEFAULT_CONFIG)
	for key, value in pairs(config or {}) do
		(cfg :: any)[key] = value
	end

	local self = setmetatable({}, VoidHydra)
	self.Config = cfg
	self.Scale = cfg.Scale
	self.Model = Instance.new("Model")
	self.Model.Name = "VoidHydra"

	self._entries = {} -- { part, offset, group }
	self._parts = {}
	self._cframes = {}
	self._pivots = {} -- neck groups: { name, pivot, phase }
	self._shards = {} -- shard groups: { name, speed, phase, lift }
	self._pulse = {} -- neon parts that breathe
	self._groups = {}
	self._time = 0

	self:_build()
	return self
end

function VoidHydra:_part(size: Vector3, offset: CFrame, color: Color3, material: Enum.Material?, group: string?): Part
	local s = self.Scale
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Size = size * s
	p.Color = color
	p.Material = material or PLASTIC
	p.CastShadow = p.Material ~= NEON
	if p.Material == PLASTIC then
		-- the classic stud look
		p.TopSurface = Enum.SurfaceType.Studs
		p.BottomSurface = Enum.SurfaceType.Inlet
	else
		p.TopSurface = Enum.SurfaceType.Smooth
		p.BottomSurface = Enum.SurfaceType.Smooth
	end
	p.Parent = self.Model

	table.insert(self._entries, {
		part = p,
		offset = CFrame.new(offset.Position * s) * offset.Rotation,
		group = group or "body",
	})
	table.insert(self._parts, p)
	if p.Material == NEON then
		table.insert(self._pulse, p)
	end
	return p
end

-- A ring of small neon blocks around the local Z axis of `center` (neck collars).
function VoidHydra:_collar(center: CFrame, radius: number, thickness: number, depth: number, group: string)
	local n = self.Config.CollarSegments
	local chord = 2 * math.pi * radius / n * 1.1
	for k = 0, n - 1 do
		local c = center * CFrame.Angles(0, 0, (k / n) * 2 * math.pi) * CFrame.new(0, radius, 0)
		self:_part(V(chord, thickness, depth), c, VoidHydra.Palette.NeonSoft, NEON, group)
	end
end

-- A flat ring of neon blocks around the Y axis at the pet's feet.
function VoidHydra:_groundRing(radius: number, n: number, height: number, width: number, y: number, color: Color3, group: string)
	local chord = 2 * math.pi * radius / n * 0.82 -- small gaps read as "segments"
	for k = 0, n - 1 do
		local c = CFrame.Angles(0, (k / n) * 2 * math.pi, 0) * CFrame.new(0, y, -radius)
		self:_part(V(chord, height, width), c, color, NEON, group)
	end
end

function VoidHydra:_build()
	local P = VoidHydra.Palette
	local cfg = self.Config

	-- invisible root so the model has a PrimaryPart / pivot
	local root = self:_part(V(1, 1, 1), CFrame.identity, P.Void, PLASTIC, "root")
	root.Name = "Root"
	root.Transparency = 1
	self.Model.PrimaryPart = root

	-- BODY ----------------------------------------------------------------
	self:_part(V(4, 3, 5), at(0, 3.6, 0.6), P.Hide) -- torso
	self:_part(V(3.2, 0.6, 4.2), at(0, 2.0, 0.4), P.Belly) -- belly plate
	local chest = self:_part(V(3.6, 2.8, 1.8), at(0, 4.0, -2.4), P.HideLight)
	self:_part(V(2.4, 1.6, 0.4), at(0, 3.4, -3.35), P.Belly) -- chest scales
	self:_part(V(0.5, 0.5, 0.2), at(0, 4.6, -3.4, 0, 0, 45), P.Neon, NEON) -- core rune

	for _, side in { -1, 1 } do
		self:_part(V(1.4, 0.5, 2.2), at(side * 2.1, 5.0, -1.8, 0, 0, side * -20), P.Plate) -- shoulder plate
		self:_part(V(1.2, 0.5, 2.0), at(side * 2.1, 4.6, 2.0, 0, 0, side * -20), P.Plate) -- hip plate
	end

	-- spine spikes with glowing tips
	for i = 0, 4 do
		local z = 3.0 - i * 1.1
		local size = 0.75 - i * 0.04
		self:_part(V(size, size, size), at(0, 5.15, z, 45, 0, 0), P.Plate)
		self:_part(V(0.22, 0.22, 0.22), at(0, 5.62, z, 45, 0, 0), P.Neon, NEON)
	end

	-- LEGS ----------------------------------------------------------------
	for _, side in { -1, 1 } do
		for _, z in { -1.6, 2.2 } do
			local x = side * 2.2
			self:_part(V(1.4, 1.8, 1.6), at(x, 2.6, z), P.HideLight) -- thigh
			self:_part(V(1.0, 1.4, 1.0), at(x, 1.1, z - 0.2), P.Hide) -- shin
			self:_part(V(1.4, 0.5, 1.8), at(x, 0.25, z - 0.5), P.Plate) -- foot
			for c = -1, 1 do
				self:_part(V(0.28, 0.28, 0.6), at(x + c * 0.45, 0.2, z - 1.6, -15, 0, 0), P.Void) -- claw
			end
			self:_part(V(0.2, 0.2, 0.2), at(x + side * 0.72, 2.9, z), P.Neon, NEON) -- thigh rune
		end
	end

	-- TAIL ----------------------------------------------------------------
	local tail = {
		{ V(2.2, 1.8, 1.8), at(0, 3.4, 3.8, 10, 0, 0) },
		{ V(1.6, 1.3, 1.8), at(0, 2.9, 5.4, 20, 0, 0) },
		{ V(1.1, 0.9, 1.6), at(0, 2.2, 6.8, 25, 0, 0) },
		{ V(0.7, 0.6, 1.4), at(0, 1.5, 8.0, 30, 0, 0) },
	}
	for i, seg in tail do
		self:_part(seg[1], seg[2], if i % 2 == 1 then P.Hide else P.HideLight, PLASTIC, "tail")
	end
	self:_part(V(0.5, 0.5, 1.0), at(0, 1.0, 9.0, 35, 0, 0), P.Neon, NEON, "tail")

	-- NECKS + HEADS -------------------------------------------------------
	local count = cfg.NeckCount
	for i = 1, count do
		local u = if count == 1 then 0 else ((i - 1) / (count - 1)) * 2 - 1 -- -1 .. 1
		local group = "neck" .. i
		local base = V(u * 1.3, 4.8, -2.6)
		local height = 5.2 - math.abs(u) * 1.4 -- middle head is tallest
		local reach = 2.4 + math.abs(u) * 1.6 -- outer heads reach further
		local turn = CFrame.Angles(0, math.rad(-u * 55), 0) -- splay outwards
		table.insert(self._pivots, { name = group, pivot = CFrame.new(base * self.Scale), phase = i * 1.37 })

		-- quadratic bezier in the neck's own plane (x = forward, y = up)
		local p0, p1, p2 = Vector2.zero, Vector2.new(-0.6, height * 0.9), Vector2.new(reach, height)
		local function point(t: number): Vector3
			local q = p0:Lerp(p1, t):Lerp(p1:Lerp(p2, t), t)
			return base + turn:VectorToWorldSpace(V(0, q.Y, -q.X))
		end

		local segments = cfg.NeckSegments
		for s = 1, segments do
			local a, b = point((s - 1) / segments), point(s / segments)
			local width = 1.15 - s * 0.08
			local frame = segmentFrame(a, b, turn.RightVector)
			local len = (b - a).Magnitude
			self:_part(V(width, width, len + 0.35), frame, if s % 2 == 1 then P.Hide else P.HideLight, PLASTIC, group)
			self:_part(V(width * 0.7, 0.2, len * 0.8), frame * CFrame.new(0, -width / 2, 0), P.Belly, PLASTIC, group)
			if s == 2 then
				-- the double glowing collar from the reference
				self:_collar(frame * CFrame.new(0, 0, 0.25), width * 0.5 + 0.35, 0.18, 0.22, group)
				self:_collar(frame * CFrame.new(0, 0, -0.25), width * 0.5 + 0.5, 0.14, 0.18, group)
			elseif s == segments then
				self:_collar(frame, width * 0.5 + 0.3, 0.14, 0.18, group)
			end
		end

		-- head, tilted slightly down and facing along the neck's turn
		local head = CFrame.new(point(1)) * turn * CFrame.Angles(math.rad(-12), 0, 0)
		local function hp(size: Vector3, offset: CFrame, color: Color3, material: Enum.Material?)
			self:_part(size, head * offset, color, material or PLASTIC, group)
		end
		hp(V(1.7, 1.3, 1.7), at(0, 0, 0), P.HideLight) -- skull
		hp(V(1.2, 0.75, 1.5), at(0, -0.15, -1.45), P.Hide) -- snout
		hp(V(1.25, 0.25, 1.1), at(0, 0.33, -1.25), P.Plate) -- snout ridge
		hp(V(1.05, 0.35, 1.5), at(0, -0.75, -1.15, -14, 0, 0), P.Belly) -- open jaw
		hp(V(0.9, 0.12, 1.1), at(0, -0.58, -1.2, -7, 0, 0), P.Neon, NEON) -- mouth glow
		for _, sd in { -1, 1 } do
			hp(V(0.12, 0.25, 0.12), at(sd * 0.45, -0.6, -2.0), P.Bone) -- fang
			hp(V(0.3, 0.22, 0.45), at(sd * 0.62, 0.22, -0.55), P.Neon, NEON) -- eye
			hp(V(0.5, 0.25, 0.7), at(sd * 0.55, 0.58, -0.45, 0, 0, sd * -15), P.Plate) -- brow
			hp(V(0.3, 0.3, 1.4), at(sd * 0.5, 0.75, 0.75, -35, sd * -15, 0), P.Plate) -- horn
			hp(V(0.18, 0.18, 0.4), at(sd * 0.55, 1.21, 1.41, -35, sd * -15, 0), P.Bone) -- horn tip
			hp(V(0.15, 0.4, 0.8), at(sd * 0.9, -0.1, 0.4, 0, sd * 20, 0), P.Plate) -- cheek frill
		end
	end

	-- SUMMONING CIRCLE ----------------------------------------------------
	local n = cfg.RingSegments
	self:_groundRing(6.2, n, 0.12, 0.4, 0.08, P.NeonSoft, "ringA")
	self:_groundRing(7.1, n, 0.08, 0.18, 0.05, P.Neon, "ringA")
	self:_groundRing(5.2, math.max(8, math.floor(n * 0.75)), 0.1, 0.22, 0.2, P.Violet, "ringB")

	-- FLOATING SHARDS -----------------------------------------------------
	for k = 1, cfg.ShardCount do
		local name = "shard" .. k
		local radius = 4.5 + (k % 3) * 1.1
		local lift = 1.5 + (k % 4) * 1.2
		table.insert(self._shards, {
			name = name,
			speed = 0.5 + (k % 3) * 0.25,
			phase = k * (2 * math.pi / cfg.ShardCount),
			lift = lift,
		})
		self:_part(V(0.3, 0.3, 0.3), at(0, lift, -radius, 45, 45, 0), P.Violet, NEON, name)
	end

	-- EFFECTS -------------------------------------------------------------
	if cfg.Light then
		local light = Instance.new("PointLight")
		light.Color = P.Neon
		light.Range = 14 * self.Scale * 2
		light.Brightness = 1.6
		light.Parent = chest
	end
	if cfg.Particles then
		local emitterPart = self:_part(V(10, 0.2, 10), at(0, 0.3, 0), P.Void, PLASTIC, "root")
		emitterPart.Name = "Aura"
		emitterPart.Transparency = 1
		local emitter = Instance.new("ParticleEmitter")
		emitter.Texture = "rbxasset://textures/particles/sparkles_main.dds"
		emitter.Color = ColorSequence.new(P.NeonSoft, P.Violet)
		emitter.LightEmission = 1
		emitter.Rate = 10
		emitter.Lifetime = NumberRange.new(1, 1.8)
		emitter.Speed = NumberRange.new(1, 2.5)
		emitter.Size = NumberSequence.new(0.35 * self.Scale * 2, 0)
		emitter.Transparency = NumberSequence.new(0.1, 1)
		emitter.EmissionDirection = Enum.NormalId.Top
		emitter.Parent = emitterPart
	end

	for i = 1, #self._parts do
		self._cframes[i] = CFrame.identity
	end
end

-- Call every frame with where the pet should stand (its feet / circle centre).
function VoidHydra:Update(rootCFrame: CFrame, dt: number)
	self._time += dt
	local t = self._time
	local s = self.Scale
	local g = self._groups

	local body = CFrame.new(0, (self.Config.Hover + math.sin(t * 2.2) * 0.12) * s, 0)
	g.root = CFrame.identity
	g.body = body

	local tailPivot = CFrame.new(0, 3.4 * s, 3 * s)
	g.tail = body * tailPivot * CFrame.Angles(0, math.sin(t * 1.7) * 0.18, 0) * tailPivot:Inverse()

	for _, neck in self._pivots do
		local sway = CFrame.Angles(math.sin(t * 1.5 + neck.phase) * 0.1, math.sin(t * 0.9 + neck.phase * 1.3) * 0.12, 0)
		g[neck.name] = body * neck.pivot * sway * neck.pivot:Inverse()
	end

	g.ringA = CFrame.Angles(0, t * 0.6, 0)
	g.ringB = CFrame.Angles(0, -t * 1.1, 0)
	for _, shard in self._shards do
		g[shard.name] = CFrame.new(0, math.sin(t * 2 + shard.phase) * 0.4 * s, 0)
			* CFrame.Angles(0, t * shard.speed + shard.phase, 0)
	end

	local cframes = self._cframes
	for i, entry in self._entries do
		cframes[i] = rootCFrame * g[entry.group] * entry.offset
	end
	workspace:BulkMoveTo(self._parts, cframes, Enum.BulkMoveMode.FireCFrameChanged)

	local glow = 0.15 + 0.15 * math.sin(t * 3)
	for _, p in self._pulse do
		p.Transparency = glow
	end
end

function VoidHydra:Destroy()
	self.Model:Destroy()
	table.clear(self._entries)
	table.clear(self._parts)
end

return VoidHydra
