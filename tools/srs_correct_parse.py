#!/usr/bin/env python3
"""
SRS正确解析流程 (MinerU原生 + HD图片提取)
==========================================
完整流程:
  Step 1: .doc → .docx (LibreOffice, EMF→PNG预处理)
  Step 2: .docx → .pdf (LibreOffice)
  Step 3: .pdf → MinerU分批解析 (pipeline/auto/ch, 每批10页)
  Step 4: 合并MinerU输出
  Step 5: HD图片提取 (从.doc提取Visio OLE对象→高分辨率PNG→替换MinerU低质量JPG)

HD图片提取原理:
  - 原始.doc中的图片是Visio格式(.vsdx/.vsd),存储在OLE ObjectPool中
  - MinerU从PDF提取的图片是JPG(有损压缩),且分辨率低
  - 本步骤直接从.doc提取Visio原始文件,用LibreOffice转为无损PNG
  - 按顺序映射到content_list的image条目,替换MinerU的JPG路径

用法: python3 tools/srs_correct_parse.py --input "data/软件需归样例数据集/" --output "data/gjb_438c/mineru_correct/"
"""
import argparse
import json
import re
import sys
import zipfile
import subprocess
import tempfile
import shutil
import olefile
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
MINERU_PYTHON = str(Path.home() / "mineru-env" / "bin" / "python")
SOFFICE = "soffice"
BATCH_PAGES = 10  # 每批处理页数(避免内存溢出)


def doc_to_docx_fix_emf(doc_path: Path, output_dir: Path) -> Path:
    """Step 1: .doc → .docx(EMF→PNG预处理)
    
    关键: 在传给MinerU之前就把EMF转为PNG,而不是事后补救
    """
    doc_name = doc_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1a: .doc → .docx (LibreOffice)
    raw_docx = output_dir / f"{doc_name}_raw.docx"
    subprocess.run(
        [SOFFICE, '--headless', '--convert-to', 'docx', '--outdir', str(output_dir), str(doc_path)],
        capture_output=True, text=True, timeout=60
    )
    # 找到生成的docx
    generated = list(output_dir.glob("*.docx"))
    if generated:
        if generated[0] != raw_docx:
            shutil.move(str(generated[0]), str(raw_docx))
    if not raw_docx.exists():
        print(f"    ✗ .doc→.docx失败")
        return None
    
    # Step 1b: docx中EMF→PNG预处理
    fixed_docx = output_dir / f"{doc_name}.docx"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # 解压docx
        with zipfile.ZipFile(raw_docx, 'r') as z:
            z.extractall(tmpdir / "extracted")
        
        media_dir = tmpdir / "extracted" / "word" / "media"
        if media_dir.exists():
            emf_files = list(media_dir.glob("*.emf"))
            for emf in emf_files:
                # EMF→PNG (LibreOffice)
                subprocess.run(
                    [SOFFICE, '--headless', '--convert-to', 'png', '--outdir', str(media_dir), str(emf)],
                    capture_output=True, text=True, timeout=30
                )
                emf.unlink()  # 删除EMF
            
            # 修改document.xml.rels中的.emf→.png引用
            rels_path = tmpdir / "extracted" / "word" / "_rels" / "document.xml.rels"
            if rels_path.exists():
                content = rels_path.read_text()
                content = content.replace('.emf', '.png')
                rels_path.write_text(content)
        
        # 重新打包docx
        with zipfile.ZipFile(fixed_docx, 'w', zipfile.ZIP_DEFLATED) as z:
            for file in (tmpdir / "extracted").rglob("*"):
                if file.is_file():
                    arcname = str(file.relative_to(tmpdir / "extracted"))
                    z.write(file, arcname)
    
    raw_docx.unlink()  # 删除原始docx
    return fixed_docx


def docx_to_pdf(docx_path: Path, output_dir: Path) -> Path:
    """Step 2: .docx → .pdf (LibreOffice)"""
    pdf_path = output_dir / f"{docx_path.stem}.pdf"
    subprocess.run(
        [SOFFICE, '--headless', '--convert-to', 'pdf', '--outdir', str(output_dir), str(docx_path)],
        capture_output=True, text=True, timeout=120
    )
    if not pdf_path.exists():
        print(f"    ✗ .docx→.pdf失败")
        return None
    return pdf_path


def get_pdf_page_count(pdf_path: Path) -> int:
    """获取PDF页数"""
    result = subprocess.run(
        [MINERU_PYTHON, '-c', f'''
import pypdf
reader = pypdf.PdfReader("{pdf_path}")
print(len(reader.pages))
'''],
        capture_output=True, text=True, timeout=30
    )
    try:
        return int(result.stdout.strip())
    except:
        return 0


