"""
ねこあつめ Pyxel 版 ― ゲームルール

catalog.py のデータを読み込み、状態(state)を操作する関数を提供します。
UI からはこのモジュールの関数だけを呼び出すこと。

【フェーズ1変更】
- _food() に tags 引数を追加（エサの好みタグ）
- _cat() で個性辞書を正規化（sex/traits/taste/affinity/habitat の既定値補完）
- 猫の状態 fullness/trust/happiness を追加
- advance() で taste_score を使って来訪率を補正
- エサの減り方を「時間で1ずつ」から「庭にいる猫が食べた分」に変更
- CATALOG_VERSION = 3、loads() でバージョン3へのマイグレーション

【フェーズ2変更点】
- 隠れレベル(level)・フラグ(flags)・出会った人々(met_actors)を追加
- gain_level() で静かな進行を管理（数字は見せない）
- meets() で出現条件判定（将来の ACTORS 用に準備）
- 猫の初来訪時にレベルが上昇
- CATALOG_VERSION = 4、loads() でバージョン4へのマイグレーション

【フェーズ3変更点】
- GOODS, ACTORS, PLACES を catalog から読み込み
- state に inventory, actor_states, current_place, places を追加
- switch_place() で場所を切り替え
- give() で GOODS を渡し、報酬を受け取る
- apply_reward() で報酬を適用（item/creature/stage unlocks/flags）
- event_text() を actor 対応に拡張
- フェーズ2互換: state['yard'] / state['food'] は current_place の場所と同期
- CATALOG_VERSION = 5

SPACE = 6  # 庭のマス数（フェーズ2互換、場所ごとの space を優先）、loads() でバージョン5へのマイグレーション
"""

import collections
import json
import random

import catalog

# ---------------------------------------------------------------------------
# カタログデータ(起動時に load_catalog() で読み込まれる)
# ---------------------------------------------------------------------------

CATALOG_VERSION = 5

SPACE = 6  # 庭のマス数（フェーズ2互換、場所ごとの space を優先）

IDS_BY_KIND = {}   # {"toy": [ID, ...], "food": [ID, ...]}
ITEMS = {}         # {ID: spec}
TOYS = {}          # {ID: toy_spec}
FOODS = {}         # {ID: food_spec}
CATS = {}          # {ID: cat_spec}
GOODS = {}         # {ID: goods_spec}
ACTORS = {}        # {ID: actor_spec}
PLACES = {}        # {ID: place_spec}

Result = collections.namedtuple("Result", ["ok", "msg", "code"])

SHOP_FILTERS = [("all", "すべて"), ("afford", "買える"), ("new", "新")]
SHOP_SORTS = [("default", "並び"), ("price_asc", "安い"), ("price_desc", "高い")]


# ---------------------------------------------------------------------------
# カタログ読み込み
# ---------------------------------------------------------------------------

def _toy(name, cost, cur, size, desc):
    return {"kind": "toy", "name": name, "cost": cost, "cur": cur,
            "size": size, "desc": desc}


def _food(name, cost, cur, minutes, tags, desc):
    return {"kind": "food", "name": name, "cost": cost, "cur": cur,
            "minutes": minutes, "tags": tags, "desc": desc}


def _cat(name, desc, treasure, **opts):
    traits = opts.get("traits", {})
    normalized_traits = {
        "appetite": traits.get("appetite", catalog.DEFAULT_TRAITS["appetite"]),
        "friendly": traits.get("friendly", catalog.DEFAULT_TRAITS["friendly"]),
        "wary": traits.get("wary", catalog.DEFAULT_TRAITS["wary"]),
    }
    return {
        "name": name,
        "desc": desc,
        "treasure": treasure,
        "sex": opts.get("sex", "m"),
        "traits": normalized_traits,
        "taste": opts.get("taste", {}),
        "affinity": opts.get("affinity", {}),
        "habitat": opts.get("habitat", ["garden"]),
        "strength": opts.get("strength", 5),
        "entry_chance": opts.get("entry_chance", 0.1),
        "time_limit": opts.get("time_limit", 30),
        "fav_toy": opts.get("fav_toy", None),
        "exclusive": opts.get("exclusive", False),
    }


