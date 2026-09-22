"""
ねこあつめ Pyxel 版 ― データ表(アイテムと猫)

ここに1行足すだけで、おもちゃ・エサ・猫・人・場所を増やせます(コードの変更は要りません)。
猫が1000匹、商品が数百種になっても動くように作ってあります。

ID は英数字とアンダースコア(セーブデータのキーになるので、あとから変えないこと)。
通貨は "s"=銀 / "g"=金。

【フェーズ1移行版】
- FOODS の6要素目に tags(dict) を追加。game.py の _food() / load_catalog() を対応させること。
- CATS の個性辞書に sex / traits / taste / affinity を追加。

【フェーズ3設計メモ】
- apply_reward() の unlocks 処理仕様:
  データ側: "unlocks": "obaachan" (actor ID) または "unlocks": "stage:mansion2"
  実装側: apply_reward() が flags.add(f"unlocked_{unlocks}") に変換して state に書き込む。
  例: "obaachan" → flag "unlocked_obaachan" を state["flags"] に追加
       "stage:mansion2" → flag "unlocked_stage_mansion2" を state["flags"] に追加
  ※ flag の綴りをデータ側に持たせず、ID / stage:xxx のまま実装側で変換する。
  ※ ACTORS の requires 側は変換後の flag 名("unlocked_obaachan")を参照する。
- validate_world() は outcome/unlocks の "stage:xxx" と "flag:xxx" を検証対象に含める。

【タグ辞書の取り決め】
- エサタグ: meat(肉), fish(魚), grain(穀物), grass(植物/草)
- 猫の taste キー: meat, fish, grass  (grain は現状猫側に対応キーなし)
  ※ grain は穀物タグ。現状の猫には grain 好みがいないために、taste_score=0 となる。
    将来的に grain 好みの猫を追加する場合は taste={"grain": ...} を使うこと。
  ※ dry_food は {"meat": 0.5, "grain": 0.5}。grain 好みの猫がいない間は meat 成分のみが採用される。
"""

# ショップの種別(タブ): (種別ID, 表示名)。種別IDは TOYS="toy" / FOODS="food"
CATEGORIES = [("toy", "おもちゃ"), ("food", "エサ")]

