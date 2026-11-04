from docx import Document
from pathlib import Path
for p in [r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\葛宣成 合稿.docx',r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\场景4实验_V2(1).docx',r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\场景三试验(1).docx']:
 d=Document(p); print('\nFILE',Path(p).name,'paras',len(d.paragraphs),'shapes',len(d.inline_shapes),'tables',len(d.tables))
 for i,x in enumerate(d.paragraphs):
  t=x.text.strip()
  if t and any(k in t for k in ['测试结果','场景','第六章','数据分析','验收','实验结果','特征','关联','溯源']): print(i,x.style.name,repr(t[:150]))
