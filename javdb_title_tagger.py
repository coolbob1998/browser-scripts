#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JAVDB 导出 JSON：按标题自动提取细标签，并聚合为 8 个大类。

用法：
    python javdb_title_tagger.py input.json
    python javdb_title_tagger.py input.json -o output_tagged.json
    python javdb_title_tagger.py input.json -o output_tagged.json --summary tag_summary.json

输入：
    JSON 数组，每项至少含 title 字段。

输出新增：
    "tags": ["眼镜", "地味", ...]
    "categories": ["外观穿着", "人设身份", ...]
    "tagMatches": {"眼镜": ["メガネ"], "地味": ["地味"]}
    "tagVersion": "title-v2-8cats"

说明：
- 只根据标题判断，所以“准确率优先、召回率其次”。
- “黑丝”和“丝袜”是层级关系：命中黒パンスト时会同时标记二者。
- “帅气男优”无法可靠从标题自动判断；仅当标题明确出现“イケメン”时标记“帅气男性_标题”。
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

TAG_VERSION = "title-v2-8cats"

# 49 个标准化标签。顺序也用于输出排序。
TAG_RULES = {
    # --- 你的核心偏好 ---
    "眼镜": [
        r"メガネ", r"眼鏡",
    ],
    "黑丝": [
        r"黒\s*パンスト", r"黒\s*ストッキング", r"黒\s*タイツ",
        r"ブラック\s*パンスト", r"ブラック\s*ストッキング", r"ブラック\s*タイツ",
    ],
    "丝袜": [
        r"パンスト", r"ストッキング", r"タイツ",
    ],
    "地味": [
        r"地味", r"地味系", r"地味子",
    ],
    "调教": [
        r"調教", r"躾け", r"躾", r"しつけ",
    ],

    # --- 视角 / 拍摄形式 ---
    "主观": [
        r"完全主観", r"主観", r"あなた視点", r"貴方視点", r"アナタ目線",
        r"プレイヤー体感", r"ヴァーチャル", r"バーチャル",
    ],
    "ASMR": [
        r"ASMR", r"バイノーラル",
    ],
    "自拍/跟拍": [
        r"ハメ撮り", r"個撮", r"個人撮影", r"生撮り", r"プライベートハメ撮り",
    ],

    # --- 人设 / 身份 / 服装 ---
    "OL/职场女性": [
        r"\bOL\b", r"女子社員", r"女性社員", r"会社員", r"事務員", r"派遣OL",
        r"バリキャリ", r"窓際社員",
    ],
    "女上司": [
        r"女上司", r"女性上司", r"上司の女", r"人妻上司",
    ],
    "女教师": [
        r"女教師", r"女性教師", r"担任女教師", r"美人教師",
    ],
    "家庭教师": [
        r"家庭教師", r"カテキョ",
    ],
    "学生/制服": [
        r"制服", r"女生徒", r"女子生徒", r"女学生", r"女子●生", r"J系",
        r"学生", r"生徒会長", r"図書委員",
    ],
    "女仆": [
        r"メイド", r"家政婦",
    ],
    "护士": [
        r"ナース", r"看護師",
    ],
    "空乘": [
        r"\bCA\b", r"客室乗務員", r"スチュワーデス",
    ],
    "泳装": [
        r"水着", r"競泳水着", r"ビキニ",
    ],
    "人妻": [
        r"人妻", r"若妻", r"巨乳妻", r"妻\b", r"奥様", r"奥さん", r"未亡人",
    ],
    "幼驯染": [
        r"幼馴染", r"幼なじみ", r"幼馴染み",
    ],
    "同居/同棲": [
        r"同棲", r"同居", r"ふたりぐらし", r"二人暮らし",
    ],
    "相部屋": [
        r"相部屋",
    ],
    "邻居": [
        r"隣人", r"隣家", r"隣の", r"近所",
    ],
    "亲属情境": [
        r"妹", r"姉", r"義妹", r"義姉", r"義母", r"母さん", r"叔母", r"兄嫁",
        r"甥", r"従妹", r"近親",
    ],

    # --- 外观 / 风格 ---
    "黑发": [
        r"黒髪",
    ],
    "清楚": [
        r"清楚", r"清純", r"純粋", r"優等生", r"大人し", r"内気",
    ],
    "辣妹": [
        r"ギャル", r"\bGAL\b", r"アゲ系", r"派手アゲ",
    ],
    "宅系": [
        r"オタク", r"陰キャ", r"ゲーマー",
    ],
    "巨乳": [
        r"巨乳", r"爆乳", r"デカ乳", r"神乳", r"[G-ZＩＨＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ]カップ",
    ],
    "美尻/大臀": [
        r"美尻", r"デカ尻", r"巨尻", r"プリ尻", r"ぷり尻", r"尻",
    ],
    "美腿": [
        r"美脚", r"脚線美",
    ],
    "帅气男性_标题": [
        r"イケメン",
    ],

    # --- 关系 / 剧情 ---
    "NTR": [
        r"\bNTR\b", r"寝取られ", r"寝取り", r"ネトラレ", r"寝取らせ",
    ],
    "不伦/出轨": [
        r"不倫", r"浮気", r"不貞", r"愛人",
    ],
    "恋爱/甜蜜": [
        r"イチャラブ", r"ラブラブ", r"純愛", r"恋人", r"彼女", r"デート",
        r"好き過ぎ", r"好きすぎ",
    ],

    # --- 玩法 / 主题 ---
    "女同": [
        r"レズ", r"レズビアン", r"\bLESBIAN\b", r"ビアン", r"百合",
    ],
    "痴女": [
        r"痴女",
    ],
    "服从/奴隶": [
        r"奴隷", r"奴●", r"性奴", r"絶対服従", r"いいなり", r"言いなり",
        r"従順", r"ペット", r"飼われ", r"飼い慣ら",
    ],
    "开发": [
        r"開発", r"育て", r"仕上げ",
    ],
    "束缚": [
        r"緊縛", r"拘束",
    ],
    "蒙眼": [
        r"目隠し",
    ],
    "监禁": [
        r"監禁", r"囚われ", r"軟禁",
    ],
    "强制情境": [
        r"レイプ", r"レ●プ", r"強●", r"犯された", r"犯し尽く", r"脅迫",
    ],
    "媚药/药物情境": [
        r"媚薬", r"キメセク", r"薬漬け",
    ],
    "露出/羞耻": [
        r"露出", r"恥辱", r"羞恥",
    ],
    "射精管理": [
        r"射精管理",
    ],
    "寸止": [
        r"寸止め", r"焦らし", r"焦らされ",
    ],
    "中出": [
        r"中出し", r"中出", r"膣内射精", r"生ハメ中出し", r"種付け",
    ],
    "口交": [
        r"フェラ", r"おしゃぶり", r"しゃぶり", r"口内射精", r"口中出し",
    ],
    "亲吻": [
        r"接吻", r"ベロキス", r"ディープキス", r"キス",
    ],
    "肛门": [
        r"アナル", r"肛門", r"ケツ穴",
    ],
    "乳头": [
        r"乳首",
    ],
    "放尿/漏尿": [
        r"放尿", r"お漏らし", r"おしっこ", r"聖水", r"失禁",
    ],
}