# おもちゃ: (ID, 名前, 価格, 通貨, 庭で使うマス数(=同時に遊べる猫の数), 説明)
TOYS = [
    ("rubber_ball", "ゴムボール", 5, "s", 1, "小さな明るいオレンジ色のゴムボール。ふにふにで、ピコピコ鳴るよ!"),
    ("sparkle_ball", "キラキラボール", 5, "g", 1, "きらめくラメが入った、小さな透明のゴムボール!"),
    ("yarn_ball", "毛糸玉", 10, "s", 1, "赤い糸玉だよ!"),
    ("fancy_yarn_ball", "高級毛糸玉", 15, "g", 1, "赤・青・緑に銀色の糸がきらめく、高級な毛糸玉!"),
    ("tennis_ball", "テニスボール", 25, "s", 1, "毛羽立った鮮やかな黄色のテニスボール!"),
    ("paper_bag", "紙袋", 20, "s", 1, "スーパーの紙袋。ガサガサいい音がするよ!"),
    ("scratching_post", "爪とぎポール", 5, "g", 1, "猫がバリバリ爪をとげる、いい感じのポール!"),
    ("fancy_scratching_post", "高級爪とぎポール", 15, "g", 1, "硬い木と合成皮革でできたデラックスな爪とぎポール!"),
    ("fishbowl", "金魚鉢", 10, "g", 1, "かわいい金魚が泳ぐ小さな金魚鉢!"),
    ("small_condo", "小型キャットハウス", 75, "s", 3, "少しだけカーペット張りの小さなキャットハウス。3匹まで入れるよ!"),
    ("medium_condo", "中型キャットハウス", 150, "s", 5, "全面カーペット張りの中くらいのキャットハウス。5匹まで入れるよ!"),
    ("large_condo", "大型キャットハウス", 50, "g", 6, "高級ベルベル絨毯に手縫いの仕上げ、6匹まで入れる大きなキャットハウス!"),
    ("catnip", "マタタビの袋", 7, "g", 1, "小さなマタタビの袋。においで猫が大興奮!"),
    ("plain_pillow", "無地のクッション", 30, "s", 1, "青くてやわらかい、小さな無地のクッション!"),
    ("tie_dye_pillow", "絞り染めのクッション", 15, "g", 1, "絞り染めのフリースでできた、ふかふかの厚いクッション!"),
    ("plastic_bucket", "プラスチックのバケツ", 20, "s", 1, "白い取っ手のついた小さな緑のバケツ。バケツがあるぞ!"),
    ("cereal_box", "シリアルの箱", 15, "s", 1, "「シナモンとろけるゴロゴロ」の空き箱!"),
    ("fruit_box", "果物の箱", 75, "s", 1, "小さな段ボールの果物箱。入れそうなら、入っちゃう!"),
    ("large_box", "大きな箱", 30, "g", 4, "もとは家電が入っていた大きな段ボール箱。猫が4匹まで入れるよ!"),
    ("butterfly_toy", "蝶々のおもちゃ", 15, "g", 1, "長い棒の先の糸に蝶々がぶら下がった、かわいいおもちゃ。ひらひら楽しい!"),
    ("laser_pointer", "ロボットレーザーポインター", 125, "g", 1, "レーザーポインターを持った小さなロボットアーム。みんな大好き!"),
    ("rainbow_umbrella", "虹色の傘", 25, "g", 5, "虹色もようの大きな傘。猫が5匹まで入れるよ!"),
    ("plain_umbrella", "無地の傘", 250, "s", 4, "明るい黄色の大きな無地の傘。猫が4匹まで入れるよ!"),
    ("plush_froggy", "カエルのぬいぐるみ", 75, "s", 1, "ぎゅっとすると鳴く、緑のかわいいカエルのぬいぐるみ!"),
]

# エサ: (ID, 名前, 価格, 通貨, もつ時間(分), 好みタグ, 説明)
# 【フェーズ1】6要素目に tags(dict) を追加。
#   タグ例: {"meat": 0.5, "fish": 1.0, "grass": 1.0}
#   game.py の _food(name, cost, cur, minutes, tags, desc) に対応
# 【後方互換メモ】タプルは省略できないため、旧5要素行と混在させる場合は
#   game.py の load_catalog() 側で row[5] if len(row) > 5 else {} を使うこと。
# 【タグ辞書】meat=肉, fish=魚, grain=穀物, grass=植物/草
#   grain は現状猫の taste 側に対応キーがない(将来的に grain 好みの猫を加予定)。
FOODS = [
    # (id, name, cost, currency, amount, tags, desc)
    # amount = エサの量（猫の食欲に応じて消費される）
    ("dry_food", "ドライフード", 10, "s", 300, {"meat": 0.5, "grain": 0.5},
     "ごく普通のドライフード。カリカリでシンプルな味。"),
    ("wet_food", "ウェットフード缶", 2, "g", 300, {"fish": 1.0},
     "ごく普通のウェットフード。においが強烈!"),
    ("fancy_food", "高級フード缶", 5, "g", 300, {"fish": 0.7, "meat": 0.3},
     "職人が手づくりした、フェアトレードのオーガニック猫ごはん。んー、おいしい!"),
]

