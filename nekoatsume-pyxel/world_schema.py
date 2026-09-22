"""
ねこあつめ Pyxel 版 ― データ表(アイテムと猫) 移行草案

【このファイルの位置づけ】
いまの catalog.py の「タプルの行を1つ足せば増やせる」スタイルを保ったまま、
猫の個性・訪問者(actor)・場所(place)・取引品(goods)を扱えるように拡張したもの。

本ファイルは「移行先の catalog.py 兼 移行計画書」です。
フェーズごとに game.py / nekoatsume.py へ反映していく想定です。

【移行フェーズ】
  フェーズ0: このファイルを catalog.py として配置(追加データのみ、動作に影響なし)
  フェーズ1: FOODS に tags を追加、CATS に個性を追加、game.py の _food/_cat を対応
  フェーズ2: 隠れレベル・条件判定を game.py に追加
  フェーズ3: GOODS / ACTORS / give() / sell() を game.py に追加、UI に「人」タブを追加
  フェーズ4: PLACES / 屋敷 / 水辺 を game.py・UI に追加
  フェーズ5: ユーザー間やり取り(先の話)
"""

# ===========================================================================
# フェーズ0: 既存データ(そのまま移行)
# ===========================================================================

# ショップの種別(タブ): (種別ID, 表示名)。種別IDは TOYS="toy" / FOODS="food"
CATEGORIES = [("toy", "おもちゃ"), ("food", "エサ")]

