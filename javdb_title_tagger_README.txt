JAVDB 标题自动标签工具 v3

核心变化：
- 保留细标签 tags
- 新增 8 大类 categories
- summary 同时按大类和细标签列出作品

8 大类：
1. 外观穿着
2. 人设身份
3. 关系剧情
4. 支配调教
5. 强情节
6. 性行为
7. 女性主导/女同
8. 拍摄形式

输出单条作品示例：
{
  "id": "APAK-251",
  "tags": ["眼镜", "地味", "OL/职场女性"],
  "categories": ["外观穿着", "人设身份"],
  "tagMatches": {
    "眼镜": ["メガネ"],
    "地味": ["地味"],
    "OL/职场女性": ["OL"]
  }
}

summary 主要结构：
{
  "categoryFrequency": {...},
  "tagFrequency": {...},
  "categories": {
    "外观穿着": {
      "count": 123,
      "subtags": [...],
      "movies": [...]
    }
  },
  "tags": {
    "眼镜": {
      "count": 12,
      "category": "外观穿着",
      "movies": [...]
    }
  }
}

使用：
python javdb_title_tagger.py input.json

指定输出：
python javdb_title_tagger.py input.json -o output_tagged.json