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
- meets() で出現条件判定
- 猫の初来訪時にレベルが上昇
- CATALOG_VERSION = 4、loads() でバージョン4へのマイグレーション

【フェーズ3変更点】
- GOODS / ACTORS / PLACES を読み込み、取引システムを実装
- inventory（取引品所持）/ actor_states（訪問者・人の状態）を追加
- current_place / places（場所別 yard/food/water）を追加
- give() / apply_reward() / _pick_gift() / _match_wants() を実装
- advance() に訪問者(visitor)の来訪・滞在・gifts抽選、人(person)の出現・退去を追加
- event_text() に actor イベントを追加
- available_places() / switch_place() を実装
- CATALOG_VERSION = 5、loads() で yard/food/food_remaining を places["garden"] へ移行
"""

import collections
import json
import random

import catalog

# ---------------------------------------------------------------------------
# カタログデータ(起動時に load_catalog() で読み込まれる)
# ---------------------------------------------------------------------------

CATALOG_VERSION = 5  # 【フーズ3】

IDS_BY_KIND = {}   # {"toy": [ID, ...], "food": [ID, ...]}
ITEMS = {}         # {ID: spec}
TOYS = {}          # {ID: toy_spec}
FOODS = {}         # {ID: food_spec}
CATS = {}          # {ID: cat_spec}
GOODS = {}         # {ID: good_spec}      【フェーズ3】
ACTORS = {}        # {ID: actor_spec}     【フェーズ3】
PLACES = {}        # {ID: place_spec}     【フェーズ3】

Result = collections.namedtuple("Result", ["ok", "msg", "code", "events"])
Result.__new__.__defaults__ = ([],)

SHOP_FILTERS = [("all", "すべて"), ("afford", "買える"), ("new", "新")]
SHOP_SORTS = [("default", "並び"), ("price_asc", "安い"), ("price_desc", "高い")]
SHOP_KINDS = [("toy", "おもちゃ"), ("food", "エサ")]  # 【フェーズ3】UI用

SPACE = 6  # 庭のマス数（既定値）


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


def _good(name, tags, desc):
    return {"name": name, "tags": tags, "desc": desc}


def _actor(kind, name, desc, **opts):
    return {
        "kind": kind,
        "name": name,
        "desc": desc,
        "habitat": opts.get("habitat", ["garden"]),
        "requires": opts.get("requires", {}),
        "gifts": opts.get("gifts", []),
        "wants": opts.get("wants", {}),
        "one_time_reward": opts.get("one_time_reward", None),
        "entry_chance": opts.get("entry_chance", 0.0),
        "time_limit": opts.get("time_limit", 0),
    }


def _place(name, space, water, requires):
    return {"name": name, "space": space, "water": water, "requires": requires}


def load_catalog():
    IDS_BY_KIND.clear()
    ITEMS.clear()
    TOYS.clear()
    FOODS.clear()
    CATS.clear()
    GOODS.clear()      # 【フェーズ3】
    ACTORS.clear()     # 【フェーズ3】
    PLACES.clear()     # 【フェーズ3】

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

    # 【フェーズ3】GOODS / ACTORS / PLACES を読み込み
    for row in catalog.GOODS:
        gid = row[0]
        GOODS[gid] = _good(row[1], row[2], row[3])

    for row in catalog.ACTORS:
        aid = row[0]
        kind = row[1]
        name = row[2]
        desc = row[3] if len(row) > 3 else ""
        opts = row[4] if len(row) > 4 else {}
        ACTORS[aid] = _actor(kind, name, desc, **opts)

    for row in catalog.PLACES:
        pid = row[0]
        PLACES[pid] = _place(row[1], row[2], row[3], row[4] if len(row) > 4 else None)

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

    # 【フェーズ3】ver < 5: inventory / actor_states / current_place / places / water を追加
    if ver < 5:
        data.setdefault("inventory", {})
        data.setdefault("actor_states", {
            aid: {"met": False, "in_place": False, "timer": 0, "reward_given": False}
            for aid in ACTORS
        })
        data.setdefault("current_place", "garden")
        data.setdefault("places", {
            pid: {"yard": [], "food": None, "food_remaining": 0, "water": {}}
            for pid in PLACES
        })
        data.setdefault("water", {})
        # 旧データの yard/food/food_remaining を places["garden"] に移行
        if "yard" in data and "places" in data:
            data["places"]["garden"]["yard"] = data.pop("yard")
        if "food" in data and "places" in data:
            data["places"]["garden"]["food"] = data.pop("food")
        if "food_remaining" in data and "places" in data:
            data["places"]["garden"]["food_remaining"] = data.pop("food_remaining")
        data["version"] = 5

    cats = data.setdefault("cats", {})
    for cid in CATS:
        if cid not in cats:
            cats[cid] = new_state(0)["cats"][cid]
    for cid in list(cats):
        if cid not in CATS:
            del cats[cid]

    # actor_states の加・削除に追従
    actor_states = data.setdefault("actor_states", {})
    for aid in ACTORS:
        if aid not in actor_states:
            actor_states[aid] = {"met": False, "in_place": False, "timer": 0, "reward_given": False}
    for aid in list(actor_states):
        if aid not in ACTORS:
            del actor_states[aid]

    # places の追加・削除に追従
    places = data.setdefault("places", {})
    for pid in PLACES:
        if pid not in places:
            places[pid] = {"yard": [], "food": None, "food_remaining": 0, "water": {}}
    for pid in list(places):
        if pid not in PLACES:
            del places[pid]

    if "current_place" not in data:
        data["current_place"] = "garden"

    if "last_advance" not in data:
        data["last_advance"] = now

    return data


# ---------------------------------------------------------------------------
# 状態の初期化
# ---------------------------------------------------------------------------

def new_state(now):
    return {
        "s_fish": 15,
        "g_fish": 0,
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
        # 【フェーズ3】
        "inventory": {},
        "actor_states": {
            aid: {"met": False, "in_place": False, "timer": 0, "reward_given": False}
            for aid in ACTORS
        },
        "current_place": "garden",
        "places": {
            pid: {"yard": [], "food": None, "food_remaining": 0, "water": {}}
            for pid in PLACES
        },
        "water": {},  # 【フェーズ3】水辺ペット（亀など）
    }


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
# 場所ヘルパー
# ---------------------------------------------------------------------------

def _place_data(state, place_id=None):
    pid = place_id or state.get("current_place", "garden")
    return state["places"][pid]


def _space(place_id):
    return PLACES.get(place_id, {}).get("space", SPACE)


def available_places(state):
    result = []
    for pid, spec in PLACES.items():
        req = spec.get("requires")
        if not req or meets(req, state):
            result.append(pid)
    return result


def switch_place(state, place_id):
    if place_id not in PLACES:
        return Result(False, "その場所はありません", "no_place")
    req = PLACES[place_id].get("requires")
    if req and not meets(req, state):
        return Result(False, "まだ行けません", "locked")
    state["current_place"] = place_id
    # 猫を全員帰す
    for c in state["cats"].values():
        c["in_yard"] = False
        c["toy"] = None
        c["time_in_yard"] = 0
    # 訪問者・人を全員帰す
    for ast in state["actor_states"].values():
        ast["in_place"] = False
        ast["timer"] = 0
    return Result(True, PLACES[place_id]["name"] + "に移動した", "ok")


# ---------------------------------------------------------------------------
# 報酬処理
# ---------------------------------------------------------------------------

def _match_wants(wants, item_tags):
    if not wants:
        return False
    for tag, needed in wants.items():
        if item_tags.get(tag, 0) >= needed:
            return True
    return False


def _pick_gift(gifts):
    if not gifts:
        return None
    total = sum(w for _item, w in gifts)
    r = random.random() * total
    for item_id, w in gifts:
        r -= w
        if r <= 0:
            return item_id
    return gifts[-1][0]


def apply_reward(state, reward):
    events = []
    if not reward:
        return events
    if "item" in reward:
        state["inventory"][reward["item"]] = state["inventory"].get(reward["item"], 0) + 1
        events.append(("got_item", reward["item"]))
    if "creature" in reward:
        state["water"][reward["creature"]] = True
        events.append(("got_creature", reward["creature"]))
    if "unlocks" in reward:
        unlocks = reward["unlocks"]
        flag = f"unlocked_{unlocks}"
        state["flags"].add(flag)
        events.append(("unlocked", unlocks))
    return events


def give(state, actor_id, item_id):
    actor = ACTORS.get(actor_id)
    if not actor:
        return Result(False, "その人はいません", "no_actor")
    inv = state["inventory"]
    if inv.get(item_id, 0) <= 0:
        return Result(False, "持っていません", "not_owned")
    item = GOODS.get(item_id, {})
    wants = actor.get("wants", {})
    tags = item.get("tags", {})
    if not _match_wants(wants, tags):
        return Result(False, "{0}は興味がないようです".format(actor["name"]), "not_wanted")
    inv[item_id] -= 1
    if inv[item_id] <= 0:
        del inv[item_id]
    ast = state["actor_states"][actor_id]
    ast["reward_given"] = True
    events = [("gave", actor_id, item_id)]
    reward = actor.get("one_time_reward")
    if reward:
        events.extend(apply_reward(state, reward))
    # 信頼度上昇
    for c in state["cats"].values():
        if c["met"]:
            c["trust"] = min(1.0, c["trust"] + 0.05)
    return Result(True, "{0}に{1}を渡した".format(actor["name"], item["name"]), "ok", events=events)


# ---------------------------------------------------------------------------
# ゲーム進行
# ---------------------------------------------------------------------------

def advance(state, now):
    last = state.get("last_advance", now)
    elapsed = now - last
    ticks = min(int(elapsed // 60), 60)
    state["last_advance"] = now - (elapsed % 60)

    events = []
    visits = 0
    bonus_treasure = None

    cp = state.get("current_place", "garden")
    pd = _place_data(state, cp)
    food_id = pd.get("food")
    food_tags = FOODS.get(food_id, {}).get("tags", {}) if food_id else {}
    place_space = _space(cp)

    for _ in range(ticks):
        # ---- エサの減り ----
        if food_id and pd["food_remaining"] > 0:
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
            pd["food_remaining"] = max(0, pd["food_remaining"] - total_eat)

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
                # 猫が帰るときに銀のさかなを置いていく（基本1〜3匹、友好度で増加）
                amount = random.randint(1, 3)
                if spec["traits"]["friendly"] > 0.6:
                    amount += 1
                state["pending_money"].append((cid, amount, "s"))
                if random.random() < 0.1:
                    state["pending_treasures"].append(cid)
                    bonus_treasure = cid
                events.append(("leave", cid))

        # ---- 猫の来訪 ----
        if food_id and pd["food_remaining"] > 0:
            used = space_used(state, cp)
            free_space = place_space - used

            for cid, spec in CATS.items():
                c = state["cats"][cid]
                if c["in_yard"]:
                    continue

                # habitat チェック
                if cp not in spec.get("habitat", ["garden"]):
                    continue

                base_chance = spec["entry_chance"]
                taste = catalog.taste_score(spec["taste"], food_tags)
                fullness_factor = 1 - c["fullness"] * 0.6
                chance = base_chance * taste * fullness_factor

                if free_space <= 0:
                    continue

                if random.random() < chance:
                    yard = pd["yard"]
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

        # ---- 【フェーズ3】訪問者・人の進行 ----
        for aid, actor in ACTORS.items():
            ast = state["actor_states"][aid]
            if ast["in_place"]:
                ast["timer"] += 1
                if ast["timer"] >= actor["time_limit"]:
                    ast["in_place"] = False
                    ast["timer"] = 0
                    if actor["kind"] == "visitor" and actor["gifts"]:
                        gift = _pick_gift(actor["gifts"])
                        if gift and gift.startswith("item:"):
                            item_id = gift[5:]
                            state["inventory"][item_id] = state["inventory"].get(item_id, 0) + 1
                            events.append(("actor_gift", aid, item_id))
                    events.append(("actor_leave", aid))
            else:
                if cp not in actor.get("habitat", []):
                    continue
                if ast.get("reward_given"):
                    continue
                if not meets(actor.get("requires", {}), state):
                    continue
                # 人は meets で出現（初回のみ）、訪問者は entry_chance で抽選
                if actor["kind"] == "person" and not ast["met"]:
                    ast["in_place"] = True
                    ast["timer"] = 0
                    ast["met"] = True
                    state["met_actors"].add(aid)
                    gain_level(state, 1, "met_actor")
                    events.append(("actor_arrive", aid))
                elif actor["entry_chance"] > 0 and random.random() < actor["entry_chance"]:
                    ast["in_place"] = True
                    ast["timer"] = 0
                    ast["met"] = True
                    state["met_actors"].add(aid)
                    gain_level(state, 1, "met_actor")
                    events.append(("actor_arrive", aid))

    return {"ticks": ticks, "events": events, "visits": visits,
            "bonus_treasure": bonus_treasure,
            "first_visits": [cid for cid, c in state["cats"].items() if c["met"] and c["total_time"] == 0 and c["time_in_yard"] == 0]}


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
    return "{0}{1}".format(it["cost"], "s" if it["cur"] == "s" else "g")


# ---------------------------------------------------------------------------
# 庭の操作（場所対応）
# ---------------------------------------------------------------------------

def space_used(state, place_id=None):
    pd = _place_data(state, place_id)
    return sum(TOYS[t]["size"] for t in pd["yard"])


def place_toy(state, toy_id, place_id=None):
    pd = _place_data(state, place_id)
    if toy_id in pd["yard"]:
        return Result(False, "すでに置いてあります", "already_placed")
    pid = place_id or state.get("current_place", "garden")
    place_space = _space(pid)
    if space_used(state, pid) + TOYS[toy_id]["size"] > place_space:
        return Result(False, "スペースが足りません", "no_space")
    pd["yard"].append(toy_id)
    return Result(True, "{0}を置きました".format(TOYS[toy_id]["name"]), "ok")


def remove_toy(state, toy_id, place_id=None):
    pd = _place_data(state, place_id)
    if toy_id not in pd["yard"]:
        return Result(False, "置いてありません", "not_placed")
    pd["yard"].remove(toy_id)
    for c in state["cats"].values():
        if c["toy"] == toy_id:
            c["toy"] = None
    return Result(True, "{0}を片付けました".format(TOYS[toy_id]["name"]), "ok")


def set_food(state, food_id, force=False, place_id=None):
    if state["food_stock"].get(food_id, 0) <= 0:
        return Result(False, "持っていません", "not_owned")
    pd = _place_data(state, place_id)
    if pd["food"] and not force:
        return Result(False, "エサを置きかえますか？", "need_confirm")
    pd["food"] = food_id
    pd["food_remaining"] = FOODS[food_id]["minutes"]
    state["food_stock"][food_id] -= 1
    if state["food_stock"][food_id] <= 0:
        del state["food_stock"][food_id]
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
# クエリ
# ---------------------------------------------------------------------------

def occupants(state, toy_id, place_id=None):
    pd = _place_data(state, place_id)
    return [cid for cid, c in state["cats"].items() if c["in_yard"] and c["toy"] == toy_id]


def met_list(state):
    return [cid for cid in CATS if state["cats"][cid]["met"]]


# ---------------------------------------------------------------------------
# イベントテキスト
# ---------------------------------------------------------------------------

def event_text(ev):
    typ = ev[0]
    if typ == "arrive":
        return "{0}が遊びに来た".format(CATS[ev[1]]["name"])
    if typ == "leave":
        return "{0}が帰った".format(CATS[ev[1]]["name"])
    if typ == "actor_arrive":
        return "{0}が来た".format(ACTORS[ev[1]]["name"])
    if typ == "actor_leave":
        return "{0}が帰った".format(ACTORS[ev[1]]["name"])
    if typ == "actor_gift":
        item_name = GOODS.get(ev[2], {}).get("name", "何か")
        return "{0}が{1}を置いていった".format(ACTORS[ev[1]]["name"], item_name)
    return None


# ---------------------------------------------------------------------------
# 初期化
# ---------------------------------------------------------------------------

load_catalog()
