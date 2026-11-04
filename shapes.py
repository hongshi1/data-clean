from docx import Document
from pathlib import Path
for p in [r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\葛宣成 合稿.docx',r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\场景4实验_V2(1).docx',r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\场景三试验(1).docx']:
 d=Document(p); print('\n',Path(p).name)
 for i,sh in enumerate(d.inline_shapes): print(i,sh.width,sh.height)
