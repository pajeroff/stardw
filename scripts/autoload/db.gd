extends Node
## DB: static content tables. Fish art ids MUST match keys in the "fish" atlas
## of assets/manifest.json (enforced by tools/validate_project.py).

const SEASONS := ["Весна", "Лето", "Осень", "Зима"]
# water: lake, river, ocean, pond
# tod: day, night, any ; weather: any, rain, sun, storm
# rarity: common, uncommon, rare, legendary

var fish := {
	"carp":         {"name": "Карп",            "water": ["lake", "pond"], "seasons": [0, 1, 2], "tod": "any",   "weather": "any",   "rarity": "common",   "diff": 2, "size": [30, 75], "price": 40},
	"perch":        {"name": "Окунь",           "water": ["lake", "river"], "seasons": [0, 1, 2, 3], "tod": "day", "weather": "any", "rarity": "common",   "diff": 1, "size": [15, 40], "price": 25},
	"roach":        {"name": "Плотва",          "water": ["river", "lake"], "seasons": [0, 1, 2, 3], "tod": "any", "weather": "any", "rarity": "common",  "diff": 1, "size": [10, 30], "price": 15},
	"bream":        {"name": "Лещ",             "water": ["lake", "river"], "seasons": [1, 2], "tod": "night", "weather": "any", "rarity": "uncommon", "diff": 2, "size": [25, 60], "price": 45},
	"minnow":       {"name": "Пескарь",         "water": ["river"], "seasons": [0, 1, 2, 3], "tod": "day", "weather": "any", "rarity": "common", "diff": 1, "size": [5, 12], "price": 8},
	"loach":        {"name": "Вьюн",            "water": ["pond", "river"], "seasons": [0, 1, 2], "tod": "any", "weather": "rain", "rarity": "uncommon", "diff": 1, "size": [10, 25], "price": 20},
	"bluegill":     {"name": "Солнечник",       "water": ["pond", "lake"], "seasons": [0, 1], "tod": "day", "weather": "sun", "rarity": "common", "diff": 1, "size": [12, 30], "price": 30},
	"sunfish":      {"name": "Речной солнечник","water": ["river"], "seasons": [0, 1, 2], "tod": "day", "weather": "sun", "rarity": "uncommon", "diff": 2, "size": [15, 35], "price": 45},
	"bass":         {"name": "Большеротый окунь","water": ["lake"], "seasons": [0, 1, 2], "tod": "any", "weather": "any", "rarity": "uncommon", "diff": 3, "size": [25, 60], "price": 60},
	"trout":        {"name": "Форель",          "water": ["river"], "seasons": [0, 2], "tod": "day", "weather": "rain", "rarity": "uncommon", "diff": 3, "size": [20, 55], "price": 70},
	"salmon":       {"name": "Лосось",          "water": ["river", "ocean"], "seasons": [2], "tod": "day", "weather": "any", "rarity": "rare", "diff": 4, "size": [40, 90], "price": 120},
	"pike":         {"name": "Щука",            "water": ["lake", "river"], "seasons": [0, 1, 2, 3], "tod": "day", "weather": "any", "rarity": "uncommon", "diff": 3, "size": [40, 110], "price": 80},
	"zander":       {"name": "Судак",           "water": ["river", "lake"], "seasons": [1, 2], "tod": "night", "weather": "any", "rarity": "rare", "diff": 4, "size": [35, 90], "price": 110},
	"catfish":      {"name": "Сом",             "water": ["river", "lake"], "seasons": [1, 2], "tod": "night", "weather": "rain", "rarity": "rare", "diff": 4, "size": [50, 150], "price": 140},
	"gar":          {"name": "Панцирник",       "water": ["lake"], "seasons": [1, 2], "tod": "day", "weather": "sun", "rarity": "rare", "diff": 4, "size": [40, 120], "price": 130},
	"eel":          {"name": "Угорь",           "water": ["river", "ocean"], "seasons": [2, 3], "tod": "night", "weather": "rain", "rarity": "rare", "diff": 4, "size": [40, 100], "price": 120},
	"goldfish":     {"name": "Золотая рыбка",   "water": ["pond"], "seasons": [0, 1, 2], "tod": "any", "weather": "sun", "rarity": "rare", "diff": 3, "size": [8, 20], "price": 150},
	"koi":          {"name": "Карп кои",        "water": ["pond"], "seasons": [0, 1, 2], "tod": "day", "weather": "any", "rarity": "rare", "diff": 3, "size": [25, 70], "price": 160},
	"piranha":      {"name": "Пиранья",         "water": ["river"], "seasons": [1], "tod": "day", "weather": "sun", "rarity": "rare", "diff": 4, "size": [15, 35], "price": 140},
	"herring":      {"name": "Сельдь",          "water": ["ocean"], "seasons": [0, 1, 2, 3], "tod": "any", "weather": "any", "rarity": "common", "diff": 2, "size": [15, 35], "price": 30},
	"sardine":      {"name": "Сардина",         "water": ["ocean"], "seasons": [0, 2], "tod": "day", "weather": "any", "rarity": "common", "diff": 1, "size": [10, 25], "price": 20},
	"flounder":     {"name": "Камбала",         "water": ["ocean"], "seasons": [1, 2, 3], "tod": "day", "weather": "any", "rarity": "uncommon", "diff": 2, "size": [20, 50], "price": 55},
	"tuna":         {"name": "Тунец",           "water": ["ocean"], "seasons": [1, 2], "tod": "day", "weather": "any", "rarity": "rare", "diff": 5, "size": [60, 180], "price": 200},
	"swordfish":    {"name": "Рыба-меч",        "water": ["ocean"], "seasons": [1], "tod": "day", "weather": "sun", "rarity": "rare", "diff": 5, "size": [100, 250], "price": 260},
	"pufferfish":   {"name": "Рыба-ёж",         "water": ["ocean"], "seasons": [1, 2], "tod": "day", "weather": "any", "rarity": "uncommon", "diff": 2, "size": [10, 30], "price": 60},
	"ray":          {"name": "Скат",            "water": ["ocean"], "seasons": [2, 3], "tod": "any", "weather": "any", "rarity": "rare", "diff": 4, "size": [50, 150], "price": 170},
	"seahorse":     {"name": "Морской конёк",   "water": ["ocean"], "seasons": [0, 1], "tod": "day", "weather": "sun", "rarity": "rare", "diff": 2, "size": [5, 15], "price": 110},
	"jellyfish":    {"name": "Медуза",          "water": ["ocean"], "seasons": [1], "tod": "any", "weather": "any", "rarity": "uncommon", "diff": 1, "size": [10, 40], "price": 35},
	"anglerfish":   {"name": "Удильщик",        "water": ["ocean"], "seasons": [2, 3], "tod": "night", "weather": "any", "rarity": "rare", "diff": 4, "size": [20, 60], "price": 180},
	"ghostfish":    {"name": "Призрачная рыба", "water": ["lake"], "seasons": [2, 3], "tod": "night", "weather": "any", "rarity": "rare", "diff": 4, "size": [20, 60], "price": 190},
	"icefish":      {"name": "Ледяная рыба",    "water": ["lake", "river"], "seasons": [3], "tod": "any", "weather": "any", "rarity": "rare", "diff": 3, "size": [15, 40], "price": 150},
	"sturgeon":     {"name": "Осётр",           "water": ["river", "ocean"], "seasons": [1, 2], "tod": "day", "weather": "any", "rarity": "rare", "diff": 5, "size": [60, 200], "price": 220},
	"moon_carp":    {"name": "Лунный карп",     "water": ["lake"], "seasons": [0, 1, 2, 3], "tod": "night", "weather": "any", "rarity": "legendary", "diff": 5, "size": [60, 140], "price": 1500},
	"crimson_pike": {"name": "Багровая щука",   "water": ["river"], "seasons": [2], "tod": "day", "weather": "storm", "rarity": "legendary", "diff": 5, "size": [80, 170], "price": 1800},
	"ice_leviathan":{"name": "Ледяной левиафан","water": ["lake"], "seasons": [3], "tod": "any", "weather": "any", "rarity": "legendary", "diff": 5, "size": [120, 260], "price": 2000},
	"deep_ghost":   {"name": "Призрак глубин",  "water": ["ocean"], "seasons": [3], "tod": "night", "weather": "storm", "rarity": "legendary", "diff": 5, "size": [70, 160], "price": 1900},
	"golden_dragon":{"name": "Золотой дракон",  "water": ["river"], "seasons": [1], "tod": "day", "weather": "sun", "rarity": "legendary", "diff": 5, "size": [90, 200], "price": 2200},
	"ancient_koi":  {"name": "Древний кои",     "water": ["pond"], "seasons": [0, 1, 2, 3], "tod": "any", "weather": "rain", "rarity": "legendary", "diff": 5, "size": [50, 120], "price": 1700},
}