def parse_pdf_with_mineru(pdf_path: Path, output_dir: Path, start_page: int = 0, end_page: int = None) -> Path:
    """Step 3: 用MinerU解析PDF(分批避免内存溢出)
    
    MinerU正确参数:
      --backend pipeline  (通用后端)
      -m auto              (自动选择txt/ocr模式)
      -l ch                (中文优化)
      -s/-e                (分页范围,避免内存溢出)
    """
    cmd = [
        MINERU_PYTHON.replace('/python', ''),  # mineru命令
        '-p', str(pdf_path),
        '-o', str(output_dir),
        '--backend', 'pipeline',
        '-m', 'auto',
        '-l', 'ch',
    ]
    # 查找mineru可执行文件
    mineru_bin = str(Path.home() / "mineru-env" / "bin" / "mineru")
    cmd[0] = mineru_bin
    
    if start_page > 0:
        cmd.extend(['-s', str(start_page)])
    if end_page is not None:
        cmd.extend(['-e', str(end_page)])
    
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600
    )
    
    if result.returncode != 0:
        print(f"    ⚠ MinerU返回码={result.returncode}")
        # 检查是否有部分输出
        return None
    
    return output_dir


def merge_mineru_outputs(output_dirs: list, final_dir: Path) -> dict:
    """合并分批MinerU输出"""
    final_dir.mkdir(parents=True, exist_ok=True)
    final_images = final_dir / "images"
    final_images.mkdir(exist_ok=True)
    
    all_content = []
    image_path_map = {}  # 旧路径→新路径
    img_counter = 0
    
    for batch_dir in output_dirs:
        if not batch_dir or not batch_dir.exists():
            continue
        # 找*content_list.json(排除v2) - 文件名格式为 <docname>_content_list.json
        cl_files = [f for f in batch_dir.rglob("*content_list.json") if 'v2' not in f.name]
        if not cl_files:
            continue
        
        cl_path = cl_files[0]
        cl = json.loads(cl_path.read_text())
        
        # 找images目录(在content_list同级)
        img_dir = cl_path.parent / "images"
        if not img_dir.exists():
            # 在上级找
            for d in cl_files[0].parent.rglob("images"):
                if d.is_dir():
                    img_dir = d
                    break
        
        # 处理图片: 复制并重命名
        for item in cl:
            if isinstance(item, dict) and item.get('type') == 'image':
                old_path = item.get('img_path', '')
                if old_path:
                    old_full = img_dir / Path(old_path).name if img_dir.exists() else None
                    if old_full and old_full.exists():
                        img_counter += 1
                        new_name = f"img_{img_counter:04d}.jpg"
                        new_full = final_images / new_name
                        shutil.copy(str(old_full), str(new_full))
                        item['img_path'] = f"images/{new_name}"
            all_content.append(item)
    
    # 保存合并后的content_list
    (final_dir / "content_list.json").write_text(
        json.dumps(all_content, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    return {
        "content_list": all_content,
        "image_count": img_counter,
        "content_count": len(all_content),
    }


# ============================================================
# Step 5: HD图片提取 (从.doc提取Visio OLE对象→高分辨率PNG)
# ============================================================

def extract_visio_objects(doc_path: Path):
    """从.doc文件提取所有Visio OLE对象
    
    返回: [(idx, data, format)] format∈{'vsdx','vsd'}
    """
    ole = olefile.OleFileIO(str(doc_path), raise_defects=False)
    objects = []
    
    for stream_path in ole.listdir():
        name = '/'.join(stream_path)
        name_lower = name.lower()
        
        # 大小写不敏感检查Package和VisioDocument
        if 'objectpool' not in name_lower:
            continue
        if 'package' not in name_lower and 'visio' not in name_lower:
            continue
        
        try:
            data = ole.openstream(name).read()
            if len(data) < 100:
                continue
            
            # 判断格式
            if data[:2] == b'PK':
                objects.append((len(objects), data, 'vsdx'))
            elif data[:4] == b'Visi':
                objects.append((len(objects), data, 'vsd'))
        except:
            continue
    
    ole.close()
    return objects


def convert_visio_to_png(obj_data: str, fmt: str, out_path: Path) -> bool:
    """将Visio对象转换为PNG
    
    使用LibreOffice headless模式转换:
      vsdx/vsd → PNG (LibreOffice Draw)
    """
    ext = '.vsdx' if fmt == 'vsdx' else '.vsd'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src_path = tmpdir / f"source{ext}"
        src_path.write_bytes(obj_data)
        
        result = subprocess.run(
            ['soffice', '--headless', '--convert-to', 'png',
             '--outdir', str(tmpdir), str(src_path)],
            capture_output=True, text=True, timeout=30
        )
        
        png_path = tmpdir / "source.png"
        if png_path.exists() and png_path.stat().st_size > 100:
            shutil.copy(str(png_path), str(out_path))
            return True
    
    return False


def replace_with_hd_images(doc_path: Path, final_dir: Path, doc_name: str) -> dict:
    """Step 5: 从.doc提取Visio→HD PNG→替换MinerU的JPG
    
    流程:
    1. 用olefile从.doc提取所有Visio OLE对象(.vsdx/.vsd)
    2. 用LibreOffice将每个Visio对象转为PNG(无损)
    3. 按顺序映射到content_list的image条目
    4. 替换MinerU的低质量JPG路径为HD PNG路径
    
    质量改进:
    - 格式: JPG(有损) → PNG(无损)
    - 来源: PDF二次提取 → Visio原始文件直接转换
    - 小图片: 104x168px/3KB → 366x248px/28KB (5x提升)
    """
    cl_path = final_dir / "content_list.json"
    if not cl_path.exists():
        return {"hd_replaced": 0, "hd_total": 0, "reason": "content_list不存在"}
    
    # 1. 提取Visio对象
    objects = extract_visio_objects(doc_path)
    if not objects:
        return {"hd_replaced": 0, "hd_total": 0, "reason": "无Visio OLE对象"}
    
    # 2. 转换为HD PNG
    img_out_dir = final_dir / "images" / doc_name[:20]
    img_out_dir.mkdir(parents=True, exist_ok=True)
    
    hd_pngs = []
    for idx, data, fmt in objects:
        out_path = img_out_dir / f"hd_{idx:03d}.png"
        if convert_visio_to_png(data, fmt, out_path):
            hd_pngs.append((idx, out_path))
    
    if not hd_pngs:
        return {"hd_replaced": 0, "hd_total": 0, "reason": "Visio→PNG转换失败"}
    
    # 3. 读取content_list,按顺序替换
    cl = json.loads(cl_path.read_text())
    img_items = [item for item in cl if isinstance(item, dict) and item.get('type') == 'image']
    
    replaced = 0
    for i, img_item in enumerate(img_items):
        if i < len(hd_pngs):
            idx, png_path = hd_pngs[i]
            rel_path = f"images/{doc_name[:20]}/hd_{idx:03d}.png"
            img_item['img_path'] = rel_path
            replaced += 1
    
    # 4. 保存更新后的content_list
    cl_path.write_text(json.dumps(cl, ensure_ascii=False, indent=2))
    
    # 5. 清理旧的MinerU JPG文件
    old_jpgs = list(img_out_dir.glob("img_*.jpg"))
    for jpg in old_jpgs:
        jpg.unlink()
    
    return {
        "hd_replaced": replaced,
        "hd_total": len(img_items),
        "visio_objects": len(objects),
        "hd_pngs_generated": len(hd_pngs),
    }


def process_document(doc_path: Path, output_base: Path) -> dict:
    """处理单个文档的完整流程"""
    doc_name = doc_path.stem
    doc_output = output_base / doc_name
    
    print(f"\n{'='*60}")
    print(f"处理: {doc_name}")
    print(f"{'='*60}")
    
    # Step 1: .doc → .docx(EMF→PNG)
    print(f"  [Step1] .doc → .docx(EMF→PNG预处理)")
    docx_path = doc_to_docx_fix_emf(doc_path, doc_output)
    if not docx_path:
        return None
    print(f"    ✓ {docx_path.name} ({docx_path.stat().st_size//1024}KB)")
    
    # Step 2: .docx → .pdf
    print(f"  [Step2] .docx → .pdf")
    pdf_path = docx_to_pdf(docx_path, doc_output)
    if not pdf_path:
        return None
    print(f"    ✓ {pdf_path.name} ({pdf_path.stat().st_size//1024}KB)")
    
    # Step 3: 获取页数
    page_count = get_pdf_page_count(pdf_path)
    print(f"  [Step3] PDF页数: {page_count}")
    
    # Step 4: MinerU分批解析
    print(f"  [Step4] MinerU解析(每{BATCH_PAGES}页一批)")
    batch_outputs = []
    
    for start in range(0, page_count, BATCH_PAGES):
        end = min(start + BATCH_PAGES - 1, page_count - 1)
        batch_num = start // BATCH_PAGES
        batch_dir = doc_output / f"batch_{batch_num:02d}"
        
        if batch_dir.exists() and (batch_dir / "done.flag").exists():
            print(f"    [batch {batch_num}] 跳过(已完成)")
            batch_outputs.append(batch_dir)
            continue
        
        print(f"    [batch {batch_num}] 页{start}-{end}...", end=" ")
        result = parse_pdf_with_mineru(pdf_path, batch_dir, start, end)
        
        if result:
            # MinerU输出到 <batch_dir>/<doc_stem>/auto/ 下
            actual_output = None
            for d in batch_dir.rglob("auto"):
                if d.is_dir() and any(d.glob("*content_list.json")):
                    actual_output = d
                    break
            # 也检查直接在batch_dir下的情况
            if not actual_output:
                for cl in batch_dir.rglob("content_list.json"):
                    actual_output = cl.parent
                    break
            if actual_output:
                batch_outputs.append(actual_output)
                (batch_dir / "done.flag").touch()
                print(f"✓")
            else:
                print(f"✗ (无输出)")
        else:
            print(f"✗")
    
    # Step 5: 合并输出
    print(f"  [Step5] 合并{len(batch_outputs)}批输出")
    final_dir = doc_output / "final"
    merged = merge_mineru_outputs(batch_outputs, final_dir)
    print(f"    ✓ content_list: {merged['content_count']}条")
    print(f"    ✓ 图片(MinerU): {merged['image_count']}个(唯一路径)")
    
    # Step 6: HD图片提取(Visio→PNG替换MinerU JPG)
    print(f"  [Step6] HD图片提取(Visio OLE→PNG)")
    hd_result = replace_with_hd_images(doc_path, final_dir, doc_name)
    if hd_result.get("hd_replaced", 0) > 0:
        print(f"    ✓ HD替换: {hd_result['hd_replaced']}/{hd_result['hd_total']}张")
        print(f"    ✓ Visio对象: {hd_result.get('visio_objects',0)}个 → HD PNG: {hd_result.get('hd_pngs_generated',0)}个")
    else:
        print(f"    ○ 无HD替换: {hd_result.get('reason','未知')}")
    
    # 验证图片
    cl = merged['content_list']
    imgs = [item for item in cl if isinstance(item, dict) and item.get('type') == 'image']
    unique_paths = set(item.get('img_path', '') for item in imgs)
    print(f"    ✓ 图片路径唯一性: {len(unique_paths)}/{len(imgs)}")
    
    # 检查文件存在
    exist_count = 0
    for item in imgs:
        p = item.get('img_path', '')
        if p and (final_dir / p).exists():
            exist_count += 1
    print(f"    ✓ 图片文件存在: {exist_count}/{len(imgs)}")
    
    return {
        "doc_name": doc_name,
        "pdf_pages": page_count,
        "batches": len(batch_outputs),
        "content_count": merged['content_count'],
        "image_count": merged['image_count'],
        "hd_replaced": hd_result.get("hd_replaced", 0),
        "image_unique": len(unique_paths),
        "image_exist": exist_count,
        "total_images": len(imgs),
        "final_dir": str(final_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="SRS正确解析流程(MinerU原生)")
    parser.add_argument("--input", required=True, help="输入.doc文件或目录")
    parser.add_argument("--output", default="data/gjb_438c/mineru_correct", help="输出目录")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if input_path.is_file():
        doc_files = [input_path]
    elif input_path.is_dir():
        doc_files = sorted(list(input_path.glob("*.doc")))
    else:
        print(f"输入路径不存在: {input_path}")
        sys.exit(1)
    
    print(f"{'='*60}")
    print(f"SRS正确解析流程 (MinerU原生 + HD图片提取)")
    print(f"  流程: .doc → .docx(EMF→PNG) → .pdf → MinerU分批 → 合并 → HD图片替换")
    print(f"  MinerU参数: --backend pipeline -m auto -l ch")
    print(f"  HD图片: 从.doc提取Visio OLE对象 → LibreOffice转PNG → 替换MinerU JPG")
    print(f"  批大小: {BATCH_PAGES}页/批")
    print(f"  文档数: {len(doc_files)}")
    print(f"{'='*60}")
    
    all_results = []
    for doc_path in doc_files:
        result = process_document(doc_path, output_dir)
        if result:
            all_results.append(result)
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"解析完成: {len(all_results)}/{len(doc_files)}份文档")
    total_imgs = sum(r['total_images'] for r in all_results)
    total_exist = sum(r['image_exist'] for r in all_results)
    total_unique = sum(r['image_unique'] for r in all_results)
    total_hd = sum(r.get('hd_replaced', 0) for r in all_results)
    print(f"  图片: {total_exist}/{total_imgs}文件存在 ({total_unique}唯一路径)")
    print(f"  HD图片: {total_hd}/{total_imgs}张已替换为Visio原始PNG")
    
    # 保存汇总
    summary = {
        "parse_date": datetime.now().isoformat(),
        "pipeline": ".doc → .docx(EMF→PNG) → .pdf → MinerU(pipeline,auto,ch,分批) → 合并 → HD图片替换(Visio→PNG)",
        "total_docs": len(all_results),
        "results": all_results,
        "totals": {
            "images": total_imgs,
            "images_exist": total_exist,
            "hd_replaced": total_hd,
        },
    }
    (output_dir / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
