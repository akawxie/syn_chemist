// 中文翻译。键必须与 en.ts 完全一致——TS 类型系统强制保证。
import type { Key } from "./index";

export const zh: Record<Key, string> = {
  "tab.fga": "官能团警报",
  "tab.conditions": "反应条件",
  "tab.retro": "逆合成分析",

  "input.label": "分子或反应（SMILES / InChI / MOL block / A.B>R>C）",
  "input.placeholder": "CCO   |   CC(=O)O.CCO>>CCOC(=O)C   |   或粘贴 MOL block",
  "input.invalid": "输入有误，请检查格式",
  "input.checking": "校验中…",
  "input.add_image": "📷 添加图片",
  "input.close_image": "✕ 关闭图片输入",

  "btn.analyze": "分析",
  "btn.analyzing": "分析中…",
  "btn.analyze_fga": "分析官能团",
  "btn.analyze_conditions": "推荐反应条件",
  "btn.analyze_retro": "提出逆合成路线",
  "btn.analyze_image": "图片分析",

  "confidence.high": "高置信度",
  "confidence.med": "中等置信度",
  "confidence.low": "低置信度",
  "confidence.composite": "综合分数",

  "lang.toggle": "语言",

  "result.title.fga": "官能团警报",
  "result.title.conditions": "反应条件",
  "result.title.retro": "逆合成路线",

  "result.generated_in": "生成语言：{{lang}}",
  "result.no_results": "（无结果）",

  "retry.label": "已重试 {{n}} 次",
  "ocr.not_verified": "OCR 结果未通过 round-trip 校验",

  "narrative.toggle": "LLM 原始返回",
  "narrative.thin_hint": "结构化字段较少，显示原始返回内容",

  "image.drop_hint": "📷 拖入分子结构图片 · 或粘贴（Ctrl/Cmd+V）· PNG/JPEG/WEBP ≤ 5 MB",
  "image.choose": "选择文件",
  "image.analyzing": "Gemini 正在识别图像…",
  "image.no_smiles": "未能从图像中识别出结构",
  "image.too_large": "图片过大（最大 5 MB）",
  "image.bad_type": "不支持的图片类型",
};