# 猫: (ID, 名前, 紹介文, お宝, {個性の上書き})
#   個性のキー:
#     sex: "m" / "f"
#     traits: {"appetite": 0〜1, "friendly": 0〜1, "wary": 0〜1}  既定値はすべて0.5
#     taste: {"meat": 重み, "fish": 重み, "grass": 重み}  エサのtagsと突き合わせる
#     affinity: {"turtle": 0〜1, ...}  同居生き物との親和性
#     strength, entry_chance, time_limit, fav_toy: 既存と同じ意味
#     habitat: [場ID, ...]  既定は ["garden"]（フェーズ4で追加予定）
#   個性辞書は省略可(省略時はすべて既定値)。
DEFAULT_TRAITS = {"appetite": 0.5, "friendly": 0.5, "wary": 0.5}

CATS = [
    ("gordo", "ゴードー", "いつもあなたのごはんを食べにくる、いちばん手のかかる猫",
     "役に立たない木切れ(ゴードーだから)",
     {"sex": "m",
      "traits": {"appetite": 0.8, "friendly": 0.4, "wary": 0.3},
      "taste": {"meat": 1.0, "fish": 0.2},
      "entry_chance": 0.3}),
    ("pukka", "プッカ", "クリーム色のぶちがある白い短毛で、緑の目の猫。レーザーを追いかけたりサーフィンをするのが大好き",
     "サーフワックスのかたまり",
     {"sex": "f",
      "traits": {"appetite": 0.6, "friendly": 0.7, "wary": 0.2},
      "taste": {"fish": 0.8, "meat": 0.3},
      "entry_chance": 0.3}),
    ("peebles", "ピーブルズ", "青い目の白黒の短毛猫。デスメタルとマタタビの山が好き",
     "べっ甲のギターピック",
     {"sex": "m",
      "traits": {"appetite": 0.5, "friendly": 0.3, "wary": 0.5},
      "taste": {"grass": 1.0, "meat": 0.4},
      "entry_chance": 0.3}),
    ("tarawa", "タラワ", "白い筋の入ったグレーの長毛で、灰色の目の猫。のんびりするのと、鳥を追いかけるのが好き",
     "アオカケスの羽根",
     {"strength": 6, "sex": "f",
      "traits": {"appetite": 0.3, "friendly": 0.2, "wary": 0.6},
      "taste": {"grass": 1.0},
      "affinity": {"turtle": 0.8},
      "entry_chance": 0.3}),
    ("felix", "フェリックス", "オレンジと白の短毛のトラ猫で、黄色い目。とてもおだやかで、一日中ほとんど瞑想している",
     "仏像のお香立て",
     {"sex": "m",
      "traits": {"appetite": 0.4, "friendly": 0.5, "wary": 0.2},
      "taste": {"meat": 0.6, "fish": 0.4},
      "entry_chance": 0.3}),
]


# ===========================================================================
# フェーズ3: 新規データ(取引品・訪問者・人・場所)
# 【注意】これらは game.py / nekoatsume.py にフェーズ3の実装が入るまで、
#         ゲームには影響しません(validate_world() で整合性チェックのみ)。
# ===========================================================================

# 物(取引品。庭には置かない。ショップの種別タブにも並べない):
# (ID, 名前, 好みタグ, 説明)
GOODS = [
    ("smartphone", "スマホ", {"electronics": 1.0}, "使い古しのスマートフォン。"),
    ("laptop", "パソコン", {"electronics": 1.0}, "使い古しのノートパソコン。"),
    ("sweets", "お菓子", {"sweets": 1.0}, "素朴な焼き菓子。"),
    ("amulet", "お守り", {}, "古びたお守り。"),
]

