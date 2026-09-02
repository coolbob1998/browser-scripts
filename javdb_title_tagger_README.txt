JAVDB 标题自动标签工具

使用方法：
1. 把 javdb_title_tagger.py 和你的导出 JSON 放到同一个文件夹。
2. 命令行执行：
   python javdb_title_tagger.py 你的文件.json

指定输出名：
   python javdb_title_tagger.py 你的文件.json -o javdb_tagged.json

脚本会生成：
- *_tagged.json：原数据 + tags + tagMatches + tagVersion
- *_summary.json：标签频次、未命中作品 ID 等统计

当前标准标签数量：49
核心标签包括：眼镜、黑丝、丝袜、地味、调教、主观、ASMR、OL/职场女性、
女上司、女教师、人妻、女同、NTR、服从/奴隶、束缚、蒙眼、监禁、
媚药/药物情境、射精管理、寸止、中出等。