TAG_ORDER = list(TAG_RULES.keys())

# 8 个大类：细标签负责检索精度，大类负责日常浏览。
CATEGORY_MAP = {
    "外观穿着": {
        "眼镜", "黑丝", "丝袜", "黑发", "清楚", "辣妹", "巨乳", "美尻/大臀", "美腿", "泳装",
    },
    "人设身份": {
        "地味", "OL/职场女性", "女上司", "女教师", "家庭教师", "学生/制服",
        "女仆", "护士", "空乘", "宅系",
    },
    "关系剧情": {
        "人妻", "幼驯染", "同居/同棲", "相部屋", "邻居", "亲属情境",
        "恋爱/甜蜜", "NTR", "不伦/出轨",
    },
    "支配调教": {
        "调教", "服从/奴隶", "开发", "束缚", "蒙眼", "监禁", "射精管理", "寸止",
    },
    "强情节": {
        "强制情境", "媚药/药物情境", "露出/羞耻",
    },
    "性行为": {
        "中出", "口交", "亲吻", "肛门", "乳头", "放尿/漏尿",
    },
    "女性主导/女同": {
        "痴女", "女同",
    },
    "拍摄形式": {
        "主观", "ASMR", "自拍/跟拍",
    },
}

CATEGORY_ORDER = list(CATEGORY_MAP.keys())

def categories_from_tags(tags):
    tag_set = set(tags)
    return [
        category
        for category in CATEGORY_ORDER
        if tag_set.intersection(CATEGORY_MAP[category])
    ]

def compile_rules():
    compiled = {}
    for tag, patterns in TAG_RULES.items():
        compiled[tag] = [(p, re.compile(p, flags=re.IGNORECASE)) for p in patterns]
    return compiled

COMPILED = compile_rules()