# おもちゃ: (ID, 名前, 価格, 通貨, 庭で使うマス数(=同時に遊べる猫の数), 説明)
TOYS = [
    ("rubber_ball", "ゴムボール", 5, "s", 1, "小さな明るいオレンジ色のゴムボール。ふにふにで、ピコピコ鳴るよ!"),
    ("sparkle_ball", "キラキラボール", 5, "g", 1, "きらめくラメが入った、小さな透明のゴムボール!"),
    ("yarn_ball", "毛糸玉", 10, "s", 1, "赤い毛糸玉だよ!"),
    ("fancy_yarn_ball", "高級毛糸玉", 15, "g", 1, "赤・青・緑に銀色の糸がきらめく、高級な毛糸玉!"),
    ("tennis_ball", "テニスボール", 25, "s", 1, "毛羽立った鮮やかな黄色のテニスボール!"),
    ("paper_bag", "紙袋", 20, "s", 1, "スーパーの紙袋。ガサガサいい音がするよ!"),
    ("scratching_post", "爪とぎポール", 5, "g", 1, "猫がバリバリ爪をとげる、いい感じのポール!"),
    ("fancy_scratching_post", "高級爪とぎポール", 15, "g", 1, "硬い木と合成皮革でできた、デラックスな爪とぎポール!"),
    ("fishbowl", "金魚鉢", 10, "g", 1, "かわいい金魚が泳ぐ小さな金魚鉢!"),
    ("small_condo", "小型キャットハウス", 75, "s", 3, "少しだけカーペット張りの小さなキャットハウス。3匹まで入れるよ!"),
    ("medium_condo", "中型キャットハウス", 150, "s", 5, "全面カーペット張りの中くらいのキャットハウス。5匹まで入れるよ!"),
    ("large_condo", "大型キャットハウス", 50, "g", 6, "高級ベルベル絨毯に手縫いの仕上、6匹まで入れる大きなキャットハウス!"),
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
# 【フェーズ1】6要素目に tags(dict) を追加。game.py の _food() / load_catalog() を対応させること。
#   タグの例: {"meat": 0.5, "fish": 1.0, "grass": 1.0}
#   タグがないエサは dict {} または省略(後方互換)。
FOODS = [
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
#     traits: {"appetite": 0〜1, "friendly": 0〜1, "wary": 0〜1}
#     taste: {"meat": 重み, "fish": 重み, "grass": 重み}
#     affinity: {"turtle": 0〜1, ...}  同居生き物との親和性
#     strength, entry_chance, time_limit, fav_toy: 既存と同じ意味
# 【フェーズ1】個性辞書は省略可(省略時既定値)。既存の5匹は段階的に個性を足していく。
DEFAULT_TRAITS = {"appetite": 0.5, "friendly": 0.5, "wary": 0.5}

CATS = [
    ("gordo", "ゴードー", "いつもあなたのごはんを食べにくる、いちばん手のかかる猫",
     "役に立たない木切れ(ゴードーだから)",
     {"sex": "m",
      "traits": {"appetite": 0.8, "friendly": 0.4, "wary": 0.3},
      "taste": {"meat": 1.0, "fish": 0.2}}),
    ("pukka", "プッカ", "クリーム色のぶちがある白い短毛で、緑の目の猫。レーザーを追いかけたり、サーフィンをするのが大好き",
     "サーフワックスのかたまり",
     {"sex": "f",
      "traits": {"appetite": 0.6, "friendly": 0.7, "wary": 0.2},
      "taste": {"fish": 0.8, "meat": 0.3}}),
    ("peebles", "ピーブルズ", "青い目の白黒の短毛猫。デスメタルとマタタビの山が好き",
     "べっ甲のギターピック",
     {"sex": "m",
      "traits": {"appetite": 0.5, "friendly": 0.3, "wary": 0.5},
      "taste": {"grass": 1.0, "meat": 0.4}}),
    ("tarawa", "タラワ", "白い筋の入ったグレーの長毛で、灰色の目の猫。のんびりするのと、鳥を追いかけるのが好き",
     "アオカケスの羽根",
     {"strength": 6, "sex": "f",
      "traits": {"appetite": 0.3, "friendly": 0.2, "wary": 0.6},
      "taste": {"grass": 1.0},
      "affinity": {"turtle": 0.8}}),
    ("felix", "フェリックス", "オレンジと白の短毛のトラ猫で、黄色い目。とてもおだやかで、一日中ほとんど瞑想している",
     "仏像のお香立て",
     {"sex": "m",
      "traits": {"appetite": 0.4, "friendly": 0.5, "wary": 0.2},
      "taste": {"meat": 0.6, "fish": 0.4}}),
]


# ===========================================================================
# フェーズ3: 新規データ(取引品・訪問者・人・場所)
# ===========================================================================

# 物(取引品。庭には置かない。ショップの種別タブにも並べない):
# (ID, 名前, 好みタグ, 説明)
#   好みタグ: person の wants と突き合わせる用。例: {"electronics": 1.0}
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
      "one_time_reward": {"item": "amulet", "unlocks": "stage:mansion2"}}),
]

# 場所: (ID, 表示名, マス数, 水辺の種類, 解放条件)
#   水辺の種類: "puddle"(小水たまり) / "pond"(池) / "none"(水辺なし)
#   解放条件: requires 辞書または None(最初から解放)
PLACES = [
    ("garden", "庭", 6, "puddle", None),
    ("mansion", "屋敷", 12, "pond", {"flag": "unlocked_stage_mansion"}),
]


# ===========================================================================
# ユーティリティ(データ検証・スコア計)
# ===========================================================================

def taste_score(cat_taste, food_tags):
    """猫の好み(taste)とエサのタグ(tags)から、相性(0以上)を出す。"""
    if not cat_taste or not food_tags:
        return 0.5  # 情報がなければ中庸
    return sum(cat_taste.get(tag, 0.0) * weight for tag, weight in food_tags.items())


def parse_outcome(outcome):
    """'item:smartphone' -> ('item', 'smartphone') のように分解する。"""
    kind, _, value = outcome.partition(":")
    return kind, value


