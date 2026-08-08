#!/usr/bin/env python3
"""
高质量图片提取：从原始.doc提取Visio对象→高分辨率PNG→替换MinerU低质量JPG

流程:
1. 用olefile从.doc提取OLE Package对象(Visio .vsdx/.vsd)
2. 用LibreOffice JSON filter转PNG(2000px宽度,保持宽高比)
3. 按顺序映射到content_list的image条目
4. 替换MinerU的JPG为高质量PNG
"""
import olefile
import subprocess
import json
import shutil
from pathlib import Path
from PIL import Image
import sys

BASE = Path(__file__).resolve().parent.parent
DATASET = BASE / "data/软件需归样例数据集"
CORRECT = BASE / "data/gjb_438c/mineru_correct"

# PNG导出filter: 2000px宽度,高度按宽高比自动计算
PNG_FILTER = 'png:draw_png_Export:{"PixelWidth":{"type":"long","value":"2000"}}'


def extract_visio_from_doc(doc_path):
    """从.doc文件提取所有Visio OLE对象,返回[(idx, data, format)]"""
    ole = olefile.OleFileIO(str(doc_path), raise_defects=False)
    objects = []
    
    for stream_path in ole.listdir():
        name = '/'.join(stream_path)
        name_lower = name.lower()
        
        # 大小写不敏感检查Package和VisioDocument
        if 'ObjectPool' not in name:
            continue
        if 'package' not in name_lower and 'visio' not in name_lower:
            continue
        
        try:
            data = ole.openstream(name).read()
            if len(data) < 100:
                continue
            
            # 判断格式
            if data[:2] == b'PK':
                fmt = 'vsdx'
            elif data[:4] == b'Visi':
                fmt = 'vsd'
            elif data[:4] == b'\xd0\xcf\x11\xe0':
                fmt = 'ole'
            else:
                # 检查是否是EMF
                if len(data) >= 8 and data[:4] == b'\x01\x00\x00\x00':
                    ver = int.from_bytes(data[4:8], 'little')
                    if ver in (0x10000, 0x10001):
                        fmt = 'emf'
                    else:
                        continue
                else:
                    continue
            
            objects.append((len(objects), data, fmt))
        except:
            continue
    
    ole.close()
    return objects


def convert_to_hd_png(obj_data, fmt, out_path):
    """将Visio/EMF对象转换为高分辨率PNG"""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # 写入临时文件
        ext = {'vsdx': '.vsdx', 'vsd': '.vsd', 'emf': '.emf', 'ole': '.ole'}[fmt]
        src_path = tmpdir / f"source{ext}"
        src_path.write_bytes(obj_data)
        
        # 用LibreOffice转换
        if fmt in ('vsdx', 'vsd', 'emf'):
            filter_str = PNG_FILTER if fmt in ('vsdx', 'vsd') else 'png'
            result = subprocess.run(
                ['soffice', '--headless', '--convert-to', filter_str,
                 '--outdir', str(tmpdir), str(src_path)],
                capture_output=True, text=True, timeout=60
            )
        else:
            # OLE格式,尝试直接用soffice打开
            result = subprocess.run(
                ['soffice', '--headless', '--convert-to', PNG_FILTER,
                 '--outdir', str(tmpdir), str(src_path)],
                capture_output=True, text=True, timeout=60
            )
        
        # 查找生成的PNG
        png_path = tmpdir / "source.png"
        if png_path.exists() and png_path.stat().st_size > 100:
            shutil.copy(str(png_path), str(out_path))
            return True
    
    return False


def process_document(doc_name):
    """处理单个文档: 提取Visio→转HD PNG→替换MinerU图片"""
    doc_path = DATASET / f"{doc_name}.doc"
    if not doc_path.exists():
        print(f"  ✗ .doc文件不存在: {doc_path}")
        return 0
    
    # 1. 提取Visio对象
    objects = extract_visio_from_doc(doc_path)
    print(f"  提取了{len(objects)}个OLE对象")
    
    if not objects:
        print(f"  无OLE对象,跳过")
        return 0
    
    # 2. 转换为HD PNG
    correct_dir = CORRECT / doc_name
    img_out_dir = correct_dir / "final" / "images" / doc_name[:20]
    img_out_dir.mkdir(parents=True, exist_ok=True)
    
    hd_pngs = []
    for idx, data, fmt in objects:
        out_path = img_out_dir / f"hd_{idx:03d}.png"
        if convert_to_hd_png(data, fmt, out_path):
            try:
                img = Image.open(out_path)
                size_kb = out_path.stat().st_size // 1024
                hd_pngs.append((idx, out_path, img.size, size_kb))
            except:
                pass
    
    print(f"  HD PNG转换成功: {len(hd_pngs)}/{len(objects)}")
    
    # 3. 读取content_list,获取图片顺序
    cl_path = correct_dir / "final" / "content_list.json"
    if not cl_path.exists():
        print(f"  ✗ content_list.json不存在")
        return 0
    
    cl = json.loads(cl_path.read_text())
    img_items = [item for item in cl if isinstance(item, dict) and item.get('type') == 'image']
    
    # 4. 按顺序映射HD PNG到content_list图片
    replaced = 0
    for i, img_item in enumerate(img_items):
        if i < len(hd_pngs):
            idx, png_path, size, size_kb = hd_pngs[i]
            old_path = img_item.get('img_path', '')
            
            # 计算相对路径
            rel_path = f"images/{doc_name[:20]}/hd_{idx:03d}.png"
            img_item['img_path'] = rel_path
            replaced += 1
    
    # 5. 保存更新后的content_list
    if replaced > 0:
        cl_path.write_text(json.dumps(cl, ensure_ascii=False, indent=2))
        print(f"  替换了{replaced}/{len(img_items)}张图片")
        
        # 对比质量
        print(f"  质量对比:")
        for i, (idx, png_path, size, size_kb) in enumerate(hd_pngs[:3]):
            print(f"    HD #{i}: {size[0]}x{size[1]}px, {size_kb}KB")
    
    return replaced


def main():
    print("=" * 60)
    print("高质量图片提取: Visio→HD PNG")
    print("=" * 60)
    
    total_replaced = 0
    for doc_dir in sorted(CORRECT.iterdir()):
        if not doc_dir.is_dir() or doc_dir.name.startswith('.') or doc_dir.name.startswith('_'):
            continue
        
        doc_name = doc_dir.name
        print(f"\n[{doc_name[:30]}]")
        replaced = process_document(doc_name)
        total_replaced += replaced
    
    print(f"\n{'='*60}")
    print(f"完成: 共替换{total_replaced}张图片为HD版本")


if __name__ == "__main__":
    main()
