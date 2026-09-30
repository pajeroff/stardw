extends Node
## Game: persistent run state (day, weather, gold, energy, inventory, dex, save).

signal gold_changed(v: int)
signal energy_changed(v: int)
signal clock_changed(hour: int, minute: int)
signal day_changed(day: int, season: int, year: int)
signal inventory_changed()
signal toast(text: String, col: Color)
signal dex_changed(id: String)

const SAVE_PATH := "user://stardw_save.json"
const INV_SIZE := 36
const DAY_START := 6 * 60      # 6:00
const DAY_END := 26 * 60       # 2:00 next day

var gold: int = 250
var energy: int = 100
var max_energy: int = 100
var day: int = 1
var season: int = 0
var year: int = 1
var clock: int = DAY_START
var weather: String = "sun"    # sun, rain, storm, snow
var inventory: Array = []      # [{id,count}]
var dex: Dictionary = {}       # id -> {count, best}
var caught_total: int = 0
var has_save: bool = false

# equipment
var rod_id := "rod_trainee"
var bait_id := ""
var tackle_id := ""
var lure_id := ""

# daily quest
var quest: Dictionary = {}          # {id, need, reward}
var catches_today: Dictionary = {}  # fish id -> count today

func rod_power() -> int:
	return DB.item_by_id(rod_id).get("power", 2)

func luck() -> int:
	var l := DB.item_by_id(rod_id).get("luck", 0)
	if lure_id != "":
		l += 1
	return l

var _rng := RandomNumberGenerator.new()

func _ready() -> void:
	_rng.randomize()
	inventory = []
	has_save = FileAccess.file_exists(SAVE_PATH)

# ---------------------------------------------------------------- time ------
func clock_string() -> String:
	var h := (clock / 60) % 24
	var m := clock % 60
	return "%02d:%02d" % [h, m]

func is_night() -> bool:
	var h := (clock / 60) % 24
	return h >= 20 or h < 5

func day_progress() -> float:
	return clampf(float(clock - DAY_START) / float(DAY_END - DAY_START), 0.0, 1.0)

func advance_time(minutes: int) -> void:
	clock += minutes
	if clock >= DAY_END:
		sleep(true)
		return
	clock_changed.emit(clock / 60, clock % 60)

# ------------------------------------------------------------- inventory ----
func add_item(id: String, count: int = 1) -> bool:
	# stack first
	for slot in inventory:
		if slot["id"] == id:
			slot["count"] += count
			inventory_changed.emit()
			return true
	if inventory.size() < INV_SIZE:
		inventory.append({"id": id, "count": count})
		inventory_changed.emit()
		return true
	emit_toast("Инвентарь полон!", Color(1, 0.5, 0.4))
	return false

func count_item(id: String) -> int:
	for slot in inventory:
		if slot["id"] == id:
			return slot["count"]
	return 0

func remove_item(id: String, count: int = 1) -> bool:
	for i in range(inventory.size()):
		if inventory[i]["id"] == id:
			if inventory[i]["count"] >= count:
				inventory[i]["count"] -= count
				if inventory[i]["count"] <= 0:
					inventory.remove_at(i)
				inventory_changed.emit()
				return true
	return false

# ----------------------------------------------------------------- stats ----
func add_gold(v: int) -> void:
	gold = maxi(0, gold + v)
	gold_changed.emit(gold)

func spend_energy(v: int) -> bool:
	if energy < v:
		emit_toast("Слишком устал... Поешь или поспи.", Color(1, 0.6, 0.3))
		return false
	energy = maxi(0, energy - v)
	energy_changed.emit(energy)
	return true

func restore_energy(v: int) -> void:
	energy = mini(max_energy, energy + v)
	energy_changed.emit(energy)

# ------------------------------------------------------------------ dex -----
func record_catch(id: String, size_cm: int) -> void:
	caught_total += 1
	catches_today[id] = catches_today.get(id, 0) + 1
	if not dex.has(id):
		dex[id] = {"count": 0, "best": 0}
	dex[id]["count"] += 1
	dex[id]["best"] = maxi(dex[id]["best"], size_cm)
	dex_changed.emit(id)

func dex_progress() -> float:
	return float(dex.size()) / float(maxi(1, DB.fish.size()))

# ---------------------------------------------------------------- weather ---
func roll_weather() -> void:
	if season == 3:
		weather = "snow" if _rng.randf() < 0.6 else "sun"
		return
	var r := _rng.randf()
	if r < 0.62:
		weather = "sun"
	elif r < 0.85:
		weather = "rain"
	else:
		weather = "storm"

# ------------------------------------------------------------------ day -----
func sleep(forced: bool = false) -> void:
	if forced:
		emit_toast("Вы уснули от усталости...", Color(0.7, 0.7, 1.0))
	day += 1
	if day > 28:
		day = 1
		season = (season + 1) % 4
		if season == 0:
			year += 1
	clock = DAY_START
	energy = max_energy
	energy_changed.emit(energy)
	quest = {}
	catches_today = {}
	roll_weather()
	day_changed.emit(day, season, year)
	save()

func roll_quest() -> void:
	var pool: Array = []
	for id in DB.fish:
		var f = DB.fish[id]
		if f["rarity"] == "legendary":
			continue
		if f["seasons"].has(season):
			pool.append(id)
	if pool.is_empty():
		pool = DB.fish.keys()
	var id = pool[randi_range(0, pool.size() - 1)]
	var need := randi_range(2, 5)
	quest = {"id": id, "need": need, "reward": DB.fish[id]["price"] * need + 50}

# ------------------------------------------------------------- save/load ----
func new_game() -> void:
	gold = 250
	energy = 100
	max_energy = 100
	day = 1
	season = 0
	year = 1
	clock = DAY_START
	inventory = [{"id": "rod_trainee", "count": 1}]
	dex = {}
	caught_total = 0
	roll_weather()
	save()

func save() -> void:
	var data := {
		"gold": gold, "energy": energy, "max_energy": max_energy,
		"day": day, "season": season, "year": year, "clock": clock,
		"weather": weather, "inventory": inventory, "dex": dex,
		"caught_total": caught_total,
		"rod_id": rod_id, "bait_id": bait_id, "tackle_id": tackle_id, "lure_id": lure_id,
	}
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	f.store_string(JSON.stringify(data))
	f = null
	has_save = true

func load_game() -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		return false
	var data = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if data == null:
		return false
	gold = data.get("gold", 250)
	energy = data.get("energy", 100)
	max_energy = data.get("max_energy", 100)
	day = data.get("day", 1)
	season = data.get("season", 0)
	year = data.get("year", 1)
	clock = data.get("clock", DAY_START)
	weather = data.get("weather", "sun")
	inventory = data.get("inventory", [])
	dex = data.get("dex", {})
	caught_total = data.get("caught_total", 0)
	rod_id = data.get("rod_id", "rod_trainee")
	bait_id = data.get("bait_id", "")
	tackle_id = data.get("tackle_id", "")
	lure_id = data.get("lure_id", "")
	return true

# ------------------------------------------------------------- helpers ------
func emit_toast(text: String, col: Color = Color.WHITE) -> void:
	toast.emit(text, col)

func randf() -> float:
	return _rng.randf()

func randi_range(a: int, b: int) -> int:
	return _rng.randi_range(a, b)