def validate_world():
    """ID の重複や、参照切れがないかを確認する。
    game.py の load_catalog() と同じ考え方で、起動時に1回呼ぶ想定。"""
    errors = []

    cat_ids = [c[0] for c in CATS]
    if len(cat_ids) != len(set(cat_ids)):
        errors.append("CATS にIDの重複があります")

    food_ids = [f[0] for f in FOODS]
    if len(food_ids) != len(set(food_ids)):
        errors.append("FOODS にIDの重複があります")

    toy_ids = {t[0] for t in TOYS}
    if len(toy_ids) != len(TOYS):
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
        if fid in toy_ids:
            errors.append(f"FOODS の '{fid}' が TOYS とIDが衝突しています")
    for gid in good_ids:
        if gid in toy_ids:
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
                errors.append(f"{actor_id} の gifts '{outcome}' が GOODS にりません")
        reward = opts.get("one_time_reward")
        if reward and "item" in reward and reward["item"] not in good_ids:
            errors.append(f"{actor_id} の one_time_reward の item '{reward['item']}' が GOODS にありませ")

    if errors:
        raise ValueError("\n".join(errors))


# ===========================================================================
# 移行計画: game.py への変更点
# ===========================================================================
"""
【フェーズ1】猫の個性・エサのタグ

1. _food(name, cost, cur, minutes, tags, desc)  ← tags 引数を追加
   load_catalog() の FOODS 処理で row[5] を tags、row[6] を desc にする。

2. _cat(name, desc, treasure, **opts)  ← **opts で個性辞書を受け取る(既存のままでOK)
   ただし opts から sex/traits/taste/affinity を取り出して保存する。

3. 猫の状態に隠し変数を追加:
   cat_state = {..., "fullness": 0.5, "trust": 0.0, "happiness": 0.5}

4. advance() の来訪率計算に taste_score() を組み込む:
   base_chance = spec.entry_chance * taste_score(cat_taste, food_tags) * (1 - fullness)

5. エサの減り方を「時間で1ずつ」から「庭にいる猫が食べた分」に変更:
   appetite が高い猫ほど1回に多く食べる → food_remaining が減る。

【フェーズ2】隠れレベル・条件判定

6. new_state(now) に以下を追加:
   state["player_name"] = "黒いネコちゃん"  # 初回起動時に決める
   state["level"] = 0
   state["ever_had"] = set()
   state["flags"] = set()
   state["met_actors"] = {}
   state["created_at"] = now
   state["log"] = []

7. dumps/loads の _sanitize に ever_had / flags / met_actors を追加(set化)。

8. meets(state, requires) を game.py に追加。

9. gain_level(state, reason) を追加。以下のタイミングで呼ぶ:
   - 新しい猫と初めて出会った: gain_level(state, "met_new_cat")
   - ギフト連鎖が進んだ: gain_level(state, "chain_step")
   - 新しい場所を開いた: gain_level(state, "stage_unlocked")

【フェーズ3】訪問者・人・取引

10. state に以下を追加:
    state["owned_goods"] = set()      # 持っている取引品
    state["trust_person"] = {}         # {actor_id: 信頼度}
    state["_rewarded_actors"] = set() # one_time_reward 済み actor_id
    state["pets"] = set()             # 庭に住みついている生き物(亀など)

11. apply_reward(state, reward, rng) を追加。

12. give(state, actor_def, item_id, rng) を追加:
    - owned_goods に item_id があるか確認
    - actor の wants と item の tags から score を計算
    - trust_person[actor_id] += score
    - score > 0 かつ未報酬なら one_time_reward を適用
    - Result を返す

13. sell(state, actor_def, item_id, rng) を追加:
    - owned_goods から削除
    - actor の wants に応じてさかなを入手
    - trust の上がりは小さいまたは無し
    - Result を返す

14. advance() に visitor の出現・滞在・帰宅を追加:
    - meets(state, actor.requires) で出現可否を判定
    - 帰るときに gifts から抽選 → pending_treasures と同じ形で受け取り待ちに積む

【フェーズ4】場所・屋敷・水辺

15. state["place"] = "garden" を追加。
    state["places"] = {
        "garden":  {"yard": [...], "occ": {...}, "pets": []},
        "mansion": {"yard": [], "occ": {}, "pets": []},
    }

16. space_used(), place_toy(), remove_toy() を place 対応に修正。

17. shop_ids() に requires チェックを追加(品揃えを場所・進行度で変える)。

18. 水辺の advance を追加:
    - pets(亀など)は別時間軸で動く
    - 亀がいると猫の affinity が来訪率・滞在時間に補正をかける
"""