def _goods(name, tags, desc):
    return {"kind": "goods", "name": name, "tags": tags, "desc": desc}


def _actor(role, name, desc, **opts):
    return {
        "role": role,
        "name": name,
        "desc": desc,
        "habitat": opts.get("habitat", []),
        "requires": opts.get("requires", {}),
        "wants": opts.get("wants", {}),
        "gifts": opts.get("gifts", []),
        "one_time_reward": opts.get("one_time_reward", None),
    }


def _place(name, space, water_feature, requires):
    return {
        "name": name,
        "space": space,
        "water_feature": water_feature,
        "requires": requires,
    }


def load_catalog():
    IDS_BY_KIND.clear()
    ITEMS.clear()
    TOYS.clear()
    FOODS.clear()
    CATS.clear()
    GOODS.clear()
    ACTORS.clear()
    PLACES.clear()

    for row in catalog.TOYS:
        TOYS[row[0]] = _toy(*row[1:])
        ITEMS[row[0]] = TOYS[row[0]]
        IDS_BY_KIND.setdefault("toy", []).append(row[0])

    for row in catalog.FOODS:
        tags = row[5] if len(row) > 5 else {}
        desc = row[6] if len(row) > 6 else ""
        FOODS[row[0]] = _food(row[1], row[2], row[3], row[4], tags, desc)
        ITEMS[row[0]] = FOODS[row[0]]
        IDS_BY_KIND.setdefault("food", []).append(row[0])

    for row in catalog.CATS:
        cid = row[0]
        opts = row[4] if len(row) > 4 else {}
        CATS[cid] = _cat(row[1], row[2], row[3], **opts)

    for row in catalog.GOODS:
        GOODS[row[0]] = _goods(row[1], row[2], row[3])
        ITEMS[row[0]] = GOODS[row[0]]
        IDS_BY_KIND.setdefault("goods", []).append(row[0])

    for row in catalog.ACTORS:
        aid = row[0]
        opts = row[4] if len(row) > 4 else {}
        ACTORS[aid] = _actor(row[1], row[2], row[3], **opts)

    for row in catalog.PLACES:
        PLACES[row[0]] = _place(row[1], row[2], row[3], row[4])

    catalog.validate_world_or_raise()


# ---------------------------------------------------------------------------
# セーブ/ロード
# ---------------------------------------------------------------------------

def _sanitize(state):
    if isinstance(state, dict):
        return {k: _sanitize(v) for k, v in state.items()}
    if isinstance(state, list):
        return [_sanitize(v) for v in state]
    if isinstance(state, set):
        return ["__set__"] + list(state)
    return state


def _deserialize(obj):
    if isinstance(obj, dict):
        return {k: _deserialize(v) for k, v in obj.items()}
    if isinstance(obj, list) and obj and obj[0] == "__set__":
        return set(obj[1:])
    if isinstance(obj, list):
        return [_deserialize(v) for v in obj]
    return obj


def dumps(state):
    return json.dumps(_sanitize({**state, "version": CATALOG_VERSION}))


