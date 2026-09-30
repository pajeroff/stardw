class_name Iso
extends RefCounted
## Isometric grid <-> screen-space math, shared by world, player and effects.
## Tile footprint is 64x32 (2:1 diamond).

const TILE_W := 64.0
const TILE_H := 32.0

static func cell_to_local(c: Vector2i) -> Vector2:
	return Vector2((c.x - c.y) * TILE_W * 0.5, (c.x + c.y) * TILE_H * 0.5)

static func local_to_cell(p: Vector2) -> Vector2i:
	var fx := (p.x / (TILE_W * 0.5) + p.y / (TILE_H * 0.5)) * 0.5
	var fy := (p.y / (TILE_H * 0.5) - p.x / (TILE_W * 0.5)) * 0.5
	return Vector2i(roundi(fx), roundi(fy))

static func depth(c: Vector2i) -> int:
	return c.x + c.y