# 訪問者・人・その他キャラ: (ID, 種類, 名前, 紹介文, 個性の上書き辞書)
#   種類: "cat"(既存CATSと同じ流れ) / "visitor"(通り過ぎるだけ) / "person"(居着く・ギフトを受け取る)
#   個性のキー:
#     habitat: [場所ID, ...]      出現しうる場所のリスト
#     requires: {条件}            meets() に渡す出現条件辞書
#     gifts: [(outcome, 重み), ...]  visitor が帰るときの抽選
#     wants: {タグ: 重み}         person が好む物のタグ
#     one_time_reward: {..., "unlocks": 次のID}
#         最初に wants を満たす物を渡されたときだけ発動
#   outcome の形式: "item:xxx" / "creature:xxx" / "flag:xxx" / "stage:xxx"
#
# 【unlocks の取り決め】
#   データ側: "unlocks": "obaachan" (actor ID) または "unlocks": "stage:mansion2"
#   実装側(apply_reward): flags.add(f"unlocked_{unlocks}") で state["flags"] に書き込む
#   例: "obaachan" → "unlocked_obaachan" / "stage:mansion2" → "unlocked_stage_mansion2"
#   requires 側は変換後の flag 名を参照: {"flag": "unlocked_obaachan"}
ACTORS = [
    ("catseye_a", "visitor", "キャツアイの誰か",
     "使い古しの電子機器を引き取って売り買いしている。お金にはこだわらず、猫を愛している。",
     {"habitat": ["mansion"], "requires": {"level": 5},
      "gifts": [("item:smartphone", 0.5), ("item:laptop", 0.2), ("item:sweets", 0.3)]}),

    ("jiro", "person", "じろうさん",
     "屋敷の近くに住む、物知りな老人。壊れた機械を直すのが得意。",
     {"habitat": ["mansion"], "requires": {"items": ["smartphone"]},
      "wants": {"electronics": 1},
      "one_time_reward": {"creature": "turtle", "unlocks": "obaachan"}}),

    ("obaachan", "person", "おばあちゃん",
     "お菓子作りが得意で、庭先に顔を出す優しい人。",
     {"habitat": ["mansion"], "requires": {"flag": "unlocked_obaachan"},
      "wants": {"sweets": 1},
      # 【フェーズ4】stage:mansion2 は PLACES に追加済み。
      "one_time_reward": {"item": "amulet", "unlocks": "stage:mansion2"}}),
]

# 場所: (ID, 表示名, マス数, 水辺の種類, 解放条件)
#   水辺の種類: "puddle"(小水たまり) / "pond"(池) / "none"(水辺なし)
#   解放条件: requires 辞書または None(最初から解放)
PLACES = [
    ("garden", "庭", 6, "puddle", None),
    ("mansion", "屋敷", 12, "pond", {"flag": "unlocked_stage_mansion"}),
    ("mansion2", "屋敷の奥", 10, "pond", {"flag": "unlocked_stage_mansion2"}),
]


# ===========================================================================
# ユーティリティ(データ検証・スコア計算)
# ===========================================================================

# フェーズ4で追加予定の stage ID。validate_world() で参照切れとして扱わない。
# フェーズ4実装時に PLACES に追加したら、ここから削除すること。
PENDING_STAGES = set()  # フェーズ4で mansion2 を PLACES に追加済み


def taste_score(cat_taste, food_tags):
    """猫の好み(taste)とエサのタグ(tags)から、相性(0以上)を出す。

    重み合計が1でない場合は正規化する。
    情報がない場合は 0.5(中庸)を返す。
    結果は max(0.1, ...) で下限を切る(来訪率が0にならないように)。
    """
    if not cat_taste or not food_tags:
        return 0.5  # 情報がなければ中庸
    total_weight = sum(cat_taste.values())
    if total_weight == 0:
        return 0.5
    raw = sum(cat_taste.get(tag, 0.0) * weight for tag, weight in food_tags.items())
    normalized = raw / total_weight
    return max(0.1, normalized)


def parse_outcome(outcome):
    """'item:smartphone' -> ('item', 'smartphone') のように分解する。"""
    kind, _, value = outcome.partition(":")
    return kind, value