def loads(s, now):
    data = json.loads(s)
    data = _deserialize(data)
    ver = data.get("version", 1)

    if ver < 3:
        for cid, c in data.get("cats", {}).items():
            c.setdefault("fullness", 0.5)
            c.setdefault("trust", 0.0)
            c.setdefault("happiness", 0.5)
        data["version"] = 3

    if ver < 4:
        data.setdefault("level", 0)
        data.setdefault("flags", set())
        data.setdefault("met_actors", set())
        data["version"] = 4

    if ver < 5:
        data.setdefault("inventory", {})
        data.setdefault("actor_states", {})
        data.setdefault("current_place", "garden")
        data.setdefault("places", {})
        # フェーズ2の yard/food を garden に移行
        if "yard" in data and "garden" not in data["places"]:
            data["places"]["garden"] = {
                "yard": data.get("yard", []),
                "food": data.get("food"),
                "food_remaining": data.get("food_remaining", 0),
                "water": {},
            }
        for pid in PLACES:
            if pid not in data["places"]:
                data["places"][pid] = {
                    "yard": [],
                    "food": None,
                    "food_remaining": 0,
                    "water": {},
                }
        data["version"] = 5

    cats = data.setdefault("cats", {})
    for cid in CATS:
        if cid not in cats:
            cats[cid] = new_state(0)["cats"][cid]
    for cid in list(cats):
        if cid not in CATS:
            del cats[cid]

    if "last_advance" not in data:
        data["last_advance"] = now

    return data


# ---------------------------------------------------------------------------
# 状態の初期化
# ---------------------------------------------------------------------------

def new_state(now):
    places = {}
    for pid in PLACES:
        places[pid] = {
            "yard": [],
            "food": None,
            "food_remaining": 0,
            "water": {},
        }

    return {
        "s_fish": 15,
        "g_fish": 0,
        "yard": [],
        "food": None,
        "food_remaining": 0,
        "owned_toys": [],
        "food_stock": {},
        "cats": {
            cid: {
                "met": False,
                "given_treasure": False,
                "total_time": 0,
                "time_in_yard": 0,
                "in_yard": False,
                "toy": None,
                "fullness": 0.5,
                "trust": 0.0,
                "happiness": 0.5,
            }
            for cid in CATS
        },
        "pending_money": [],
        "pending_treasures": [],
        "version": CATALOG_VERSION,
        "last_advance": now,
        "level": 0,
        "flags": set(),
        "met_actors": set(),
        "inventory": {},
        "actor_states": {},
        "current_place": "garden",
        "places": places,
    }


# ---------------------------------------------------------------------------
# フェーズ2互換: yard/food 同期
# ---------------------------------------------------------------------------

def _sync_from_current_place(state):
    """current_place の場所データを state['yard'] / state['food'] に反映"""
    pid = state["current_place"]
    if pid in state["places"]:
        p = state["places"][pid]
        state["yard"] = p.get("yard", [])
        state["food"] = p.get("food")
        state["food_remaining"] = p.get("food_remaining", 0)


def _sync_to_current_place(state):
    """state['yard'] / state['food'] を current_place の場所データに反映"""
    pid = state["current_place"]
    if pid in state["places"]:
        p = state["places"][pid]
        p["yard"] = state["yard"]
        p["food"] = state["food"]
        p["food_remaining"] = state["food_remaining"]


# ---------------------------------------------------------------------------
# レベル・条件判定
# ---------------------------------------------------------------------------

def gain_level(state, delta, reason=None):
    old = state["level"]
    state["level"] = old + delta
    return old, state["level"]


def meets(requires, state):
    if not requires:
        return True
    for key, value in requires.items():
        if key == "level":
            if state.get("level", 0) < value:
                return False
        elif key == "flag":
            if value not in state.get("flags", set()):
                return False
        elif key == "items":
            inv = set(state.get("owned_toys", []))
            inv.update(state.get("food_stock", {}).keys())
            inv.update(state.get("inventory", {}).keys())
            if not all(item in inv for item in value):
                return False
        elif key == "cats_met":
            met = sum(1 for c in state.get("cats", {}).values() if c.get("met"))
            if met < value:
                return False
        else:
            pass
    return True


# ---------------------------------------------------------------------------
# 場所
# ---------------------------------------------------------------------------

def available_places(state):
    return [pid for pid in PLACES if meets(PLACES[pid]["requires"], state)]


def switch_place(state, pid):
    if pid not in PLACES:
        return Result(False, "その場所は存在しません", "no_place")
    if pid not in available_places(state):
        return Result(False, "まだ行けません", "locked")
    _sync_to_current_place(state)
    state["current_place"] = pid
    _sync_from_current_place(state)
    return Result(True, PLACES[pid]["name"] + "に移動した", "ok")