var items := {
	# rods: power = cast distance, luck = rarity bonus
	"rod_trainee":  {"name": "Удочка новичка",  "type": "rod",  "price": 0,    "power": 2, "luck": 0, "desc": "Простая палка с леской."},
	"rod_bamboo":   {"name": "Бамбуковая удочка","type": "rod", "price": 100,  "power": 3, "luck": 1, "desc": "Надёжная классика."},
	"rod_fiberglass":{"name": "Стекловолоконная удочка","type":"rod","price": 400,"power": 4, "luck": 2, "desc": "Дальше заброс, клюёт чаще."},
	"rod_iridium":  {"name": "Иридиевая удочка","type": "rod",  "price": 2000, "power": 5, "luck": 3, "desc": "Вершина рыбацкого искусства."},
	# baits: bite_speed multiplier (lower wait), some unlock fish
	"bait_worm":    {"name": "Червяк",        "type": "bait", "price": 5,  "bite": 0.85, "desc": "Классическая наживка."},
	"bait_maggot":  {"name": "Опарыш",        "type": "bait", "price": 8,  "bite": 0.75, "desc": "Клюёт заметно быстрее."},
	"bait_shrimp":  {"name": "Креветка",      "type": "bait", "price": 15, "bite": 0.7,  "desc": "Любима океанской рыбой."},
	"bait_glow":    {"name": "Светлячок",     "type": "bait", "price": 40, "bite": 0.8,  "night": true, "desc": "Светится — рыба ночью идёт к нему."},
	# tackles: modify the minigame
	"tackle_cork":  {"name": "Пробковый поплавок","type": "tackle","price": 60, "bar": 1.25, "desc": "Планка ловли выше."},
	"tackle_barbed":{"name": "Крючок с бородкой","type":"tackle","price": 80, "grip": 1.3, "desc": "Рыба медленнее срывается."},
	"tackle_magnet":{"name": "Магнит сокровищ","type":"tackle","price": 120,"treasure": 2.0,"desc": "Больше шанс найти сокровища."},
	"lure_spinner": {"name": "Блесна",        "type": "lure", "price": 50, "rare": 1.15, "desc": "Чуть выше шанс редкой рыбы."},
	"lure_fly":     {"name": "Мушка",         "type": "lure", "price": 45, "river": true, "desc": "Для речной форели."},
	"lure_trap":    {"name": "Воблер",        "type": "lure", "price": 90, "rare": 1.25, "desc": "Приманка на хищника."},
	# dishes: energy restore
	"dish_sushi":   {"name": "Суши",          "type": "food", "price": 60, "energy": 45, "desc": "Свежая рыба + рис."},
	"dish_grill":   {"name": "Жареная рыба",  "type": "food", "price": 40, "energy": 35, "desc": "С костра, с дымком."},
	"dish_soup":    {"name": "Уха",           "type": "food", "price": 50, "energy": 40, "desc": "Наваристая уха."},
	"dish_stew":    {"name": "Рыбное рагу",   "type": "food", "price": 70, "energy": 60, "desc": "Сытное рагу."},
	"coffee":       {"name": "Кофе",          "type": "food", "price": 25, "energy": 15, "desc": "Бодрит."},
	# junk
	"junk_boot":    {"name": "Старый ботинок","type": "junk", "price": 1, "desc": "Кто-то его потерял."},
	"junk_can":     {"name": "Консервная банка","type":"junk","price": 1, "desc": "Мусор."},
	"junk_seaweed": {"name": "Водоросли",     "type": "junk", "price": 2, "desc": "Скользкие."},
	"junk_driftwood":{"name": "Коряга",       "type": "junk", "price": 2, "desc": "Пригодится на дрова."},
	"junk_oldrod":  {"name": "Сломанная удочка","type":"junk","price": 1, "desc": "Увы."},
	"junk_glasses": {"name": "Очки",          "type": "junk", "price": 3, "desc": "Без стекол."},
	# treasure
	"treasure_pearl":  {"name": "Жемчужина",   "type": "treasure", "price": 400, "desc": "Сияет."},
	"treasure_ring":   {"name": "Кольцо",      "type": "treasure", "price": 300, "desc": "Чьё-то обручальное?"},
	"treasure_emerald":{"name": "Изумруд",     "type": "treasure", "price": 250, "desc": "Зелёный."},
	"treasure_sapphire":{"name": "Сапфир",     "type": "treasure", "price": 300, "desc": "Синий."},
	"treasure_ruby":   {"name": "Рубин",       "type": "treasure", "price": 320, "desc": "Красный."},
	"treasure_crown":  {"name": "Корона",      "type": "treasure", "price": 900, "desc": "Королевская!"},
	"treasure_idol":   {"name": "Древний идол","type": "treasure", "price": 500, "desc": "Из глубин."},
	# resources
	"wood":   {"name": "Дерево", "type": "resource", "price": 4, "desc": ""},
	"stone":  {"name": "Камень", "type": "resource", "price": 5, "desc": ""},
	"fiber":  {"name": "Волокно","type": "resource", "price": 2, "desc": ""},
}

func fish_by_id(id: String) -> Dictionary:
	return fish.get(id, {})

func item_by_id(id: String) -> Dictionary:
	return items.get(id, {})

func rarity_color(r: String) -> Color:
	match r:
		"common": return Color(0.8, 0.8, 0.8)
		"uncommon": return Color(0.5, 0.9, 0.5)
		"rare": return Color(0.5, 0.7, 1.0)
		"legendary": return Color(1.0, 0.8, 0.3)
	return Color.WHITE

func rarity_weight(r: String, luck: int) -> float:
	match r:
		"common": return 100.0
		"uncommon": return 34.0 + luck * 2
		"rare": return 12.0 + luck * 2
		"legendary": return 1.6 + luck * 0.5
	return 0.0