def validate_world():
    """ID の重複や、参照切れがないかを確認する。
    game.py の load_catalog() と同じ考え方で、起動時に1回呼ぶ想定。
    エラリストを返す。問題がなければ空リストを返す。"""
    errors = []

    cat_ids = [c[0] for c in CATS]
    if len(cat_ids) != len(set(cat_ids)):
        errors.append("CATS にIDの重複があります")

    food_ids = [f[0] for f in FOODS]
    if len(food_ids) != len(set(food_ids)):
        errors.append("FOODS にIDの重複があります")

    if len({t[0] for t in TOYS}) != len(TOYS):
        errors.append("TOYS にIDの重複があります")

    good_ids = {g[0] for g in GOODS}
    if len(good_ids) != len(GOODS):
        errors.append("GOODS にIDの重複があります")

    actor_ids = [a[0] for a in ACTORS]
    if len(actor_ids) != len(set(actor_ids)):
        errors.append("ACTORS にIDの重複があります")

    place_ids = {p[0] for p in PLACES}
    if len(place_ids) != len(PLACES):
        errors.append("PLACES にIDの重複があります")

    # 種別間の ID 衝突チェック
    for fid in food_ids:
        if fid in {t[0] for t in TOYS}:
            errors.append(f"FOODS の '{fid}' が TOYS とIDが衝突しています")
    for gid in good_ids:
        if gid in {t[0] for t in TOYS}:
            errors.append(f"GOODS の '{gid}' が TOYS とIDが衝突しています")
        if gid in food_ids:
            errors.append(f"GOODS の '{gid}' が FOODS とIDが衝突しています")
    for aid in actor_ids:
        if aid in cat_ids:
            errors.append(f"ACTORS の '{aid}' が CATS とIDが衝突しています")

    # ACTORS の参照整合性チェック
    for actor_id, kind, name, desc, opts in ACTORS:
        for h in opts.get("habitat", []):
            if h not in place_ids:
                errors.append(f"{actor_id} の habitat '{h}' が PLACES にありません")
        for outcome, _w in opts.get("gifts", []):
            k, v = parse_outcome(outcome)
            if k == "item" and v not in good_ids:
                errors.append(f"{actor_id} の gifts '{outcome}' が GOODS にありません")
        reward = opts.get("one_time_reward")
        if reward:
            if "item" in reward and reward["item"] not in good_ids:
                errors.append(f"{actor_id} の one_time_reward の item '{reward['item']}' が GOODS にありません")
            # unlocks の検証
            unlocks = reward.get("unlocks")
            if unlocks:
                uk, uv = parse_outcome(unlocks) if ":" in unlocks else ("actor", unlocks)
                if uk == "stage":
                    # stage:xxx は PLACES のIDまたは PENDING_STAGES として検証
                    if uv not in place_ids and uv not in PENDING_STAGES:
                        errors.append(f"{actor_id} の unlocks '{unlocks}' が PLACES にも PENDING_STAGES にもありません")
                elif uk == "flag":
                    # flag:xxx は実装側で扱うのでデータ整合性のみ確認
                    pass
                else:
                    # actor ID として検証
                    if unlocks not in actor_ids:
                        errors.append(f"{actor_id} の unlocks '{unlocks}' が ACTORS にありません")

    return errors


def validate_world_or_raise():
    """validate_world() のラッパー。エラーがあれば ValueError を投げる。"""
    errors = validate_world()
    if errors:
        raise ValueError("\n".join(errors))


if __name__ == "__main__":
    validate_world_or_raise()
    print("OK: catalog is consistent")
    # ID 引きでサンプルを表示(行追加時に壊れない)
    tarawa = next((c for c in CATS if c[0] == "tarawa"), None)
    wet_food = next((f for f in FOODS if f[0] == "wet_food"), None)
    if tarawa and wet_food:
        print("taste_score sample (tarawa vs wet_food):",
              taste_score(tarawa[4].get("taste", {}), wet_food[5]))

# ===== 店の人セリフ =====
SHOP_KEEPER_LINES = [
    "ナイスチョイスですね",
    "それはいい選択ですよ",
    "まいどあり",
    "すてきなチョイスです",
    "これはおすすめですよ",
]