# ---------------------------------------------------------------------------
# ゲーム進行
# ---------------------------------------------------------------------------

def advance(state, now):
    _sync_from_current_place(state)

    last = state.get("last_advance", now)
    elapsed = now - last
    ticks = min(int(elapsed // 60), 60)
    state["last_advance"] = now - (elapsed % 60)

    events = []
    visits = 0
    bonus_treasure = None

    pid = state["current_place"]
    place = PLACES.get(pid)
    space = place["space"] if place else 6

    food_id = state.get("food")
    food_tags = FOODS.get(food_id, {}).get("tags", {}) if food_id else {}

    # アクター出現判定
    for aid, actor in ACTORS.items():
        if pid not in actor["habitat"]:
            continue
        if not meets(actor["requires"], state):
            continue
        astate = state["actor_states"].setdefault(aid, {
            "met": False, "in_place": False, "timer": 0, "reward_given": False,
        })
        if not astate["met"]:
            astate["met"] = True
            state["met_actors"].add(aid)
            events.append(("actor_met", aid))
        if not astate["in_place"]:
            astate["in_place"] = True
            astate["timer"] = 0
            events.append(("actor_arrive", aid))

    for _ in range(ticks):
        # ---- アクタータイマー ----
        for aid, astate in state["actor_states"].items():
            if astate.get("in_place"):
                astate["timer"] = astate.get("timer", 0) + 1

        # ---- エサの減り ----
        if food_id and state["food_remaining"] > 0:
            eaters = [cid for cid, c in state["cats"].items() if c["in_yard"]]
            total_eat = 0
            for cid in eaters:
                spec = CATS[cid]
                appetite = spec["traits"]["appetite"]
                if appetite < 0.5:
                    if random.random() >= appetite * 2:
                        continue
                    eat = 1
                elif appetite >= 0.8:
                    eat = 2
                else:
                    eat = 1
                total_eat += eat
                c = state["cats"][cid]
                c["fullness"] = min(1.0, c["fullness"] + 0.08 * eat)
            state["food_remaining"] = max(0, state["food_remaining"] - total_eat)

        # ---- 満腹度減少 ----
        for c in state["cats"].values():
            c["fullness"] = max(0.0, c["fullness"] - 0.015)

        # ---- 猫の滞在時間 ----
        for cid, c in list(state["cats"].items()):
            if not c["in_yard"]:
                continue
            c["time_in_yard"] += 1
            c["total_time"] += 1
            spec = CATS[cid]
            limit = spec["time_limit"]

            if c["time_in_yard"] >= limit:
                c["in_yard"] = False
                c["toy"] = None
                c["time_in_yard"] = 0
                amount = random.randint(1, 3)
                if spec["traits"]["friendly"] > 0.6:
                    amount += 1
                state["pending_money"].append((cid, amount, "s"))
                if random.random() < 0.1:
                    state["pending_treasures"].append(cid)
                    bonus_treasure = cid
                events.append(("leave", cid))

        # ---- 猫の来訪 ----
        if food_id and state["food_remaining"] > 0:
            used = space_used(state)
            free_space = space - used

            for cid, spec in CATS.items():
                c = state["cats"][cid]
                if c["in_yard"]:
                    continue
                if pid not in spec["habitat"]:
                    continue

                base_chance = spec["entry_chance"]
                taste = catalog.taste_score(spec["taste"], food_tags)
                fullness_factor = 1 - c["fullness"] * 0.6
                chance = base_chance * taste * fullness_factor

                if free_space <= 0:
                    continue

                if random.random() < chance:
                    yard = state["yard"]
                    toy = None
                    if yard:
                        fav = spec.get("fav_toy")
                        if fav and fav in yard:
                            toy = fav
                        else:
                            toy = random.choice(yard)
                    c["in_yard"] = True
                    if not c["met"]:
                        gain_level(state, 1, "met_new_cat")
                    c["met"] = True
                    c["time_in_yard"] = 0
                    c["toy"] = toy
                    visits += 1
                    free_space -= 1
                    events.append(("arrive", cid))

    _sync_to_current_place(state)

    return {"ticks": ticks, "events": events, "visits": visits,
            "bonus_treasure": bonus_treasure,
            "first_visits": [cid for cid, c in state["cats"].items()
                             if c["met"] and c["total_time"] == 0 and c["time_in_yard"] == 0]}


def resume(state, now):
    return advance(state, now)


# ---------------------------------------------------------------------------
# ショップ
# ---------------------------------------------------------------------------

def shop_ids(state, kind, filt, sort):
    ids = IDS_BY_KIND.get(kind, []) if kind else (
        IDS_BY_KIND.get("toy", []) + IDS_BY_KIND.get("food", [])
    )
    if filt == "afford":
        ids = [iid for iid in ids
               if state[ITEMS[iid]["cur"] + "_fish"] >= ITEMS[iid]["cost"]]
    elif filt == "new":
        owned = set(state["owned_toys"])
        ids = [
            iid for iid in ids
            if (ITEMS[iid]["kind"] == "toy" and iid not in owned)
            or (ITEMS[iid]["kind"] == "food" and state["food_stock"].get(iid, 0) <= 0)
        ]
    if sort == "price_asc":
        ids = sorted(ids, key=lambda iid: (ITEMS[iid]["cur"] != "s", ITEMS[iid]["cost"]))
    elif sort == "price_desc":
        ids = sorted(ids, key=lambda iid: (ITEMS[iid]["cur"] != "g", ITEMS[iid]["cost"]),
                     reverse=True)
    return ids


def buy(state, item_id):
    it = ITEMS[item_id]
    cur = it["cur"] + "_fish"
    if state[cur] < it["cost"]:
        return Result(False, "{0}が足りません".format("銀のさかな" if it["cur"] == "s" else "金のさかな"),
                      "not_enough")
    state[cur] -= it["cost"]
    if it["kind"] == "toy":
        state["owned_toys"].append(item_id)
    else:
        state["food_stock"][item_id] = state["food_stock"].get(item_id, 0) + 1
    return Result(True, "{0}を買いました".format(it["name"]), "ok")


def price_text(item_id):
    it = ITEMS[item_id]
    if it["cur"] == "s":
        return "銀{0}匹".format(it["cost"])
    else:
        return "金{0}匹".format(it["cost"])


# ---------------------------------------------------------------------------
# 庭の操作
# ---------------------------------------------------------------------------

def space_used(state):
    _sync_from_current_place(state)
    return sum(TOYS[t]["size"] for t in state["yard"])


def place_toy(state, toy_id):
    _sync_from_current_place(state)
    if toy_id in state["yard"]:
        return Result(False, "すでに置いてあります", "already_placed")
    pid = state["current_place"]
    place = PLACES.get(pid)
    space = place["space"] if place else 6
    if space_used(state) + TOYS[toy_id]["size"] > space:
        return Result(False, "スペースが足りません", "no_space")
    state["yard"].append(toy_id)
    _sync_to_current_place(state)
    return Result(True, "{0}を置きました".format(TOYS[toy_id]["name"]), "ok")


def remove_toy(state, toy_id):
    _sync_from_current_place(state)
    if toy_id not in state["yard"]:
        return Result(False, "ありません", "not_placed")
    state["yard"].remove(toy_id)
    for c in state["cats"].values():
        if c["toy"] == toy_id:
            c["toy"] = None
    _sync_to_current_place(state)
    return Result(True, "{0}を片付けました".format(TOYS[toy_id]["name"]), "ok")


def set_food(state, food_id, force=False):
    _sync_from_current_place(state)
    if state["food_stock"].get(food_id, 0) <= 0:
        return Result(False, "持ってません", "not_owned")
    if state["food"] and not force:
        return Result(False, "エサを置きかえますか？", "need_confirm")
    state["food"] = food_id
    state["food_remaining"] = FOODS[food_id]["minutes"]
    state["food_stock"][food_id] -= 1
    if state["food_stock"][food_id] <= 0:
        del state["food_stock"][food_id]
    _sync_to_current_place(state)
    return Result(True, "{0}を置きました".format(FOODS[food_id]["name"]), "ok")


# ---------------------------------------------------------------------------
# 報酬
# ---------------------------------------------------------------------------

def collect(state):
    got = state["pending_money"][:]
    state["pending_money"] = []
    for _cid, amount, cur in got:
        state[cur + "_fish"] += amount
    return got


def collect_treasures(state):
    got = state["pending_treasures"][:]
    state["pending_treasures"] = []
    for cid in got:
        state["cats"][cid]["given_treasure"] = True
    return got


# ---------------------------------------------------------------------------
# 取引
# ---------------------------------------------------------------------------

def give(state, actor_id, goods_id):
    if actor_id not in ACTORS:
        return Result(False, "その人はいません", "no_actor")
    if goods_id not in GOODS:
        return Result(False, "その品物はありません", "no_goods")
    if state["inventory"].get(goods_id, 0) <= 0:
        return Result(False, "持っていません", "not_owned")

    actor = ACTORS[actor_id]
    astate = state["actor_states"].get(actor_id, {})

    if not astate.get("in_place"):
        return Result(False, "今はいません", "not_here")

    # wants チェック
    goods_tags = GOODS[goods_id].get("tags", {})
    wants = actor.get("wants", {})
    if wants:
        match = False
        for tag, threshold in wants.items():
            if goods_tags.get(tag, 0) >= threshold:
                match = True
                break
        if not match:
            return Result(False, "これは不要のようだ", "not_wanted")

    # 渡す
    state["inventory"][goods_id] -= 1
    if state["inventory"][goods_id] <= 0:
        del state["inventory"][goods_id]

    # 報酬
    reward = actor.get("one_time_reward")
    if reward and not astate.get("reward_given"):
        astate["reward_given"] = True
        apply_reward(state, reward)
        return Result(True, "{0}に{1}を渡した".format(actor["name"], GOODS[goods_id]["name"]), "rewarded")

    return Result(True, "{0}に{1}を渡した".format(actor["name"], GOODS[goods_id]["name"]), "ok")


def apply_reward(state, reward):
    if not reward:
        return
    if "item" in reward:
        item_id = reward["item"]
        state["inventory"][item_id] = state["inventory"].get(item_id, 0) + 1
    if "creature" in reward:
        creature = reward["creature"]
        state["flags"].add("creature_" + creature)
    if "unlocks" in reward:
        unlocks = reward["unlocks"]
        state["flags"].add("unlocked_" + unlocks)
    if "flag" in reward:
        state["flags"].add(reward["flag"])


# ---------------------------------------------------------------------------
# クエリ
# ---------------------------------------------------------------------------

def occupants(state, toy_id):
    return [cid for cid, c in state["cats"].items() if c["in_yard"] and c["toy"] == toy_id]


def met_list(state):
    return [cid for cid in CATS if state["cats"][cid]["met"]]


# ---------------------------------------------------------------------------
# イベントテキスト
# ---------------------------------------------------------------------------

def event_text(ev):
    typ = ev[0]
    if typ in ("arrive", "leave"):
        cid = ev[1]
        name = CATS[cid]["name"]
        if typ == "arrive":
            return "{0}が遊びに来た".format(name)
        if typ == "leave":
            return "{0}が帰った".format(name)
    if typ == "actor_met":
        aid = ev[1]
        return "{0}と出会った".format(ACTORS[aid]["name"])
    if typ == "actor_arrive":
        aid = ev[1]
        return "{0}が来た".format(ACTORS[aid]["name"])
    return None


# ---------------------------------------------------------------------------
# 初期化
# ---------------------------------------------------------------------------

load_catalog()