def tag_title(title: str):
    title = title or ""
    tags = []
    matches = {}

    for tag in TAG_ORDER:
        hit_terms = []
        for raw_pattern, rx in COMPILED[tag]:
            for m in rx.finditer(title):
                s = m.group(0)
                if s and s not in hit_terms:
                    hit_terms.append(s)

        if hit_terms:
            tags.append(tag)
            matches[tag] = hit_terms

    return tags, matches

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="JAVDB 导出的 JSON")
    parser.add_argument("-o", "--output", help="输出 JSON 文件")
    parser.add_argument("--summary", help="标签统计 JSON 文件")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_tagged.json")
    summary_path = Path(args.summary) if args.summary else output_path.with_name(output_path.stem + "_summary.json")

    with input_path.open("r", encoding="utf-8") as f:
        movies = json.load(f)

    if not isinstance(movies, list):
        raise ValueError("输入 JSON 顶层必须是数组。")

    tag_counter = Counter()
    category_counter = Counter()
    untagged = []

    tag_movies = {tag: [] for tag in TAG_ORDER}
    category_movies = {category: [] for category in CATEGORY_ORDER}

    for movie in movies:
        title = movie.get("title", "")
        tags, matches = tag_title(title)
        categories = categories_from_tags(tags)

        # 双层结构：
        # tags = 细标签，用于精确筛选
        # categories = 8 大类，用于浏览和聚合
        movie["tags"] = tags
        movie["categories"] = categories
        movie["tagMatches"] = matches
        movie["tagVersion"] = TAG_VERSION

        tag_counter.update(tags)
        category_counter.update(categories)

        movie_summary_base = {
            "id": movie.get("id"),
            "title": title,
            "score": movie.get("score"),
            "scoreNumber": movie.get("scoreNumber"),
            "releaseDate": movie.get("releaseDate"),
        }

        if not tags:
            untagged.append(movie_summary_base.copy())

        # 细标签 -> 作品
        for tag in tags:
            item = movie_summary_base.copy()
            item["matchedTerms"] = matches.get(tag, [])
            item["categories"] = categories
            tag_movies[tag].append(item)

        # 大类 -> 作品
        for category in categories:
            item = movie_summary_base.copy()
            item["tags"] = [
                tag for tag in tags
                if tag in CATEGORY_MAP[category]
            ]
            item["matchedTerms"] = {
                tag: matches.get(tag, [])
                for tag in item["tags"]
            }
            category_movies[category].append(item)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)

    # 8 大类详情：
    # 大类 -> 子标签 -> 作品
    category_details = {}
    for category in CATEGORY_ORDER:
        subtag_details = {}

        # 保持该大类中细标签的统一顺序，只输出实际命中过的标签
        for tag in TAG_ORDER:
            if tag not in CATEGORY_MAP[category]:
                continue

            count = tag_counter.get(tag, 0)
            if count == 0:
                continue

            subtag_details[tag] = {
                "count": count,
                "movies": tag_movies[tag],
            }

        category_details[category] = {
            "count": category_counter.get(category, 0),
            "subtags": subtag_details,
        }

    summary = {
        "tagVersion": TAG_VERSION,
        "movieCount": len(movies),
        "taggedMovieCount": len(movies) - len(untagged),
        "untaggedMovieCount": len(untagged),

        "categoryCount": len(CATEGORY_MAP),
        "tagCount": len(TAG_RULES),

        # 大类统计
        "categoryFrequency": {
            category: category_counter.get(category, 0)
            for category in CATEGORY_ORDER
        },

        # 细标签统计仍保留一个扁平索引，便于快速统计；
        # 具体作品统一放到 categories -> subtags 下。
        "tagFrequency": dict(tag_counter.most_common()),

        # 层级详情：大类 -> 子标签 -> 作品
        "categories": category_details,

        # 无标签作品
        "untaggedMovies": untagged,

        "notes": [
            "summary.categories.<大类>.subtags.<细标签>.movies 是主要浏览结构。",
            "categories 是 8 个大类；subtags 是细标签。",
            "一部作品可以同时属于多个大类和多个细标签。",
            "标签只来自标题，不代表正片一定包含或主要包含该元素。",
            "matchedTerms 表示标题中实际触发标签的词，便于检查误判。",
            "tagFrequency 只作为扁平统计索引，不再重复保存作品列表。",
            "黑丝命中时通常也会命中丝袜，这是有意保留的层级标签。",
            "帅气男性_标题未放入 8 大类，因为它更适合作为男优个人属性单独管理。",
        ],
    }

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"处理作品: {len(movies)}")
    print(f"标准标签: {len(TAG_RULES)}")
    print(f"有标签作品: {len(movies) - len(untagged)}")
    print(f"无标签作品: {len(untagged)}")
    print(f"输出: {output_path}")
    print(f"统计: {summary_path}")
    print("\nTop 20 标签:")
    for tag, n in tag_counter.most_common(20):
        print(f"{tag:12s} {n}")

if __name__ == "__main__":
    main()