# ===========================================================================
# 移行計画: nekoatsume.py(UI) への変更点
# ===========================================================================
"""
【フェーズ1】猫の個性反映(UI表示)

1. draw_cats() のプロフィールに性別(♂/♀)を表示。

2. _cat_blocks() に「満腹・信頼・機嫌」の反応文を追加:
   - fullness が高い: "おなかいっぱいのようだ"
   - trust が低い: "遠くからこちらを見ている"
   - trust が高い: "すりすりと足元を回った"
   - affinity(turtle) が高く亀がいる: "亀のそばで丸くなっている"

3. エサのタグはユーザーには見せない。猫の反応文で好みを感じさせる。

【フェーズ3】人・取引UI

4. タブを増やす(または「にわ」画面に統合):
   TABS = [("yard", "にわ"), ("shop", "ショップ"), ("bag", "もちもの"),
           ("cats", "おたから"), ("people", "人々"), ("help", "ヘルプ")]
   ※ タブが6つになると画面幅が厳しいので、◀ ▶ でめくる形にするか検討。

5. 「人々」タブ(または「にわ」の一部):
   - 出現している person を一覧表示
   - タップで「あげる」「売る」のボタンを表示
   - 持ち物(bag)に goods を表示し、人をタップしてから渡す流れ

6. 取引の反応文をタイプライターで表示:
   - give(): "スマホを受け取って、目を丸くした"
   - sell(): "少しだけお金を出して受け取った"
   - one_time_reward 発動時: "亀も喜んでいるよ" → 次の日に亀が出現

7. visitor(キャツアイなど)の出現は「にわ」のできごとログに出す:
   - "キャツアイの誰かが、使い古しのスマホを置いていった"
   - 受け取りは「にわ」の「お宝を受け取る」ボタンと同じ流れ

【フェーズ4】場所・水辺

8. 「にわ」画面に場所名を表示(「庭」または「屋敷」)。

9. 屋敷への移行は静かに:
   - 解放された日の「にわ」で: "庭が、いつの間にか屋敷になっている"
   - ショップの品揃えが変わっていることで気づかせる

10. 水辺の表示:
    - 庭: "隅に小さな水たまりがある"
    - 屋敷: "池で亀が日向ぼっこをしている"
    - 亀が潜っているとき: "亀は今、水の中に潜っている"

11. 猫と亀の相性を「にわ」のできごとで表現:
    - "猫が、亀の日向ぼっこをじっと見ている"
    - "猫と亀が、それぞれ日向ぼっこをしている"
"""


# ===========================================================================
# セーブデータのバージョン管理
# ===========================================================================
"""
【バージョンアップ計画】

現在のセーブデータ version は game.py の CATALOG_VERSION で管理。
新しいフィールドを追加するたびに version を上げ、loads() で古いデータを
新しい形式にマイグレーションする。

フェーズ1: version += 1
  - 猫の状態に fullness / trust / happiness を追加(既定値で初期化)
  - FOODS の tags 対応(旧データには tags がないので空dictで補完)

フェーズ2: version += 1
  - player_name / level / ever_had / flags / met_actors / created_at / log を追加

フェーズ3: version += 1
  - owned_goods / trust_person / _rewarded_actors / pets を追加

フェーズ4: version += 1
  - place / places を追加
  - yard / occ を places["garden"] へ移行
"""


if __name__ == "__main__":
    validate_world()
    print("OK: world schema is consistent")
    print("taste_score sample (tarawa vs wet_food):",
          taste_score(CATS[3][4].get("taste", {}), FOODS[1][5]))
